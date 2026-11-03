"""确定性统计分析：不依赖大模型，作为报告证据与离线基线。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .data_loader import Comment, Dataset

THEMES: dict[str, tuple[str, ...]] = {
    "难度与关卡": (
        "难度", "太难", "过不去", "打不过", "卡关", "卡在", "劝退", "关卡", "地狱",
        "检查点", "存档点", "简单模式", "跳过",
    ),
    "数值平衡": (
        "数值", "血量", "攻击力", "伤害", "翻倍", "崩坏", "参数", "战力", "不掉血",
        "BOSS", "boss", "小怪", "倍",
    ),
    "新手引导": (
        "引导", "教程", "教学", "怎么用", "机制", "提示", "说明", "新手", "萌新",
        "不会玩", "弹窗",
    ),
    "客服与响应": (
        "客服", "工单", "没回复", "没人回", "反馈", "官方群", "装死", "回应", "公告",
    ),
    "竞品与福利": (
        "竞品", "隔壁", "活动", "福利", "送", "十连", "复活币", "对比", "回归",
        "XX传说", "天天冒险", "减负", "拉新",
    ),
    "付费体验": ("氪", "充值", "月卡", "付费", "抽卡", "买", "逼氪"),
    "性能与缺陷": (
        "BUG", "bug", "卡死", "闪退", "黑屏", "加载", "卡顿", "无敌", "延迟",
    ),
}

NEGATIVE_WORDS = (
    "太难", "过不去", "卡关", "卡在", "劝退", "恶心", "垃圾", "卸载", "崩坏",
    "不合理", "极差", "太差", "无语", "服了", "没人回", "抠门", "寒酸", "反了",
    "打不过", "被围殴", "无解", "无聊", "烦", "差", "缺失", "不会玩", "没教",
)

RISK_HIGH = "高"
RISK_MEDIUM = "中"
RISK_LOW = "低"


@dataclass(frozen=True)
class ThemeHit:
    name: str
    count: int
    share: float
    top_terms: list[str]
    examples: list[Comment]


@dataclass
class DataProfile:
    total: int
    rated: int
    avg_rating: float | None
    rating_dist: dict[int, int]
    negative: int
    negative_share: float
    sentiment_basis: str
    date_range: tuple[str, str] | None
    daily_counts: dict[str, int]
    themes: list[ThemeHit]
    negative_examples: list[Comment]
    risk_level: str

    @property
    def has_ratings(self) -> bool:
        return self.rated > 0

    @property
    def top_theme(self) -> ThemeHit | None:
        return self.themes[0] if self.themes else None


def profile_dataset(dataset: Dataset) -> DataProfile:
    comments = dataset.comments
    total = len(comments)
    if total == 0:
        raise ValueError("没有可分析的评论")

    ratings = [c.rating for c in comments if c.rating is not None]
    rating_dist = {score: 0 for score in range(1, 6)}
    for rating in ratings:
        rating_dist[rating] += 1

    if ratings:
        negative = sum(1 for rating in ratings if rating <= 2)
        basis = "评分≤2星"
    else:
        negative = sum(1 for comment in comments if _is_negative_text(comment.text))
        basis = "负面词命中"

    dates = sorted(c.date for c in comments if c.date)
    daily_counts = dict(sorted(Counter(c.date for c in comments if c.date).items()))
    date_range = (dates[0], dates[-1]) if dates else None

    themes = _build_themes(comments, total)
    negative_examples = _pick_negative_examples(comments, themes)
    negative_share = negative / total
    top_share = themes[0].share if themes else 0.0

    return DataProfile(
        total=total,
        rated=len(ratings),
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
        rating_dist=rating_dist,
        negative=negative,
        negative_share=negative_share,
        sentiment_basis=basis,
        date_range=date_range,
        daily_counts=daily_counts,
        themes=themes,
        negative_examples=negative_examples,
        risk_level=_risk_level(negative_share, top_share, negative),
    )


def matched_themes(text: str) -> list[str]:
    return [
        name
        for name, terms in THEMES.items()
        if any(term in text for term in terms)
    ]


def _build_themes(comments: list[Comment], total: int) -> list[ThemeHit]:
    themes: list[ThemeHit] = []
    for name, terms in THEMES.items():
        hits = [comment for comment in comments if any(term in comment.text for term in terms)]
        if not hits:
            continue
        term_counts = Counter(
            term for comment in hits for term in terms if term in comment.text
        )
        top_terms = [term for term, _ in term_counts.most_common(3)]
        examples = sorted(
            hits,
            key=lambda c: (c.rating is None or c.rating > 2, c.index),
        )[:2]
        themes.append(
            ThemeHit(
                name=name,
                count=len(hits),
                share=len(hits) / total,
                top_terms=top_terms,
                examples=examples,
            )
        )
    themes.sort(key=lambda theme: (-theme.count, theme.name))
    return themes


def _pick_negative_examples(comments: list[Comment], themes: list[ThemeHit]) -> list[Comment]:
    theme_names = {theme.name for theme in themes}

    def theme_hit_count(comment: Comment) -> int:
        return sum(1 for name in matched_themes(comment.text) if name in theme_names)

    negatives = [comment for comment in comments if _is_negative(comment)]
    ranked = sorted(
        negatives,
        key=lambda c: (-theme_hit_count(c), c.index),
    )
    return ranked[:8]


def _is_negative(comment: Comment) -> bool:
    if comment.rating is not None:
        return comment.rating <= 2
    return _is_negative_text(comment.text)


def _is_negative_text(text: str) -> bool:
    return any(word in text for word in NEGATIVE_WORDS)


def _risk_level(negative_share: float, top_share: float, negative_count: int) -> str:
    if negative_share >= 0.5 or (top_share >= 0.6 and negative_count >= 5):
        return RISK_HIGH
    if negative_share >= 0.25 or top_share >= 0.35:
        return RISK_MEDIUM
    return RISK_LOW
