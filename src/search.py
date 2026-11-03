"""可选联网检索：为报告补充竞品与行业情报，失败时不影响主流程。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

from .utils import md_cell, topic_label, truncate


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass
class SearchOutcome:
    enabled: bool
    queries: list[str] = field(default_factory=list)
    results: list[SearchResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        if not self.enabled:
            return "本次未启用联网检索，未获取外部竞品情报。"
        if not self.results:
            detail = (
                f"（错误：{'；'.join(truncate(error, 120) for error in self.errors)}）"
                if self.errors
                else ""
            )
            return f"联网检索已启用，但未返回可用结果{detail}。"
        lines = [
            "| 编号 | 标题 | 摘要 | 来源 |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for index, result in enumerate(self.results, start=1):
            host = urlparse(result.url).netloc or "链接"
            lines.append(
                f"| S{index} | {md_cell(result.title, 60)} | {md_cell(result.snippet, 100)} "
                f"| [{host}]({result.url}) |"
            )
        lines.append("")
        lines.append("> 检索结果来自公开网络，时间与真实性需人工复核。")
        return "\n".join(lines)


def build_queries(game: str, level: str, competitors: list[str] | None = None) -> list[str]:
    year = date.today().year
    topic = topic_label(level)
    names = " ".join(competitors) if competitors else "同类游戏"
    return [
        f"{game} {topic} 难度 玩家评价 {year}",
        f"{game} 竞品 {names} 活动 福利 {year}",
        f"游戏行业 新手引导 难度曲线 减负 优化 {year}",
    ]


def search_web(queries: list[str], max_results_per_query: int = 4) -> SearchOutcome:
    ddgs_class = _load_ddgs()
    if ddgs_class is None:
        return SearchOutcome(
            enabled=True,
            queries=queries,
            errors=["未安装搜索依赖 ddgs，请执行 pip install -r requirements.txt"],
        )

    results: list[SearchResult] = []
    errors: list[str] = []
    seen: set[str] = set()
    try:
        with ddgs_class() as ddgs:
            for query in queries:
                try:
                    items = ddgs.text(query, region="cn-zh", max_results=max_results_per_query)
                except Exception as exc:  # 网络/限流等问题不应中断分析
                    errors.append(f"{query}: {exc}")
                    continue
                for item in items or []:
                    url = (item.get("href") or item.get("url") or "").strip()
                    title = (item.get("title") or "").strip()
                    parsed = urlparse(url)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        continue
                    if not title or url in seen:
                        continue
                    seen.add(url)
                    snippet = (item.get("body") or item.get("snippet") or "").strip()
                    results.append(
                        SearchResult(title=title, url=url, snippet=truncate(snippet, 300))
                    )
    except Exception as exc:
        errors.append(f"检索初始化失败：{exc}")

    return SearchOutcome(enabled=True, queries=queries, results=results, errors=errors)


def _load_ddgs():
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # 兼容旧包名
        except ImportError:
            return None
    return DDGS
