import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT

SAMPLE = PROJECT_ROOT / "data" / "sample_comments.csv"


class CliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "src", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    def test_offline_end_to_end(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "report.md"
            proc = self._run(
                "--offline",
                "--no-search",
                "--input",
                str(SAMPLE),
                "--output",
                str(output),
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(output.exists())
            content = output.read_text(encoding="utf-8")
            self.assertIn("游戏经营分析报告", content)
            self.assertIn("现状摘要", content)
            self.assertIn("报告已保存", proc.stdout)

    def test_missing_input_returns_error(self):
        proc = self._run(
            "--offline",
            "--no-search",
            "--input",
            str(PROJECT_ROOT / "data" / "missing.csv"),
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("不存在", proc.stderr)

    def test_strict_llm_without_key_fails(self):
        proc = self._run(
            "--no-search",
            "--strict-llm",
            "--input",
            str(SAMPLE),
        )

        self.assertEqual(proc.returncode, 3)
        self.assertIn("MOONSHOT_API_KEY", proc.stderr)


if __name__ == "__main__":
    unittest.main()
