import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.config import Settings
from src.llm import LLMError, complete


class FakeCompletions:
    def __init__(self, content: str = "  分析报告  ", error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class LLMTest(unittest.TestCase):
    def _fake_module(self, completions: FakeCompletions):
        module = types.ModuleType("openai")

        class Client:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.chat = SimpleNamespace(completions=completions)

        module.OpenAI = Client
        return module

    def test_complete_returns_stripped_content(self):
        completions = FakeCompletions("  报告正文  ")
        with patch.dict(sys.modules, {"openai": self._fake_module(completions)}):
            result = complete(Settings(api_key="key", model="test-model"), "system", "user")

        self.assertEqual(result, "报告正文")
        call = completions.calls[0]
        self.assertEqual(call["model"], "test-model")
        self.assertEqual(call["messages"][0], {"role": "system", "content": "system"})
        self.assertEqual(call["messages"][1], {"role": "user", "content": "user"})

    def test_missing_key_raises(self):
        with self.assertRaises(LLMError):
            complete(Settings(api_key=None), "system", "user")

    def test_api_error_wrapped(self):
        completions = FakeCompletions(error=RuntimeError("rate limit"))
        with patch.dict(sys.modules, {"openai": self._fake_module(completions)}):
            with self.assertRaisesRegex(LLMError, "大模型调用失败"):
                complete(Settings(api_key="key"), "system", "user")

    def test_empty_content_raises(self):
        completions = FakeCompletions("   ")
        with patch.dict(sys.modules, {"openai": self._fake_module(completions)}):
            with self.assertRaisesRegex(LLMError, "空内容"):
                complete(Settings(api_key="key"), "system", "user")

    def test_missing_sdk_raises(self):
        with patch.dict(sys.modules, {"openai": None}):
            with self.assertRaisesRegex(LLMError, "缺少依赖"):
                complete(Settings(api_key="key"), "system", "user")


if __name__ == "__main__":
    unittest.main()
