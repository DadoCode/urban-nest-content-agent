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


def _property_post(property_id="draycott", **overrides):
    """A Property Showcase post about a real property (Draycott Avenue by
    default: Chelsea, 1 bed, sleeps 4, split-level maisonette; features are
    a mantelpiece living area, a bedroom, and a walk to Sloane Square — no
    gym, balcony, or transport-DLR feature)."""
    post = {
        "content_type": "Property Showcase",
        "format": "Carousel",
        "property": "Draycott Avenue",
        "property_id": property_id,
        "hook": "Your next stay in Chelsea could look like this.",
        "content_idea": "Walkthrough-style tour of the split-level maisonette in Chelsea, London.",
        "caption": (
            "Say hello to Draycott Avenue — a split-level maisonette in Chelsea, London, "
            "sleeping 4. Perfect for couples, families, professionals, guests travelling with pets."
        ),
        "cta": "Tap the link in bio to check availability.",
        "objective": "Showcase Draycott Avenue to attract direct bookings.",
        "visual_assets": {"assets_selected": ["living_room_wide.jpg"], "overlay_text": None},
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


class TestPropertyFactGrounding(unittest.TestCase):
    """Deliberately incorrect claims about a real property (Draycott Avenue),
    one per fact category the agent might get wrong."""

    def test_accurate_property_post_is_ready(self):
        result = publishability.check_post(_property_post())
        self.assertEqual(result["status"], "ready", result["issues"])

    def test_wrong_property_name_is_blocking(self):
        post = _property_post(caption="Say hello to Eider Apartments, a lovely stay in Chelsea, sleeping 4.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_wrong_area_is_blocking(self):
        post = _property_post(hook="Your next stay in Limehouse could look like this.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_wrong_bedroom_count_is_blocking(self):
        post = _property_post(caption="A bright 2-bedroom maisonette in Chelsea, sleeping 4.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_wrong_sleeps_count_is_blocking(self):
        post = _property_post(caption="Say hello to Draycott Avenue, sleeping 8.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_wrong_property_type_is_blocking(self):
        post = _property_post(content_idea="A tour of this modern apartment in Chelsea.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_feature_borrowed_from_another_property_is_blocking(self):
        post = _property_post(
            content_idea="Enjoy the private wraparound balcony with views toward Canary Wharf and the docklands."
        )
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_unsupported_gym_claim_is_blocking(self):
        post = _property_post(hook="Start the day with on-site gym access before exploring Chelsea.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_unsupported_balcony_claim_is_blocking(self):
        post = _property_post(hook="Morning coffee on your own private balcony in Chelsea.")
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_unsupported_transport_claim_is_blocking_for_property_without_one(self):
        # Eider Apartments' own record has no walk/station/DLR feature at all.
        post = _property_post(
            property_id="pw", property="Eider Apartments",
            caption="Eider Apartments is a 5-minute walk to the nearest station.",
        )
        result = publishability.check_post(post)
        self.assertEqual(result["status"], "cannot_produce")
        self.assertTrue(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))

    def test_unsupported_ideal_guest_type_is_advisory_not_blocking(self):
        # "guests wanting a peaceful lakeside stay" is Eider Apartments' ideal_for
        # phrase, not Draycott's — and doesn't collide with any area/feature text.
        post = _property_post(content_idea="A great pick for guests wanting a peaceful lakeside stay.")
        result = publishability.check_post(post)
        issue = next(i for i in result["issues"] if i["code"] == "unsupported_property_fact")
        self.assertEqual(issue["severity"], "advisory")
        self.assertEqual(result["status"], "needs_revision")

    def test_correct_transport_claim_is_not_flagged(self):
        # Draycott Avenue's own record does have this exact feature.
        post = _property_post(content_idea="Just a 5-minute walk to Sloane Square station.")
        result = publishability.check_post(post)
        self.assertFalse(any(i["code"] == "unsupported_property_fact" for i in result["issues"]))


if __name__ == "__main__":
    unittest.main()
