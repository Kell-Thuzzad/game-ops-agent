"""运行配置：统一从环境变量与 .env 读取。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2.5"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _as_float(name: str, default: float) -> float:
    value = _env(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: float = 120.0
    max_comments: int = 20000
    max_context_chars: int = 120000

    @property
    def has_llm(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        return cls(
            # 兼容 Moonshot 官方与通用 OpenAI 兼容网关
            api_key=_env("MOONSHOT_API_KEY") or _env("OPENAI_API_KEY"),
            base_url=_env("LLM_BASE_URL") or DEFAULT_BASE_URL,
            model=_env("LLM_MODEL") or DEFAULT_MODEL,
            temperature=_as_float("LLM_TEMPERATURE", 0.3),
            max_tokens=_as_int("LLM_MAX_TOKENS", 4096),
            timeout=_as_float("LLM_TIMEOUT", 120.0),
            max_comments=_as_int("MAX_COMMENTS", 20000),
            max_context_chars=_as_int("MAX_CONTEXT_CHARS", 120000),
        )
