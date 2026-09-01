import os
import random
import unittest
from unittest import mock

import planner
from mock_data import PROPERTIES


def _empty_history():
    return {
        "weeks_considered": 0,
        "content_type_recency": {},
        "property_recency": {},
        "format_recency": {},
        "recent_hooks": [],
    }


@mock.patch.dict(os.environ, {}, clear=True)  # ensure offline fallback path (no ANTHROPIC_API_KEY)
class TestFallbackDecide(unittest.TestCase):
    def test_three_distinct_types_and_at_most_one_showcase(self):
        for seed in range(50):
            decisions = planner._fallback_decide(_empty_history(), random.Random(seed))
            self.assertEqual(len(decisions), 3)
            keys = [d["content_type"]["key"] for d in decisions]
            self.assertEqual(len(keys), len(set(keys)), f"seed {seed} produced duplicate types: {keys}")
            self.assertLessEqual(keys.count("property_showcase"), 1)

    def test_property_only_assigned_to_showcase(self):
        for seed in range(50):
            decisions = planner._fallback_decide(_empty_history(), random.Random(seed))
            for d in decisions:
                if d["content_type"]["key"] == "property_showcase":
                    self.assertIsNotNone(d["property"])
                    self.assertIn(d["property"], PROPERTIES)
                else:
                    self.assertIsNone(d["property"])

    def test_every_decision_has_a_reason(self):
        decisions = planner._fallback_decide(_empty_history(), random.Random(0))
        for d in decisions:
            self.assertTrue(d["reason"])

    def test_recently_used_type_is_favored_less_than_fresh_type(self):
        history_summary = _empty_history()
        history_summary["content_type_recency"] = {"Property Showcase": 0}  # used last week

        counts = {"property_showcase": 0, "reviews": 0}
        trials = 300
        for seed in range(trials):
            decisions = planner._fallback_decide(history_summary, random.Random(seed))
            keys = {d["content_type"]["key"] for d in decisions}
            if "property_showcase" in keys:
                counts["property_showcase"] += 1
            if "reviews" in keys:
                counts["reviews"] += 1

        # "reviews" (never used) should be picked meaningfully more often than
        # "property_showcase" (used last week), but the showcase should still
        # appear sometimes -- diversity is the default, not an absolute rule.
        self.assertGreater(counts["reviews"], counts["property_showcase"])
        self.assertGreater(counts["property_showcase"], 0)

    def test_recently_used_property_is_favored_less(self):
        history_summary = _empty_history()
        history_summary["property_recency"] = {"Riverside Loft": 0}  # used last week

        counts = {"Riverside Loft": 0}
        trials = 100
        for seed in range(trials):
            decisions = planner._fallback_decide(history_summary, random.Random(seed))
            for d in decisions:
                if d["content_type"]["key"] == "property_showcase":
                    counts[d["property"]["name"]] = counts.get(d["property"]["name"], 0) + 1

        showcased_total = sum(counts.values())
        if showcased_total:  # only meaningful if showcase was picked at least once
            self.assertLess(counts.get("Riverside Loft", 0), showcased_total)


if __name__ == "__main__":
    unittest.main()
