"""报告组装：本地规则基线、证据附录与评论原文摘要。"""

from __future__ import annotations

from datetime import datetime

from .analytics import DataProfile, ThemeHit
from .data_loader import Comment, Dataset
from .search import SearchOutcome
from .utils import md_cell, topic_label, truncate

THEME_INSIGHTS: dict[str, str] = {
    "难度与关卡": "关卡难度与当前玩家战力/操作水平不匹配，重复失败与跑图成本放大了挫败感。",
    "数值平衡": "关卡数值（血量、攻击力、刷新频率）疑似偏离设计区间，玩家将其感知为“数值崩坏”。",
    "新手引导": "关键机制缺少强制、可回看的分步教学，玩家“不会玩”时容易把学习成本误判成难度。",
    "客服与响应": "反馈渠道响应不及时，负面情绪缺少疏导出口，容易在社区二次发酵。",
    "竞品与福利": "竞品在体验受阻期集中投放福利，对比效应放大了玩家的流失意愿。",
    "付费体验": "付费点与卡关体验冲突时，玩家容易产生“逼氪”感知，付费意愿下降。",
    "性能与缺陷": "加载、黑屏、卡死或机制异常等技术问题会直接破坏可玩性，属于阻断性风险。",
}

# (优先级, 动作, 依据模板, 成本, 验证指标)
THEME_ACTIONS: dict[str, tuple[str, str, str, str, str]] = {
    "难度与关卡": (
        "P0",
        "下调{topic}难度并增加检查点",
        "卡关/劝退类提及 {count} 条（{share:.0%}）",
        "低",
        "关卡通过率、次日留存、卡关工单量",
    ),
    "数值平衡": (
        "P0",
        "对{topic}做一次数值回归",
        "数值类提及 {count} 条（{share:.0%}），高频词：{terms}",
        "中",
        "击杀耗时、失败次数、战力分布",
    ),
    "新手引导": (
        "P1",
        "重做关键机制的强制引导",
        "引导类提及 {count} 条（{share:.0%}），高频词：{terms}",
        "中",
        "引导完成率、首次失败后留存",
    ),
    "客服与响应": (
        "P0",
        "建立卡关工单快速响应通道",
        "客服/反馈类提及 {count} 条（{share:.0%}）",
        "低",
        "工单首响时长、重复投诉率",
    ),
    "竞品与福利": (
        "P1",
        "上线限时减负与回归福利",
        "竞品/福利类提及 {count} 条（{share:.0%}）",
        "中",
        "回流率、活动参与率、舆情情绪",
    ),
    "付费体验": (
        "P2",
        "审查卡关点附近的付费诱导",
        "付费相关提及 {count} 条（{share:.0%}）",
        "低",
        "付费转化、退款/差评提及",
    ),
    "性能与缺陷": (
        "P0",
        "排查并热更阻断性缺陷",
        "性能/BUG 类提及 {count} 条（{share:.0%}）",
        "中",
        "崩溃率、加载失败率、客服工单",
    ),
}


def build_offline_report(
    *,
    game: str,
    level: str,
    dataset: Dataset,
    profile: DataProfile,
    search: SearchOutcome | None,
    competitors: list[str],
    generated_at: str | None = None,
) -> str:
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    topic = topic_label(level)
    risk = f"{profile.risk_level}危"
    top_themes = profile.themes[:4]

    lines = [
        f"# 游戏经营分析报告：《{game}》{topic}专项分析",
        "",
        f"- 生成时间：{generated_at}",
        f"- 数据来源：`{dataset.source}`，{profile.total} 条有效样本",
        "- 分析模式：本地规则基线（未调用大模型）",
        f"- 风险等级：**{risk}**",
        "",
        "## 1. 现状摘要",
        "",
        f"- **样本概况**：共 {profile.total} 条评论"
        + (f"，其中 {profile.rated} 条带评分，平均 {profile.avg_rating} 星。" if profile.has_ratings else "，无评分字段。"),
        f"- **负面信号**：{profile.negative} 条负面样本，占 {profile.negative_share:.0%}（口径：{profile.sentiment_basis}）。",
    ]
    if profile.date_range:
        lines.append(f"- **时间范围**：{profile.date_range[0]} 至 {profile.date_range[1]}。")
    if profile.has_ratings:
        lines.append(f"- **评分分布**：{_format_rating_dist(profile)}。")
    if top_themes:
        issue_text = "；".join(
            f"{theme.name}（{theme.count} 条，{theme.share:.0%}）" for theme in top_themes
        )
        lines.append(f"- **主要问题**：{issue_text}。")
    lines.append("")

    lines.extend(["## 2. 核心归因", ""])
    if not top_themes:
        lines.extend(
            [
                "未识别到稳定的问题主题。可能原因是样本量过小或评论内容过于分散。",
                "建议补充更多评论，或改用 LLM 模式进行语义归因。",
                "",
            ]
        )
    for index, theme in enumerate(top_themes, start=1):
        lines.extend(_theme_section(index, theme))
    if len(profile.themes) > len(top_themes):
        rest = "、".join(theme.name for theme in profile.themes[len(top_themes):])
        lines.append(f"其余主题：{rest}。")
        lines.append("")

    lines.extend(["## 3. 竞品对标", ""])
    if competitors:
        lines.append(f"本次重点关注的竞品：{'、'.join(competitors)}。")
        lines.append("")
    if search is None or not search.enabled:
        lines.append("本次未启用联网检索，不包含外部竞品动态。")
        competitor_theme = _find_theme(profile, "竞品与福利")
        if competitor_theme:
            lines.append(
                f"不过，样本中有 {competitor_theme.count} 条评论主动提及竞品或福利"
                f"（占 {competitor_theme.share:.0%}），说明外部对比已影响玩家情绪，建议人工核查竞品近期活动。"
            )
    else:
        lines.append(search.to_markdown())
    lines.append("")

    lines.extend(["## 4. 行动建议", ""])
    lines.extend(_action_table(profile, top_themes, topic))
    lines.append("")

    lines.extend(["## 5. 风险与不确定性", ""])
    lines.extend(
        [
            "- 本报告为规则基线：主题归因基于关键词与评分，只说明相关性和玩家感知，不能证明因果。",
            "- 评论与工单样本存在沉默用户偏差和情绪放大效应，负面占比不代表全量玩家。",
        ]
    )
    if dataset.truncated:
        lines.append("- 样本因数量上限被截断，结论仅代表所加载的部分数据。")
    if profile.total < 30:
        lines.append("- 当前样本量小于 30 条，统计波动较大，风险等级与占比仅作提示。")
    if not profile.has_ratings:
        lines.append("- 数据缺少评分字段，负面判断依赖词典命中，可能存在漏判或误判。")
    if search is not None and search.errors:
        errors_text = "；".join(truncate(error, 120) for error in search.errors)
        lines.append(f"- 联网检索存在异常：{errors_text}。")
    lines.extend(
        [
            "- 建议人工抽检 10-20 条原始评论，并对关键结论做小流量灰度验证。",
            "- 如需更深层的语义归因与策略推演，配置大模型 API Key 后使用 LLM 模式。",
            "",
        ]
    )
    return "\n".join(lines)


def build_evidence_markdown(dataset: Dataset, profile: DataProfile, max_examples: int = 10) -> str:
    lines = [
        "### 数据概况",
        f"- 数据文件：`{dataset.source}`。",
        f"- 有效样本：{profile.total} 条；有评分：{profile.rated} 条；"
        f"平均评分：{profile.avg_rating if profile.avg_rating is not None else '无'}。",
        f"- 负面样本：{profile.negative} 条，占 {profile.negative_share:.1%}"
        f"（口径：{profile.sentiment_basis}）；风险等级：{profile.risk_level}。",
    ]
    if profile.date_range:
        lines.append(f"- 时间范围：{profile.date_range[0]} 至 {profile.date_range[1]}。")
    if profile.has_ratings:
        lines.append(f"- 评分分布：{_format_rating_dist(profile)}。")
    lines.append("")

    if profile.themes:
        lines.extend(
            [
                "### 主题提及",
                "| 主题 | 提及条数 | 占比 | 高频词 |",
                "| :--- | ---: | ---: | :--- |",
            ]
        )
        for theme in profile.themes:
            lines.append(
                f"| {theme.name} | {theme.count} | {theme.share:.0%} "
                f"| {'、'.join(theme.top_terms) or '-'} |"
            )
        lines.append("")

    examples = _select_examples(profile, max_examples)
    if examples:
        lines.extend(["### 代表性评论"])
        for comment in examples:
            lines.append(f"- {format_comment(comment)}")
        lines.append("")
    return "\n".join(lines)


def build_full_context(dataset: Dataset, max_chars: int = 120000) -> str:
    """长上下文模式：按字符预算拼接评论原文。"""
    lines: list[str] = []
    used = 0
    for comment in dataset.comments:
        line = format_comment(comment, limit=500)
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1
    if len(lines) < len(dataset):
        lines.append(f"...（其余 {len(dataset) - len(lines)} 条评论因长度限制省略）")
    return "\n".join(lines)


def build_data_summary(dataset: Dataset, profile: DataProfile) -> str:
    parts = [f"{profile.total} 条有效样本"]
    if profile.has_ratings:
        parts.append(f"平均 {profile.avg_rating} 星")
    parts.append(f"负面占比 {profile.negative_share:.0%}（{profile.sentiment_basis}）")
    if profile.date_range:
        parts.append(f"时间范围 {profile.date_range[0]} 至 {profile.date_range[1]}")
    if dataset.truncated:
        parts.append("样本已截断")
    return "；".join(parts)


def build_appendix(dataset: Dataset, profile: DataProfile, search: SearchOutcome | None) -> str:
    lines = [
        "---",
        "",
        "## 附录：证据与来源",
        "",
        build_evidence_markdown(dataset, profile),
    ]
    if search is not None:
        lines.extend(["", "### 联网检索来源", "", search.to_markdown()])
    return "\n".join(lines)


def format_comment(comment: Comment, limit: int = 120) -> str:
    meta: list[str] = []
    meta.append(f"用户{comment.user_id}" if comment.user_id else f"#{comment.index}")
    if comment.date:
        meta.append(comment.date)
    if comment.rating is not None:
        meta.append(f"{comment.rating}星")
    return f"[{' | '.join(meta)}] {truncate(comment.text, limit)}"


def _theme_section(index: int, theme: ThemeHit) -> list[str]:
    insight = THEME_INSIGHTS.get(theme.name, "该主题可能反映体验或沟通问题，需结合原文进一步确认。")
    terms = "、".join(theme.top_terms) if theme.top_terms else "无明显高频词"
    lines = [
        f"### 2.{index} {theme.name}（提及 {theme.count} 条，占 {theme.share:.0%}）",
        "",
        f"- **事实**：{theme.count} 条评论命中该主题，高频词为“{terms}”。",
        f"- **推断（待验证）**：{insight}",
        "- **代表评论**：",
    ]
    for comment in theme.examples:
        lines.append(f"  - {format_comment(comment)}")
    lines.append("")
    return lines


def _action_table(profile: DataProfile, top_themes: list[ThemeHit], topic: str) -> list[str]:
    rows: list[tuple[str, str, str, str, str]] = []
    seen: set[str] = set()
    for theme in top_themes:
        template = THEME_ACTIONS.get(theme.name)
        if template is None:
            continue
        priority, action, basis, cost, metric = template
        action_text = action.format(topic=topic)
        if action_text in seen:
            continue
        seen.add(action_text)
        basis_text = basis.format(
            count=theme.count,
            share=theme.share,
            terms="、".join(theme.top_terms) or "-",
        )
        rows.append((priority, action_text, basis_text, cost, metric))

    if len(rows) < 5:
        rows.append(
            (
                "P1",
                "建立关卡通过率与舆情监控",
                f"负面样本 {profile.negative} 条（{profile.negative_share:.0%}），问题集中在少数主题",
                "低",
                "负面评论占比、通过率日环比",
            )
        )
    if len(rows) < 5:
        rows.append(
            (
                "P1",
                "对主要修复项做灰度 A/B 验证",
                "规则基线只能说明相关性，需验证改动与留存的因果关系",
                "中",
                "实验组与对照组留存差",
            )
        )

    lines = [
        "| 优先级 | 动作 | 依据 | 执行成本 | 验证指标 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for priority, action, basis, cost, metric in rows[:5]:
        lines.append(
            f"| {priority} | {md_cell(action, 40)} | {md_cell(basis, 50)} "
            f"| {cost} | {md_cell(metric, 40)} |"
        )
    return lines


def _select_examples(profile: DataProfile, limit: int) -> list[Comment]:
    selected: list[Comment] = []
    seen: set[str] = set()

    def add(comment: Comment) -> None:
        key = comment.text.strip()
        if key in seen:
            return
        seen.add(key)
        selected.append(comment)

    for theme in profile.themes:
        for comment in theme.examples:
            add(comment)
    for comment in profile.negative_examples:
        add(comment)
    selected.sort(key=lambda comment: comment.index)
    return selected[:limit]


def _find_theme(profile: DataProfile, name: str) -> ThemeHit | None:
    return next((theme for theme in profile.themes if theme.name == name), None)


def _format_rating_dist(profile: DataProfile) -> str:
    return " / ".join(
        f"{score}星 {count}" for score, count in profile.rating_dist.items()
    )


__all__ = [
    "build_appendix",
    "build_data_summary",
    "build_evidence_markdown",
    "build_full_context",
    "build_offline_report",
    "format_comment",
]
