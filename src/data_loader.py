"""评论数据加载：兼容不同列名、编码与换行格式。"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

TEXT_COLUMNS = ("comment_content", "content", "comment", "text", "message", "内容", "评论")
RATING_COLUMNS = ("rating", "score", "star", "stars", "评分")
DATE_COLUMNS = ("date", "time", "created_at", "created", "日期")
USER_COLUMNS = ("user_id", "uid", "user", "player_id", "用户")


@dataclass
class Comment:
    index: int
    text: str
    rating: int | None = None
    date: str | None = None
    user_id: str | None = None


@dataclass
class Dataset:
    comments: list[Comment]
    source: Path
    warnings: list[str] = field(default_factory=list)
    duplicates_removed: int = 0
    truncated: bool = False

    def __len__(self) -> int:
        return len(self.comments)


def load_dataset(path: str | Path, max_comments: int = 20000) -> Dataset:
    """加载 CSV/TXT 评论文件。

    CSV 自动探测文本、评分、日期、用户列；TXT 按行读取。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在：{path}")
    if max_comments <= 0:
        raise ValueError("max_comments 必须为正整数")

    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix == ".csv":
        raw_comments = _load_csv(path, warnings)
    elif suffix in {".txt", ".md", ".log"}:
        raw_comments = _load_lines(path)
    else:
        raise ValueError(f"不支持的文件类型：{suffix}（仅支持 .csv/.txt/.md/.log）")

    comments, duplicates = _dedupe(raw_comments)
    if duplicates:
        warnings.append(f"已去除 {duplicates} 条完全重复的评论")

    truncated = len(comments) > max_comments
    if truncated:
        warnings.append(f"样本超过上限 {max_comments} 条，仅使用前 {max_comments} 条")
        comments = comments[:max_comments]

    if not comments:
        raise ValueError("数据文件中没有可用的评论内容")

    return Dataset(
        comments=comments,
        source=path,
        warnings=warnings,
        duplicates_removed=duplicates,
        truncated=truncated,
    )


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            # 默认 universal newlines 会把只含 \r 的旧式换行统一成 \n
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别文件编码：{path}（请使用 UTF-8 或 GB18030）")


def _pick_column(fields: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {field.strip().lower(): field for field in fields if field}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _guess_text_column(rows: list[dict[str, str]], fields: list[str]) -> str | None:
    best: str | None = None
    best_avg = -1.0
    for field in fields:
        values = [(row.get(field) or "").strip() for row in rows]
        avg = sum(len(value) for value in values) / max(1, len(values))
        if avg > best_avg:
            best, best_avg = field, avg
    return best


def _load_csv(path: Path, warnings: list[str]) -> list[Comment]:
    text = _read_text(path)
    reader = csv.DictReader(io.StringIO(text))
    fields = [field.strip() for field in (reader.fieldnames or []) if field]
    if not fields:
        raise ValueError(f"CSV 缺少表头：{path}")
    reader.fieldnames = fields
    try:
        rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    except csv.Error as exc:
        raise ValueError(f"CSV 解析失败：{exc}") from exc

    text_col = _pick_column(fields, TEXT_COLUMNS) or _guess_text_column(rows, fields)
    if text_col is None:
        raise ValueError(f"CSV 中找不到评论文本列，现有列：{fields}")
    if _pick_column(fields, TEXT_COLUMNS) is None:
        warnings.append(f"未找到标准评论列名，自动选择内容最长的列：{text_col}")

    rating_col = _pick_column(fields, RATING_COLUMNS)
    date_col = _pick_column(fields, DATE_COLUMNS)
    user_col = _pick_column(fields, USER_COLUMNS)

    comments: list[Comment] = []
    for position, row in enumerate(rows, start=1):
        text_value = (row.get(text_col) or "").strip()
        if not text_value:
            continue
        comments.append(
            Comment(
                index=position,
                text=text_value,
                rating=_parse_rating(row.get(rating_col)) if rating_col else None,
                date=_parse_date(row.get(date_col)) if date_col else None,
                user_id=_clean_user(row.get(user_col)) if user_col else None,
            )
        )
    return comments


def _load_lines(path: Path) -> list[Comment]:
    comments: list[Comment] = []
    for position, line in enumerate(_read_text(path).splitlines(), start=1):
        text_value = line.strip()
        if not text_value or text_value.startswith("#"):
            continue
        comments.append(Comment(index=position, text=text_value))
    return comments


def _parse_rating(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(raw))
    if match is None:
        return None
    rating = round(float(match.group()))
    if rating < 1 or rating > 5:
        return None
    return rating


def _parse_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%Y/%m/%d %H:%M:%S", "%Y%m%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value[:19]


def _clean_user(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _dedupe(comments: list[Comment]) -> tuple[list[Comment], int]:
    seen: set[str] = set()
    unique: list[Comment] = []
    duplicates = 0
    for comment in comments:
        key = re.sub(r"\s+", " ", comment.text).strip()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(comment)
    return unique, duplicates
