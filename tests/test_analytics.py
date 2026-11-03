import unittest
from pathlib import Path

from src.analytics import profile_dataset
from src.data_loader import Comment, Dataset


def make_dataset(comments: list[Comment]) -> Dataset:
    return Dataset(comments=comments, source=Path("memory.csv"))


class AnalyticsTest(unittest.TestCase):
    def test_profile_with_ratings(self):
        dataset = make_dataset(
            [
                Comment(1, "第5关太难了，卡关劝退", 1, "2026-03-20", "1"),
                Comment(2, "小怪血量太厚，数值崩坏", 1, "2026-03-21", "2"),
                Comment(3, "新手引导缺失，不会用连携技能", 2, "2026-03-21", "3"),
                Comment(4, "画面不错，就是难度偏高", 3, "2026-03-22", "4"),
                Comment(5, "竞品送十连抽，福利对比明显", 2, "2026-03-23", "5"),
            ]
        )
        profile = profile_dataset(dataset)

        self.assertEqual(profile.total, 5)
        self.assertEqual(profile.rated, 5)
        self.assertEqual(profile.negative, 4)
        self.assertAlmostEqual(profile.negative_share, 0.8)
        self.assertEqual(profile.sentiment_basis, "评分≤2星")
        self.assertEqual(profile.avg_rating, 1.8)
        self.assertEqual(profile.risk_level, "高")
        self.assertEqual(profile.date_range, ("2026-03-20", "2026-03-23"))
        self.assertEqual(profile.daily_counts["2026-03-21"], 2)
        self.assertEqual(profile.rating_dist[1], 2)
        self.assertEqual(profile.rating_dist[5], 0)
        theme_names = {theme.name for theme in profile.themes}
        self.assertIn("难度与关卡", theme_names)
        self.assertIn("竞品与福利", theme_names)
        self.assertTrue(profile.negative_examples)
        self.assertTrue(all(c.rating is not None and c.rating <= 2 for c in profile.negative_examples))

    def test_profile_without_ratings_uses_lexicon(self):
        dataset = make_dataset(
            [
                Comment(1, "太难了，已经卸载"),
                Comment(2, "引导缺失，不会玩"),
                Comment(3, "画面不错"),
            ]
        )
        profile = profile_dataset(dataset)

        self.assertEqual(profile.rated, 0)
        self.assertIsNone(profile.avg_rating)
        self.assertEqual(profile.negative, 2)
        self.assertEqual(profile.sentiment_basis, "负面词命中")
        self.assertAlmostEqual(profile.negative_share, 2 / 3, places=4)

    def test_low_risk_small_sample(self):
        dataset = make_dataset(
            [
                Comment(1, "画面不错", 5),
                Comment(2, "音乐好听", 4),
            ]
        )
        profile = profile_dataset(dataset)

        self.assertEqual(profile.negative, 0)
        self.assertEqual(profile.risk_level, "低")
        self.assertEqual(profile.themes, [])

    def test_empty_dataset_rejected(self):
        with self.assertRaises(ValueError):
            profile_dataset(make_dataset([]))


if __name__ == "__main__":
    unittest.main()
