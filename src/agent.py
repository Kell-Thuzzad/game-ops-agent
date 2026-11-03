"""分析编排：本地统计 → 可选联网检索 → 证据注入 LLM → 报告与附录。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .analytics import DataProfile, profile_dataset
from .config import Settings
from .data_loader import Dataset
from .llm import LLMError, complete
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .report import (
    build_appendix,
    build_data_summary,
    build_evidence_markdown,
    build_full_context,
    build_offline_report,
)
from .search import SearchOutcome, build_queries, search_web
from .utils import topic_label, truncate

MODE_LLM = "llm"
MODE_OFFLINE = "offline"
MODE_FALLBACK = "fallback"

MODE_LABELS = {
    MODE_LLM: "LLM 深度分析",
    MODE_OFFLINE: "本地规则基线",
    MODE_FALLBACK: "LLM 失败降级",
}


@dataclass
class AnalysisResult:
    report: str
    mode: str
    profile: DataProfile
    search: SearchOutcome | None = None


class GameOpsAgent:
    def __init__(self, settings: Settings, logger: logging.Logger | None = None):
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)

    def run(
        self,
        *,
        dataset: Dataset,
        game: str,
        level: str,
        competitors: list[str] | None = None,
        offline: bool = False,
        use_search: bool = True,
        full_context: bool = False,
        strict_llm: bool = False,
    ) -> AnalysisResult:
        competitors = competitors or []
        profile = profile_dataset(dataset)
        self.logger.info(
            "已加载 %s 条评论：负面占比 %.0f%%，风险等级 %s",
            profile.total,
            profile.negative_share * 100,
            profile.risk_level,
        )

        search_outcome: SearchOutcome | None = None
        if use_search and not offline:
            queries = build_queries(game, level, competitors)
            self.logger.info("开始联网检索（%s 个查询）…", len(queries))
            search_outcome = search_web(queries)
            self.logger.info("检索完成：%s 条结果", len(search_outcome.results))
            for error in search_outcome.errors:
                self.logger.warning("检索异常：%s", error)

        if offline:
            report = build_offline_report(
                game=game,
                level=level,
                dataset=dataset,
                profile=profile,
                search=search_outcome,
                competitors=competitors,
            )
            return AnalysisResult(report=report, mode=MODE_OFFLINE, profile=profile, search=search_outcome)

        if not self.settings.has_llm:
            if strict_llm:
                raise LLMError("未配置 MOONSHOT_API_KEY 或 OPENAI_API_KEY")
            self.logger.warning("未配置 API Key，自动切换到本地规则基线模式")
            report = build_offline_report(
                game=game,
                level=level,
                dataset=dataset,
                profile=profile,
                search=search_outcome,
                competitors=competitors,
            )
            return AnalysisResult(report=report, mode=MODE_OFFLINE, profile=profile, search=search_outcome)

        try:
            report = self._llm_report(
                dataset=dataset,
                profile=profile,
                search=search_outcome,
                game=game,
                level=level,
                competitors=competitors,
                full_context=full_context,
            )
            return AnalysisResult(report=report, mode=MODE_LLM, profile=profile, search=search_outcome)
        except LLMError as exc:
            if strict_llm:
                raise
            self.logger.warning("大模型调用失败，降级为本地规则基线：%s", exc)
            note = (
                f"> 说明：本次大模型调用失败（{exc}），已自动降级为本地规则基线报告。"
                "以下内容仅基于确定性统计，不含 LLM 语义归因。\n\n"
            )
            report = note + build_offline_report(
                game=game,
                level=level,
                dataset=dataset,
                profile=profile,
                search=search_outcome,
                competitors=competitors,
            )
            return AnalysisResult(report=report, mode=MODE_FALLBACK, profile=profile, search=search_outcome)

    def _llm_report(
        self,
        *,
        dataset: Dataset,
        profile: DataProfile,
        search: SearchOutcome | None,
        game: str,
        level: str,
        competitors: list[str],
        full_context: bool,
    ) -> str:
        evidence = build_evidence_markdown(dataset, profile)
        if full_context:
            evidence += (
                "\n### 评论原文（按长度预算截断）\n"
                + build_full_context(dataset, self.settings.max_context_chars)
            )
        search_evidence = (
            search.to_markdown() if search is not None else "本次未启用联网检索，缺少外部竞品情报。"
        )
        if search is not None and search.errors:
            errors_text = "；".join(truncate(error, 120) for error in search.errors)
            search_evidence += f"\n\n检索异常：{errors_text}"

        user_prompt = build_user_prompt(
            game=game,
            topic=topic_label(level),
            competitors=competitors,
            data_summary=build_data_summary(dataset, profile),
            evidence=evidence,
            search_evidence=search_evidence,
        )
        self.logger.info("调用模型 %s 生成报告…", self.settings.model)
        body = complete(self.settings, SYSTEM_PROMPT, user_prompt)
        appendix = build_appendix(dataset, profile, search)
        return f"{body}\n\n{appendix}"
