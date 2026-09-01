import random
import unittest

import history


class TestSummarize(unittest.TestCase):
    def test_recency_is_ordinal_and_most_recent_wins(self):
        # plans passed most-recent-first, as load_recent_plans returns them
        plans = [
            {
                "week_of": "2026-09-08",
                "posts": [
                    {"content_type": "Reviews", "property": None, "format": "Story", "hook": "hook A"},
                ],
            },
            {
                "week_of": "2026-09-01",
                "posts": [
                    {"content_type": "Property Showcase", "property": "Riverside Loft", "format": "Carousel", "hook": "hook B"},
                    {"content_type": "Reviews", "property": None, "format": "Normal post", "hook": "hook C"},
                ],
            },
        ]
        summary = history.summarize(plans)

        self.assertEqual(summary["weeks_considered"], 2)
        # "Reviews" appears in both weeks -> should record the MORE recent (weeks_ago=0), not overwrite with 1
        self.assertEqual(summary["content_type_recency"]["Reviews"], 0)
        self.assertEqual(summary["content_type_recency"]["Property Showcase"], 1)
        self.assertEqual(summary["property_recency"]["Riverside Loft"], 1)
        self.assertEqual(summary["format_recency"]["Story"], 0)
        self.assertEqual(summary["format_recency"]["Carousel"], 1)
        self.assertEqual(summary["recent_hooks"], ["hook A", "hook B", "hook C"])

    def test_empty_history(self):
        summary = history.summarize([])
        self.assertEqual(summary["weeks_considered"], 0)
        self.assertEqual(summary["content_type_recency"], {})
        self.assertEqual(summary["recent_hooks"], [])


class TestRankByFreshness(unittest.TestCase):
    def test_never_used_ranks_before_used(self):
        items = ["used", "unused"]
        recency = {"used": 0}
        rng = random.Random(1)
        ranked = history.rank_by_freshness(items, lambda x: x, recency, rng)
        self.assertEqual(ranked[0], "unused")

    def test_used_longer_ago_ranks_before_used_recently(self):
        items = ["used_recently", "used_long_ago"]
        recency = {"used_recently": 0, "used_long_ago": 3}
        rng = random.Random(1)
        ranked = history.rank_by_freshness(items, lambda x: x, recency, rng)
        self.assertEqual(ranked[0], "used_long_ago")


class TestFreshnessWeight(unittest.TestCase):
    def test_never_used_has_highest_weight(self):
        recency = {"a": 0, "b": 3}
        self.assertGreater(history.freshness_weight("never_used", recency), history.freshness_weight("a", recency))
        self.assertGreater(history.freshness_weight("never_used", recency), history.freshness_weight("b", recency))

    def test_weight_increases_with_weeks_ago(self):
        recency = {"a": 0, "b": 3}
        self.assertGreater(history.freshness_weight("b", recency), history.freshness_weight("a", recency))


class TestWeightedSample(unittest.TestCase):
    def test_returns_k_distinct_items(self):
        rng = random.Random(42)
        items = ["a", "b", "c", "d"]
        weights = [1, 1, 1, 1]
        chosen = history.weighted_sample_without_replacement(items, weights, 3, rng)
        self.assertEqual(len(chosen), 3)
        self.assertEqual(len(set(chosen)), 3)
        for item in chosen:
            self.assertIn(item, items)


if __name__ == "__main__":
    unittest.main()
