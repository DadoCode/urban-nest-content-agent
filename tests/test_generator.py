import os
import random
import unittest
from unittest import mock

import generator
from mock_data import CONTENT_TYPES, MOCK_PROPERTIES as PROPERTIES

REQUIRED_KEYS = {"objective", "content_idea", "hook", "visual_needed", "caption", "cta", "reason", "format"}


def _empty_history():
    return {
        "weeks_considered": 0,
        "content_type_recency": {},
        "property_recency": {},
        "format_recency": {},
        "recent_hooks": [],
    }


@mock.patch.dict(os.environ, {}, clear=True)  # offline template path
class TestGeneratePost(unittest.TestCase):
    def test_property_post_has_all_fields_and_only_uses_given_property(self):
        content_type = next(c for c in CONTENT_TYPES if c["key"] == "property_showcase")
        property_record = PROPERTIES[0]
        post = generator.generate_post(
            {"name": "Urban Nest Estates", "cities": ["London"], "hashtags_core": ["#UrbanNestEstates"], "tone_of_voice": "warm"},
            content_type,
            property_record,
            _empty_history(),
            reason="test reason",
            rng=random.Random(0),
        )
        self.assertTrue(REQUIRED_KEYS.issubset(post.keys()))
        self.assertEqual(post["property"], property_record["name"])
        self.assertEqual(post["reason"], "test reason")
        # Grounding: no other property's name should appear in the generated copy.
        other_names = [p["name"] for p in PROPERTIES if p["id"] != property_record["id"]]
        for field in ("content_idea", "hook", "caption"):
            for name in other_names:
                self.assertNotIn(name, post[field])

    def test_non_property_post_has_no_property(self):
        content_type = next(c for c in CONTENT_TYPES if c["key"] == "travel_tips")
        post = generator.generate_post(
            {"name": "Urban Nest Estates", "cities": ["London"], "hashtags_core": ["#UrbanNestEstates"], "tone_of_voice": "warm"},
            content_type,
            None,
            _empty_history(),
            reason="test reason",
            rng=random.Random(0),
        )
        self.assertIsNone(post["property"])

    def test_hook_avoids_immediately_repeating_recent_hook(self):
        content_type = next(c for c in CONTENT_TYPES if c["key"] == "travel_tips")
        brand = {"name": "Urban Nest Estates", "cities": ["London"], "hashtags_core": ["#UrbanNestEstates"], "tone_of_voice": "warm"}

        first = generator.generate_post(brand, content_type, None, _empty_history(), "r", rng=random.Random(0))

        history_with_last_hook = _empty_history()
        history_with_last_hook["recent_hooks"] = [first["hook"]]
        second = generator.generate_post(brand, content_type, None, history_with_last_hook, "r", rng=random.Random(0))

        self.assertNotEqual(first["hook"], second["hook"])


if __name__ == "__main__":
    unittest.main()
