import tempfile
import unittest
from pathlib import Path

from src.data_loader import load_dataset


class DataLoaderTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, name: str, content: str, encoding: str = "utf-8") -> Path:
        path = self.root / name
        path.write_bytes(content.encode(encoding))
        return path

    def test_cr_only_csv_with_quoted_commas(self):
        path = self._write(
            "comments.csv",
            "user_id,comment_content,date,rating\r"
            "1001,\"第5关太难了，卡关\",2026-03-20,1\r"
            "1002,\"新手引导太差，不会用技能\",2026-03-21,2\r"
            "1003,\"第5关太难了，卡关\",2026-03-22,5\r",
        )
        dataset = load_dataset(path)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.duplicates_removed, 1)
        self.assertEqual(dataset.comments[0].rating, 1)
        self.assertEqual(dataset.comments[0].date, "2026-03-20")
        self.assertEqual(dataset.comments[1].user_id, "1002")

    def test_column_fallback_and_custom_names(self):
        path = self._write(
            "custom.csv",
            "uid,text,score,date\n"
            "a1,小怪血量太厚,1,2026/03/20\n"
            "a2,引导缺失,3,2026/03/21\n",
        )
        dataset = load_dataset(path)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.comments[0].text, "小怪血量太厚")
        self.assertEqual(dataset.comments[0].rating, 1)
        self.assertEqual(dataset.comments[0].date, "2026-03-20")

    def test_unknown_text_column_is_guessed(self):
        path = self._write(
            "guess.csv",
            "id,foo\n1,这是一条很长的玩家评论内容\n2,短\n",
        )
        dataset = load_dataset(path)

        self.assertEqual(dataset.comments[0].text, "这是一条很长的玩家评论内容")
        self.assertTrue(any("自动选择" in warning for warning in dataset.warnings))

    def test_txt_lines_and_comments(self):
        path = self._write("comments.txt", "# header\n第一关卡关\n\n第二关还行\n")
        dataset = load_dataset(path)

        self.assertEqual([c.text for c in dataset.comments], ["第一关卡关", "第二关还行"])

    def test_gb18030_encoding(self):
        path = self._write("gbk.csv", "user_id,content\n1,数值崩坏\n", encoding="gb18030")
        dataset = load_dataset(path)

        self.assertEqual(dataset.comments[0].text, "数值崩坏")

    def test_max_comments_truncates_with_warning(self):
        path = self._write("many.csv", "content\n" + "\n".join(f"评论{i}" for i in range(10)))
        dataset = load_dataset(path, max_comments=4)

        self.assertEqual(len(dataset), 4)
        self.assertTrue(dataset.truncated)
        self.assertTrue(any("上限" in warning for warning in dataset.warnings))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_dataset(self.root / "missing.csv")

    def test_unsupported_extension(self):
        path = self._write("data.json", "{}")
        with self.assertRaises(ValueError):
            load_dataset(path)


if __name__ == "__main__":
    unittest.main()
