import unittest
from unittest.mock import patch

from src.search import build_queries, search_web


class FakeDDGS:
    def __init__(self, items=None, error: Exception | None = None):
        self.items = items or []
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, region=None, max_results=None):
        if self.error is not None:
            raise self.error
        return self.items


class SearchTest(unittest.TestCase):
    def test_build_queries_include_game_topic_and_competitors(self):
        queries = build_queries("冒险大作战", "5", ["天天冒险"])

        self.assertEqual(len(queries), 3)
        self.assertIn("冒险大作战 第5关", queries[0])
        self.assertIn("天天冒险", queries[1])

    def test_invalid_urls_are_filtered_and_duplicates_removed(self):
        items = [
            {"title": "恶意链接", "href": "javascript:alert(1)", "body": "x"},
            {"title": "竞品动态", "href": "https://example.com/a", "body": "减负活动"},
            {"title": "重复结果", "href": "https://example.com/a", "body": "重复"},
            {"title": "无协议", "href": "//example.com/b", "body": "y"},
        ]
        with patch("src.search._load_ddgs", return_value=lambda: FakeDDGS(items)):
            outcome = search_web(["query"])

        self.assertTrue(outcome.enabled)
        self.assertEqual(len(outcome.results), 1)
        self.assertEqual(outcome.results[0].title, "竞品动态")
        self.assertEqual(outcome.results[0].url, "https://example.com/a")

    def test_search_error_does_not_raise(self):
        with patch("src.search._load_ddgs", return_value=lambda: FakeDDGS(error=RuntimeError("blocked"))):
            outcome = search_web(["query"])

        self.assertTrue(outcome.enabled)
        self.assertEqual(outcome.results, [])
        self.assertTrue(outcome.errors)
        self.assertIn("未返回可用结果", outcome.to_markdown())

    def test_missing_dependency_degrades(self):
        with patch("src.search._load_ddgs", return_value=None):
            outcome = search_web(["query"])

        self.assertEqual(outcome.results, [])
        self.assertTrue(any("ddgs" in error for error in outcome.errors))


if __name__ == "__main__":
    unittest.main()
