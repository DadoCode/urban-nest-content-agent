"""
Automated publishability checks, plus the content-type feasibility gate
that keeps placeholder-only ideas out of the plan in the first place.

Two distinct moments matter here:

1. Feasibility (planning-time, preventative): is this content type even
   producible right now, given data we actually have? "Offers" and
   "Reviews" need a real confirmed offer / real guest quote to talk about —
   without one, they're not offered as candidates at all, rather than being
   generated as placeholder copy and caught afterward.

2. check_post() (post-generation): scans the actual generated copy for
   issues that slipped through anyway — placeholder wording, unsupported
   promotional claims, empty/generic CTAs, the hook/caption/CTA repeating
   the same idea verbatim, property facts that don't match the source
   record, and (once rendering has run) text the renderer had to shrink or
   truncate to avoid clipping.

check_post() returns one of three statuses:
  "ready"           — no issues.
  "needs_revision"  — minor/advisory issues; still usable as-is.
  "cannot_produce"  — a blocking issue; the caller should pick a different
                       idea rather than ship this one.

Property-fact grounding (see _check_property_facts) is deliberately simple:
no NLP, just structured lookups against the property catalogue we already
have — exact/substring matches for names, areas, types, and standout
features, plus small fixed keyword lists for a few claim categories
(balcony/outdoor space, gym, transport). The rule is: any specific,
checkable claim about a property must trace back to that property's own
record, or it's blocking.
"""

import re

PLACEHOLDER_MARKERS = ["placeholder", "tbd", "to be confirmed", "lorem ipsum", "xxx", "insert "]
PROMO_MARKERS = [
    "% off", "percent off", "discount", "promo code", "limited time offer",
    "flash sale", "sale ends", "half price", "half-price",
]
GENERIC_CTAS = {"click here", "learn more", "swipe up", "check it out", "find out more"}

# Content types that legitimately talk about a promotion/testimonial — these
# are exempt from the "unsupported claim" scan, since for them it's the point.
OFFER_BACKED_LABELS = {"Offers"}
REVIEW_BACKED_LABELS = {"Reviews"}

# Claim category -> keywords. If the copy uses any keyword from a category,
# the property's OWN standout_features must contain a keyword from that same
# category, or the claim isn't backed by anything in the source record.
AMENITY_CATEGORIES = {
    "balcony/outdoor space": ["balcony", "terrace", "courtyard", "garden", "outdoor space"],
    "gym/access": ["gym", "fitness suite", "fitness room"],
    "transport/walking time": ["walk to", "minute walk", "-minute walk", "station", " dlr", "tube", "underground"],
}

BEDROOM_PATTERN = re.compile(r"(\d+)[\s-]*bed(?:room)?s?\b")
SLEEPS_PATTERN = re.compile(r"sleep(?:s|ing)?\s+(\d+)")


def _contains_phrase(text: str, phrase: str) -> bool:
    """Word-boundary substring match. A plain `in` check would let a bare
    word like 'apartment' (one property's own type) spuriously match inside
    an unrelated compound token like the hashtag '#LondonApartments'."""
    return re.search(r"\b" + re.escape(phrase.lower()) + r"\b", text) is not None


def feasible_content_types(content_types: list[dict], brand: dict) -> list[dict]:
    """Filter out content types that need data we don't actually have yet.
    Once that data exists (brand['active_offers'] / brand['guest_reviews']
    is non-empty), the type becomes selectable again automatically — this
    is a data gate, not a permanent removal."""
    feasible = []
    for c in content_types:
        if c["label"] in OFFER_BACKED_LABELS and not brand.get("active_offers"):
            continue
        if c["label"] in REVIEW_BACKED_LABELS and not brand.get("guest_reviews"):
            continue
        feasible.append(c)
    return feasible


def _all_property_records() -> list[dict]:
    from mock_data import MOCK_PROPERTIES
    from real_properties import PROPERTIES as REAL_PROPERTIES

    return REAL_PROPERTIES + MOCK_PROPERTIES


def _same_catalog_records(record: dict) -> list[dict]:
    """Real and mock properties are two separate, unrelated catalogues —
    a mock property's area/name should never be treated as a 'different
    property' collision against a real property's copy, or vice versa."""
    from mock_data import MOCK_PROPERTIES
    from real_properties import PROPERTIES as REAL_PROPERTIES

    real_ids = {r["id"] for r in REAL_PROPERTIES}
    return REAL_PROPERTIES if record["id"] in real_ids else MOCK_PROPERTIES


def _find_property_record(property_id: str | None) -> dict | None:
    if not property_id:
        return None
    for record in _all_property_records():
        if record["id"] == property_id:
            return record
    return None


def _check_property_facts(all_text_lower: str, record: dict, flag) -> None:
    """Cross-checks every specific, checkable claim in all_text_lower
    against `record` (this post's own property) and the rest of its own
    catalogue (real vs. mock stay separate — see _same_catalog_records)."""
    catalog = _same_catalog_records(record)
    other_records = [r for r in catalog if r["id"] != record["id"]]
    own_features_text = " ".join(record["standout_features"]).lower()

    # Wrong property entirely.
    for other in other_records:
        if _contains_phrase(all_text_lower, other["name"]):
            flag("blocking", "unsupported_property_fact", f"Mentions '{other['name']}', a different property.")

    # Area/location claimed that belongs to a different known property.
    known_areas = {r["area"] for r in catalog}
    for area in known_areas:
        if area == record["area"]:
            continue
        if _contains_phrase(all_text_lower, area):
            flag(
                "blocking", "unsupported_property_fact",
                f"Mentions '{area}', which is not this property's area ({record['area']}).",
            )

    # Property type claimed that belongs to a different known property.
    # Skip a candidate that's actually just a substring of this property's
    # own correct type (e.g. bare "apartment" inside "modern apartment") —
    # that's not a wrong claim, it's the same claim worded more simply.
    known_types = {r["type"] for r in catalog}
    for type_name in known_types:
        if type_name == record["type"] or type_name in record["type"].lower():
            continue
        if _contains_phrase(all_text_lower, type_name):
            flag(
                "blocking", "unsupported_property_fact",
                f"Describes it as '{type_name}', but the record says {record['type']}.",
            )

    # Bedrooms / sleeps counts.
    m = BEDROOM_PATTERN.search(all_text_lower)
    if m and int(m.group(1)) != record["bedrooms"]:
        flag(
            "blocking", "unsupported_property_fact",
            f"Claims {m.group(1)} bedroom(s), but the record says {record['bedrooms']}.",
        )
    m = SLEEPS_PATTERN.search(all_text_lower)
    if m and int(m.group(1)) != record["sleeps"]:
        flag(
            "blocking", "unsupported_property_fact",
            f"Claims sleeping {m.group(1)}, but the record says {record['sleeps']}.",
        )

    # A standout feature that belongs to a different property.
    for other in other_records:
        for feature in other["standout_features"]:
            if _contains_phrase(all_text_lower, feature) and feature.lower() not in own_features_text:
                flag(
                    "blocking", "unsupported_property_fact",
                    f"Mentions '{feature}', a feature of {other['name']}, not this property.",
                )

    # Amenity-category claims (balcony/outdoor, gym, transport) not backed
    # by anything in this property's own standout_features.
    for category, keywords in AMENITY_CATEGORIES.items():
        claimed = any(_contains_phrase(all_text_lower, kw) for kw in keywords)
        supported = any(_contains_phrase(own_features_text, kw) for kw in keywords)
        if claimed and not supported:
            flag(
                "blocking", "unsupported_property_fact",
                f"Claims a {category} feature that isn't listed for this property.",
            )

    # Target/ideal guest type — softer field, so advisory rather than blocking.
    # Same subset exemption as the type check: a shorter "other" phrase that's
    # actually a substring of this property's own longer phrase (e.g. "business
    # travellers" inside this record's own "business travellers near Canary
    # Wharf") is the same claim worded more simply, not a wrong one.
    own_ideal_text = " ".join(record["ideal_for"]).lower()
    other_ideal_phrases = {
        p for r in other_records for p in r["ideal_for"]
        if p.lower() not in own_ideal_text
    }
    for phrase in other_ideal_phrases:
        if phrase.lower() in own_ideal_text:
            continue
        if _contains_phrase(all_text_lower, phrase):
            flag(
                "advisory", "unsupported_property_fact",
                f"Mentions '{phrase}' as an ideal guest type, which isn't listed for this property.",
            )


def check_post(post: dict) -> dict:
    issues: list[dict] = []

    def flag(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    text_fields = {
        "hook": post.get("hook") or "",
        "content_idea": post.get("content_idea") or "",
        "caption": post.get("caption") or "",
        "cta": post.get("cta") or "",
        "objective": post.get("objective") or "",
    }
    all_text = " ".join(text_fields.values()).lower()

    for marker in PLACEHOLDER_MARKERS:
        if marker in all_text:
            flag("blocking", "placeholder_text", f"Contains placeholder wording ('{marker.strip()}').")
            break

    if post.get("content_type") not in OFFER_BACKED_LABELS:
        for marker in PROMO_MARKERS:
            if marker in all_text:
                flag(
                    "blocking",
                    "unsupported_offer_claim",
                    f"Mentions '{marker.strip()}' but no confirmed offer backs this post.",
                )
                break

    cta = text_fields["cta"].strip()
    if len(cta) < 6:
        flag("blocking", "empty_cta", "CTA is missing or too short to be useful.")
    elif cta.lower().rstrip(".") in GENERIC_CTAS:
        flag("advisory", "generic_cta", f"CTA '{cta}' is generic — consider something more specific.")

    hook = text_fields["hook"].strip()
    caption = text_fields["caption"].strip()
    if hook and len(hook) > 12 and hook.lower() in caption.lower():
        flag("advisory", "repetition", "The hook is repeated verbatim inside the caption.")
    if hook and cta and hook.lower() == cta.lower():
        flag("advisory", "repetition", "The hook and CTA say exactly the same thing.")

    if post.get("property_id"):
        record = _find_property_record(post["property_id"])
        if record:
            # Overlay text gets rendered onto the actual photo, so it's a
            # real factual claim too — include it alongside the copy fields.
            va = post.get("visual_assets") or {}
            property_text_lower = all_text + " " + (va.get("overlay_text") or "").lower()
            _check_property_facts(property_text_lower, record, flag)
        if post.get("format") == "Carousel":
            va = post.get("visual_assets") or {}
            if not va.get("assets_selected"):
                flag("blocking", "no_assets_available", "No usable photos were found for this property.")

    for warning in post.get("_render_warnings", []) or []:
        flag("advisory", "text_overflow_shrunk", warning)

    blocking = [i for i in issues if i["severity"] == "blocking"]
    if blocking:
        status = "cannot_produce"
    elif issues:
        status = "needs_revision"
    else:
        status = "ready"

    return {"status": status, "issues": issues}
