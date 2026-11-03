"""通用文本与文件工具。"""

from __future__ import annotations

import re
from pathlib import Path


def truncate(text: str, limit: int = 120) -> str:
    """按字符截断，避免破坏 Markdown 结构。"""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def md_cell(text: str, limit: int = 80) -> str:
    """转义 Markdown 表格单元格内容。"""
    return truncate(text, limit).replace("|", "\\|")


def topic_label(level: str) -> str:
    value = str(level).strip()
    return value if value.startswith("第") else f"第{value}关"


def save_report(content: str, path: str | Path = "output/analysis_report.md") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path
