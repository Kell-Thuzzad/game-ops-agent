"""OpenAI 兼容的对话接口封装（Moonshot / Kimi 默认）。"""

from __future__ import annotations

from .config import Settings


class LLMError(RuntimeError):
    """可预期的模型调用失败，用于触发离线降级。"""


def complete(settings: Settings, system_prompt: str, user_prompt: str) -> str:
    if not settings.api_key:
        raise LLMError("未配置 MOONSHOT_API_KEY 或 OPENAI_API_KEY")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError("缺少依赖 openai，请执行 pip install -r requirements.txt") from exc

    try:
        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
            max_retries=3,
        )
        response = client.chat.completions.create(
            model=settings.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    except Exception as exc:  # 网络、鉴权、限流、模型名错误等统一降级
        raise LLMError(f"大模型调用失败：{exc}") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise LLMError("大模型返回了空内容")
    return content
