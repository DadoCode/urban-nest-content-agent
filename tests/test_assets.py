import os
import random
import unittest
from unittest import mock

import assets
from mock_data import MOCK_PROPERTIES as PROPERTIES
from real_properties import PROPERTIES as REAL_PROPERTIES

RIVERSIDE_LOFT = next(p for p in PROPERTIES if p["id"] == "ldn-01")
DRAYCOTT_AVENUE = next(p for p in REAL_PROPERTIES if p["id"] == "draycott")


@mock.patch.dict(os.environ, {}, clear=True)  # offline heuristic path
class TestOfflineSelect(unittest.TestCase):
    def test_excludes_weak_and_duplicate_shot_type_images(self):
        # ldn-01 has: living_room_01 (q5), living_room_02 (q3, duplicate shot_type),
        # bedroom_01 (q4), kitchen_01 (q2, weak), exterior_01 (q4).
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertEqual(
            set(result["assets_selected"]),
            {"living_room_01.jpg", "bedroom_01.jpg", "exterior_01.jpg"},
        )
        self.assertNotIn("living_room_02.jpg", result["assets_selected"])
        self.assertNotIn("kitchen_01.jpg", result["assets_selected"])

    def test_cover_is_highest_quality_selected_image(self):
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertEqual(result["cover_asset"], "living_room_01.jpg")
        self.assertEqual(result["assets_selected"][0], result["cover_asset"])

    def test_missing_visual_notes_mentions_skipped_weak_image(self):
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertIn("kitchen_01.jpg", result["missing_visual_notes"])

    def test_every_selected_asset_has_a_reason_and_description(self):
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Carousel", "hook", rng=random.Random(0)
        )
        for filename in result["assets_selected"]:
            self.assertTrue(result["asset_reasons"][filename])
            self.assertTrue(result["asset_descriptions"][filename])

    def test_reel_overlay_uses_the_hook(self):
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Reel concept", "Your next stay could look like this.",
            rng=random.Random(0),
        )
        self.assertEqual(result["overlay_text"], "Your next stay could look like this.")

    def test_carousel_overlay_uses_non_visual_feature_when_available(self):
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, RIVERSIDE_LOFT, "Carousel", "hook", rng=random.Random(0)
        )
        # Riverside Loft's standout_features include a proximity fact ("5-minute walk to...")
        self.assertIsNotNone(result["overlay_text"])
        self.assertIn("station", result["overlay_text"].lower())

    def test_property_with_no_assets_folder_returns_empty_with_note(self):
        fake_property = {**RIVERSIDE_LOFT, "id": "does-not-exist"}
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, fake_property, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertEqual(result["assets_selected"], [])
        self.assertIsNone(result["cover_asset"])
        self.assertIsNotNone(result["missing_visual_notes"])

    def test_overlay_preserves_proper_noun_capitalisation(self):
        # Regression test: Draycott Avenue's feature is "5-minute walk to Sloane
        # Square station" — str.capitalize() used to lowercase "Sloane Square".
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, DRAYCOTT_AVENUE, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertEqual(result["overlay_text"], "5-minute walk to Sloane Square station")

    def test_overlay_skipped_when_no_short_qualifying_feature(self):
        long_feature_property = {
            **DRAYCOTT_AVENUE,
            "id": "does-not-exist",
            "standout_features": [
                "a very long-winded description of a walk to the nearest station that "
                "goes on for far too long to ever sit cleanly as a photo overlay"
            ],
        }
        result = assets.select_assets_for_post(
            {"name": "Urban Nest Estates"}, long_feature_property, "Carousel", "hook", rng=random.Random(0)
        )
        self.assertIsNone(result["overlay_text"])

    def test_sentence_case_does_not_lowercase_rest_of_string(self):
        self.assertEqual(
            assets._sentence_case("5-minute walk to Sloane Square station"),
            "5-minute walk to Sloane Square station",
        )
        self.assertEqual(assets._sentence_case("bright living area"), "Bright living area")


class TestLoadAssetRecords(unittest.TestCase):
    def test_loads_all_five_riverside_loft_images(self):
        records = assets.load_asset_records("ldn-01")
        filenames = {r["filename"] for r in records}
        self.assertEqual(
            filenames,
            {"living_room_01.jpg", "living_room_02.jpg", "bedroom_01.jpg", "kitchen_01.jpg", "exterior_01.jpg"},
        )

    def test_unknown_property_returns_empty(self):
        self.assertEqual(assets.load_asset_records("does-not-exist"), [])


if __name__ == "__main__":
    unittest.main()
