import random
import unittest

import publishability
from mock_data import CONTENT_TYPES


def _brand(active_offers=None, guest_reviews=None):
    return {
        "name": "Urban Nest Estates",
        "cities": ["London"],
        "active_offers": active_offers or [],
        "guest_reviews": guest_reviews or [],
    }


def _base_post(**overrides):
    post = {
        "content_type": "Travel tips",
        "format": "Normal post",
        "property": None,
        "property_id": None,
        "hook": "The one thing every first-time visitor gets wrong.",
        "content_idea": "Practical tips for getting around London.",
        "caption": "A few things that make getting around town easier.",
        "cta": "Which tip would help you most?",
        "objective": "Give followers something useful.",
    }
    post.update(overrides)
    return post


class TestFeasibleContentTypes(unittest.TestCase):
    def test_offers_and_reviews_excluded_when_no_real_data(self):
        feasible = publishability.feasible_content_types(CONTENT_TYPES, _brand())
        labels = {c["label"] for c in feasible}
        self.assertNotIn("Offers", labels)
        self.assertNotIn("Reviews", labels)
        # everything else should still be there
        self.assertIn("Property Showcase", labels)
        self.assertIn("Travel tips", labels)

    def test_offers_included_once_a_real_offer_exists(self):
        brand = _brand(active_offers=[{"description": "10% off stays booked in December"}])
        feasible = publishability.feasible_content_types(CONTENT_TYPES, brand)
        labels = {c["label"] for c in feasible}
        self.assertIn("Offers", labels)
        self.assertNotIn("Reviews", labels)  # still no real review


class TestCheckPost(unittest.TestCase):
    def test_clean_post_is_ready(self):
        result = publishability.check_post(_base_post())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["issues"], [])

    def test_placeholder_text_is_blocking(self):
        post = _base_post(content_idea="Promote a placeholder seasonal offer or discount.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "placeholder_text" for i in result["issues"]))

    def test_unsupported_promo_claim_is_blocking(self):
        post = _base_post(caption="Book now and get 20% off your stay this week.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_offer_claim" for i in result["issues"]))

    def test_promo_language_allowed_for_offer_backed_post(self):
        post = _base_post(content_type="Offers", caption="20% off this week only.")
        result = publishability.check_post(post)
        self.assertFalse(any(i["code"] == "unsupported_offer_claim" for i in result["issues"]))

    def test_empty_cta_is_blocking(self):
        post = _base_post(cta="")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "empty_cta" for i in result["issues"]))

    def test_generic_cta_is_advisory_not_blocking(self):
        post = _base_post(cta="Learn more")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "needs_revision")
        self.assertTrue(any(i["code"] == "generic_cta" for i in result["issues"]))

    def test_hook_repeated_in_caption_is_flagged(self):
        hook = "This is the exact same sentence repeated for no reason."
        post = _base_post(hook=hook, caption=f"{hook} #UrbanNestEstates")
        result = publishability.check_post(post)
        self.assertTrue(any(i["code"] == "repetition" for i in result["issues"]))

    def test_unsupported_sleeps_count_is_blocking(self):
        post = _base_post(
            property_id="draycott",
            caption="Say hello to Draycott Avenue, sleeping 12.",
        )
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_correct_sleeps_count_is_not_flagged(self):
        post = _base_post(
            property_id="draycott",
            caption="Say hello to Draycott Avenue, sleeping 4.",
        )
        result = publishability.check_post(post)
        self.assertFalse(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_property_carousel_with_no_assets_is_blocking(self):
        post = _base_post(
            property_id="draycott", format="Carousel",
            visual_assets={"assets_selected": [], "cover_asset": None},
        )
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "no_assets_available" for i in result["issues"]))

    def test_render_warning_becomes_advisory(self):
        post = _base_post(_render_warnings=["Headline was too long and had to be truncated to fit."])
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "needs_revision")
        self.assertTrue(any(i["code"] == "text_overflow_shrunk" for i in result["issues"]))


if __name__ == "__main__":
    unittest.main()
