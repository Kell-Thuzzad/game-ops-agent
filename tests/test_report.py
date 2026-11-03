import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent import MODE_FALLBACK, MODE_LLM, MODE_OFFLINE, GameOpsAgent
from src.analytics import profile_dataset
from src.config import PROJECT_ROOT, Settings
from src.data_loader import load_dataset
from src.llm import LLMError
from src.prompts import SYSTEM_PROMPT
from src.report import build_evidence_markdown, build_offline_report
from src.search import SearchOutcome, SearchResult
from src.utils import save_report

SAMPLE = PROJECT_ROOT / "data" / "sample_comments.csv"


class ReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_dataset(SAMPLE)
        cls.profile = profile_dataset(cls.dataset)

    def _offline_report(self, search=None) -> str:
        return build_offline_report(
            game="冒险大作战",
            level="5",
            dataset=self.dataset,
            profile=self.profile,
            search=search,
            competitors=[],
            generated_at="2026-03-25 16:30",
        )

    def test_offline_report_structure(self):
        report = self._offline_report()

        for section in ("现状摘要", "核心归因", "竞品对标", "行动建议", "风险与不确定性"):
            self.assertIn(section, report)
        self.assertIn("《冒险大作战》第5关", report)
        self.assertIn("本地规则基线", report)
        self.assertIn("未启用联网检索", report)
        self.assertNotIn("None", report)
        self.assertGreaterEqual(report.count("### 2."), 3)

    def test_report_with_search_results(self):
        search = SearchOutcome(
            enabled=True,
            queries=["测试查询"],
            results=[
                SearchResult(
                    title="竞品上线减负活动",
                    url="https://example.com/news",
                    snippet="竞品本周上线登录福利",
                )
            ],
        )
        report = self._offline_report(search)

        self.assertIn("竞品上线减负活动", report)
        self.assertIn("[example.com](https://example.com/news)", report)
        self.assertIn("S1", report)

    def test_evidence_markdown_contains_quotes(self):
        evidence = build_evidence_markdown(self.dataset, self.profile)

        self.assertIn("主题提及", evidence)
        self.assertIn("代表性评论", evidence)
        self.assertIn("风险等级", evidence)

    def test_agent_offline_without_key(self):
        agent = GameOpsAgent(Settings(api_key=None))
        result = agent.run(
            dataset=self.dataset,
            game="冒险大作战",
            level="5",
            offline=True,
            use_search=False,
        )

        self.assertEqual(result.mode, MODE_OFFLINE)
        self.assertIn("现状摘要", result.report)

    def test_agent_auto_offline_when_key_missing(self):
        agent = GameOpsAgent(Settings(api_key=None))
        result = agent.run(
            dataset=self.dataset,
            game="冒险大作战",
            level="5",
            offline=False,
            use_search=False,
        )

        self.assertEqual(result.mode, MODE_OFFLINE)

    def test_strict_llm_without_key_raises(self):
        agent = GameOpsAgent(Settings(api_key=None))
        with self.assertRaises(LLMError):
            agent.run(
                dataset=self.dataset,
                game="冒险大作战",
                level="5",
                use_search=False,
                strict_llm=True,
            )

    def test_agent_llm_path_appends_appendix(self):
        agent = GameOpsAgent(Settings(api_key="test-key"))
        with patch("src.agent.complete", return_value="# 分析\n\n正文") as mocked:
            result = agent.run(
                dataset=self.dataset,
                game="冒险大作战",
                level="5",
                use_search=False,
            )

        self.assertEqual(result.mode, MODE_LLM)
        self.assertTrue(result.report.startswith("# 分析"))
        self.assertIn("附录：证据与来源", result.report)
        self.assertEqual(mocked.call_count, 1)
        _, system_prompt, user_prompt = mocked.call_args.args
        self.assertEqual(system_prompt, SYSTEM_PROMPT)
        self.assertIn("代表性评论", user_prompt)
        self.assertIn("不可信输入", system_prompt)

    def test_agent_llm_failure_falls_back(self):
        agent = GameOpsAgent(Settings(api_key="test-key"))
        with patch("src.agent.complete", side_effect=LLMError("模拟失败")):
            result = agent.run(
                dataset=self.dataset,
                game="冒险大作战",
                level="5",
                use_search=False,
            )

        self.assertEqual(result.mode, MODE_FALLBACK)
        self.assertIn("已自动降级", result.report)
        self.assertIn("现状摘要", result.report)

    def test_save_report_creates_directory(self):
        with self.subTest("nested path"):
            import tempfile

            with tempfile.TemporaryDirectory() as tempdir:
                target = Path(tempdir) / "nested" / "report.md"
                saved = save_report("# 测试", target)
                self.assertEqual(saved, target)
                self.assertEqual(target.read_text(encoding="utf-8"), "# 测试\n")


if __name__ == "__main__":
    unittest.main()
