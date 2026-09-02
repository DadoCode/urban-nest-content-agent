"""
Turns a chosen content type (+ optional property) into a fully written
Instagram post plan: objective, idea, hook, visual needed, caption, CTA.

If ANTHROPIC_API_KEY is set in the environment, Claude is used to write the
creative copy. Otherwise a deterministic template fallback is used, so the
agent is fully testable offline with no API key.

Grounding rule: when a property is involved, the model/template is only
given that property's own record from mock_data.py and is explicitly told
not to add any facts beyond it.

History-awareness: the post format is chosen with a freshness bias against
recently-used formats, and offline-mode hooks are picked from a small set of
variants favoring the one used longest ago (or never), so consecutive weeks
don't read identically even without the Claude path.
"""

import json
import os
import random
from datetime import date

import assets
from history import describe_for_prompt, freshness_weight, rank_by_freshness, weighted_sample_without_replacement
from real_properties import PROPERTIES as REAL_PROPERTIES

REAL_AREAS = sorted({p["area"] for p in REAL_PROPERTIES})

ANTHROPIC_MODEL = "claude-sonnet-5"


def _format_property_facts(property_record: dict) -> str:
    p = property_record
    features = "; ".join(p["standout_features"])
    ideal_for = ", ".join(p["ideal_for"])
    return (
        f"Name: {p['name']}\n"
        f"City / area: {p['city']}, {p['area']}\n"
        f"Type: {p['type']}\n"
        f"Bedrooms: {p['bedrooms']} (sleeps {p['sleeps']})\n"
        f"Standout features: {features}\n"
        f"Ideal for: {ideal_for}"
    )


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _pick_format(content_type: dict, history_summary: dict, rng: random.Random) -> str:
    formats = content_type["typical_formats"]
    weights = [freshness_weight(f, history_summary["format_recency"]) for f in formats]
    return weighted_sample_without_replacement(formats, weights, 1, rng)[0]


def _build_prompt(
    brand: dict,
    content_type: dict,
    chosen_format: str,
    property_record: dict | None,
    history_summary: dict,
) -> str:
    lines = [
        f"You are writing one Instagram post plan for {brand['name']}, a short-let "
        f"apartment company operating in {', '.join(brand['cities'])}.",
        f"Brand tone of voice: {brand['tone_of_voice']}",
        f"Content type for this post: {content_type['label']}",
        f"Post format: {chosen_format}",
        f"Recent history:\n{describe_for_prompt(history_summary)}",
    ]

    if property_record is not None:
        lines.append(
            "This post is about ONE specific real property from our mock database. "
            "Use ONLY the facts listed below. Do NOT invent any additional details "
            "about the property (no made-up prices, amenities, distances, or reviews):\n"
            + _format_property_facts(property_record)
        )
    else:
        lines.append(
            "This post is NOT about a specific property. Do not invent or reference "
            "any specific property, price, or guest review as fact."
        )

    lines.append(
        "Write a fresh hook and content idea — do not reuse the recent hooks listed above "
        "or very similar phrasing/topics."
    )

    lines.append(
        "Copy quality bar: avoid generic AI-sounding filler — be specific and concrete, not vague. "
        "The hook, caption, and CTA must each say something different; do not restate the hook inside "
        "the caption, and do not make the CTA just repeat the hook. Never state or imply a discount, "
        "promotion, or limited-time offer unless one is explicitly given to you above as a confirmed "
        "fact — if none is given, don't invent one."
    )

    lines.append(
        "Return ONLY valid JSON (no markdown fences) with exactly these string keys: "
        '"objective", "content_idea", "hook", "visual_needed", "caption", "cta". '
        "The caption should be 2-4 short sentences plus 3-5 relevant, specific hashtags "
        f"(always include {' '.join(brand['hashtags_core'])}, and add a location/topic hashtag only "
        "when it's genuinely relevant — don't pad with generic tags)."
    )
    return "\n\n".join(lines)


def _call_claude(prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    return json.loads(text)


def _pick_hook(variants: list[str], history_summary: dict, rng: random.Random) -> str:
    """Prefer whichever variant was used longest ago (or never), so offline
    mode doesn't repeat the same hook every time this content type comes up."""
    recency: dict[str, int] = {}
    for i, hook in enumerate(history_summary.get("recent_hooks", [])):
        if hook not in recency:
            recency[hook] = i
    ranked = rank_by_freshness(variants, lambda h: h, recency, rng)
    return ranked[0]


def _template_fallback(
    brand: dict,
    content_type: dict,
    property_record: dict | None,
    history_summary: dict,
    rng: random.Random,
    week_of: str | None = None,
) -> dict:
    """Deterministic-ish, offline stand-in used when no ANTHROPIC_API_KEY is set.

    Note: "Offers" and "Reviews" have no template here on purpose — they're
    gated out by publishability.feasible_content_types() before generation
    is ever reached, since we have no confirmed real offer/review to talk
    about. If this function is ever called with one of those keys, that's a
    bug in the gate, and a loud KeyError is safer than silently producing
    placeholder copy.
    """
    hashtags = " ".join(brand["hashtags_core"])

    if property_record is not None:
        p = property_record
        hook = _pick_hook(
            [
                f"Your next stay in {p['area']} could look like this.",
                f"Meet {p['name']} — the {p['type']} guests keep coming back to.",
            ],
            history_summary,
            rng,
        )
        area_tag = "#" + p["area"].replace(" ", "").replace("-", "")
        return {
            "objective": f"Showcase {p['name']} to attract direct bookings.",
            "content_idea": f"Walkthrough-style tour of the {p['type']} in {p['area']}, {p['city']}.",
            "hook": hook,
            "visual_needed": (
                f"Photos/video of: {', '.join(p['standout_features'])}."
            ),
            "caption": (
                f"Say hello to {p['name']} — {_article(p['type'])} {p['type']} in {p['area']}, {p['city']}, "
                f"sleeping {p['sleeps']}. Perfect for {', '.join(p['ideal_for'])}. "
                f"{hashtags} {area_tag}"
            ),
            "cta": "Tap the link in bio to check availability.",
        }

    area = rng.choice(REAL_AREAS)
    month = date.fromisoformat(week_of).strftime("%B") if week_of else date.today().strftime("%B")

    templates = {
        "neighbourhood": {
            "objective": f"Build local authority around {area}, one of the areas we operate in.",
            "content_idea": f"Guide-style highlight of {area}: what's actually worth a visitor's time.",
            "hooks": [
                f"What a weekend in {area} actually looks like.",
                f"{area}, the way someone who lives there would show you.",
            ],
            "visual_needed": f"Street-level photos/video of {area} — cafes, shopfronts, transport links.",
            "caption": f"A local's take on {area}: where to eat, walk, and catch the train.",
            "cta": "Save this for your next trip.",
        },
        "travel_tips": {
            "objective": "Give followers something genuinely useful, not just a booking pitch.",
            "content_idea": "Three practical tips for getting around London without wasting a day of the trip.",
            "hooks": [
                "The one thing every first-time visitor gets wrong about the Tube.",
                "Three things that make a London trip run smoother.",
            ],
            "visual_needed": "Simple, uncluttered text-on-image slides — no property footage needed.",
            "caption": "A few things that make getting around town easier — worth saving before you land.",
            "cta": "Which tip would help you most? Tell us below.",
        },
        "shortlet_vs_hotel": {
            "objective": "Make the concrete case for a short-let over a hotel room, without overselling.",
            "content_idea": "A side-by-side look at what you get with a short-let that a hotel room can't offer.",
            "hooks": [
                "A hotel room can't do this.",
                "Here's what you give up when you book a hotel instead.",
            ],
            "visual_needed": "Split-screen or side-by-side graphic comparing kitchen, space, and layout.",
            "caption": "A full kitchen, a proper living room, and room to actually unpack — a hotel room can't match that.",
            "cta": "DM us if you're deciding between the two.",
        },
        "corporate_longstay": {
            "objective": "Speak directly to a corporate/relocating guest weighing a longer stay.",
            "content_idea": "What a 1-6 month corporate stay with us actually includes, day to day.",
            "hooks": [
                "Relocating for work doesn't have to mean living out of a suitcase.",
                "A month-long stay that still feels like your own place.",
            ],
            "visual_needed": "Photos of a genuinely work-friendly setup: desk, storage, a quiet corner.",
            "caption": "A dedicated workspace, proper storage, and a lease that flexes with the assignment.",
            "cta": "Message us about corporate rates.",
        },
        "landlord_facing": {
            "objective": "Speak to a property owner evaluating short-let management, not a guest.",
            "content_idea": "What a property owner actually gets when they let with Urban Nest Estates.",
            "hooks": [
                "Your property, managed the way you'd manage it yourself.",
                "What good short-let management actually looks like day to day.",
            ],
            "visual_needed": "A clean, text-led graphic — no guest-facing photos needed here.",
            "caption": "Professional cleaning, guest vetting, and upkeep — handled, so you don't have to think about it.",
            "cta": "Send us a message to find out how it works.",
        },
        "seasonal": {
            "objective": f"Stay timely by tying content to {month} specifically, not a vague 'this time of year.'",
            "content_idea": f"What {month} actually feels like in London, for anyone planning a visit.",
            "hooks": [
                f"What {month} in London actually feels like.",
                f"Why {month} is one of the better times to visit.",
            ],
            "visual_needed": f"Seasonal imagery for {month} — weather, light, what's on in the city.",
            "caption": f"{month} has its own rhythm in the city — here's what to expect if you're visiting.",
            "cta": "Plan your visit — link in bio.",
        },
        "brand_lifestyle": {
            "objective": "Build an emotional, specific moment rather than a generic mood board.",
            "content_idea": "A lifestyle moment built around the first few minutes after check-in.",
            "hooks": [
                "The five minutes after check-in, when it stops feeling like a rental.",
                "What staying with us feels like, not just looks like.",
            ],
            "visual_needed": "Warm, specific lifestyle imagery — keys on a counter, coffee, unpacking — not a stock mood shot.",
            "caption": "The best part of a short-let isn't the photos — it's how fast the place starts to feel like yours.",
            "cta": "Follow along for more from Urban Nest Estates.",
        },
    }
    body = dict(templates[content_type["key"]])
    body["hook"] = _pick_hook(body.pop("hooks"), history_summary, rng)
    body["caption"] = f"{body['caption']} {hashtags}"
    return body


def generate_post(
    brand: dict,
    content_type: dict,
    property_record: dict | None,
    history_summary: dict,
    reason: str,
    rng: random.Random | None = None,
    week_of: str | None = None,
) -> dict:
    rng = rng or random.Random()
    chosen_format = _pick_format(content_type, history_summary, rng)

    if os.environ.get("ANTHROPIC_API_KEY"):
        prompt = _build_prompt(brand, content_type, chosen_format, property_record, history_summary)
        try:
            body = _call_claude(prompt)
        except Exception as exc:  # network/parsing issues -> fall back, don't crash the run
            body = _template_fallback(brand, content_type, property_record, history_summary, rng, week_of)
            body["_generation_warning"] = f"Fell back to template (Claude call failed: {exc})"
    else:
        body = _template_fallback(brand, content_type, property_record, history_summary, rng, week_of)

    post = {
        "content_type": content_type["label"],
        "format": chosen_format,
        "property": property_record["name"] if property_record else None,
        "property_id": property_record["id"] if property_record else None,
        "reason": reason,
    }
    post.update(body)

    post["visual_assets"] = (
        assets.select_assets_for_post(brand, property_record, chosen_format, post["hook"], rng)
        if property_record is not None
        else None
    )
    return post
