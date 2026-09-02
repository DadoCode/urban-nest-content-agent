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


def _find_property_record(property_id: str | None) -> dict | None:
    if not property_id:
        return None
    from mock_data import MOCK_PROPERTIES
    from real_properties import PROPERTIES as REAL_PROPERTIES

    for record in REAL_PROPERTIES + MOCK_PROPERTIES:
        if record["id"] == property_id:
            return record
    return None


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
            m = re.search(r"sleeping (\d+)", text_fields["caption"].lower())
            if m and int(m.group(1)) != record["sleeps"]:
                flag(
                    "blocking",
                    "unsupported_property_fact",
                    f"Caption says 'sleeping {m.group(1)}' but the property record says {record['sleeps']}.",
                )
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
