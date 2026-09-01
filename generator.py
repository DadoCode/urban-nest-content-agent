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

from history import describe_for_prompt, freshness_weight, rank_by_freshness, weighted_sample_without_replacement

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
        "Return ONLY valid JSON (no markdown fences) with exactly these string keys: "
        '"objective", "content_idea", "hook", "visual_needed", "caption", "cta". '
        "The caption should be 2-4 short sentences plus 3-5 relevant hashtags "
        f"including {' '.join(brand['hashtags_core'])}."
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
) -> dict:
    """Deterministic-ish, offline stand-in used when no ANTHROPIC_API_KEY is set."""
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
        return {
            "objective": f"Showcase {p['name']} to attract direct bookings.",
            "content_idea": f"Walkthrough-style tour of the {p['type']} in {p['area']}, {p['city']}.",
            "hook": hook,
            "visual_needed": (
                f"Photos/video of: {', '.join(p['standout_features'])}."
            ),
            "caption": (
                f"Say hello to {p['name']} — a {p['type']} in {p['area']}, {p['city']}, "
                f"sleeping {p['sleeps']}. Perfect for {', '.join(p['ideal_for'])}. "
                f"{hashtags}"
            ),
            "cta": "Tap the link in bio to check availability.",
        }

    templates = {
        "neighbourhood": {
            "objective": "Build local authority and inspire travel to our cities.",
            "content_idea": "Guide-style highlight of a neighbourhood in London.",
            "hooks": [
                "This is the area our guests keep asking to come back to.",
                "The neighbourhood everyone overlooks — and shouldn't.",
            ],
            "visual_needed": "Street-level photos/video of local cafes, shops, and transport links.",
            "caption": f"A local's guide to one of our favourite neighbourhoods. {hashtags}",
            "cta": "Save this post for your next trip.",
        },
        "travel_tips": {
            "objective": "Provide value to followers and position the brand as a travel expert.",
            "content_idea": "Practical tips for staying in London like a local.",
            "hooks": [
                "3 things every visitor wishes they knew sooner.",
                "The mistake most first-time visitors make.",
            ],
            "visual_needed": "Simple text-on-image carousel slides, no property footage needed.",
            "caption": f"A few tips to make your next trip smoother. {hashtags}",
            "cta": "Which tip is most useful? Let us know in the comments.",
        },
        "shortlet_vs_hotel": {
            "objective": "Educate the audience on the benefits of short-lets over hotels.",
            "content_idea": "Side-by-side comparison of short-let vs hotel stays.",
            "hooks": [
                "Same trip, more space, better value.",
                "Why more travellers are skipping hotels altogether.",
            ],
            "visual_needed": "Split-screen graphic or carousel comparing space/kitchen/cost.",
            "caption": f"Wondering whether to book a hotel or a short-let? Here's the difference. {hashtags}",
            "cta": "DM us to find the right stay for your trip.",
        },
        "corporate_longstay": {
            "objective": "Attract corporate and relocation bookings for longer stays.",
            "content_idea": "Highlight the ease of a 1-6 month corporate stay with us.",
            "hooks": [
                "Relocating for work shouldn't mean living out of a suitcase.",
                "A better way to do a work trip that lasts months, not nights.",
            ],
            "visual_needed": "Photos of a work-friendly setup (desk, fast wifi signage, quiet space).",
            "caption": f"Moving for work? We make longer stays feel like home. {hashtags}",
            "cta": "Message us about corporate rates.",
        },
        "landlord_facing": {
            "objective": "Attract landlords interested in short-let property management.",
            "content_idea": "Explain the benefits of letting your property with Urban Nest Estates.",
            "hooks": [
                "Your property, fully managed, zero hassle.",
                "What your property could be earning with the right management.",
            ],
            "visual_needed": "Clean graphic listing management benefits, no guest-facing photos.",
            "caption": f"Thinking about short-let management for your property? Let's talk. {hashtags}",
            "cta": "Send us a message to find out how it works.",
        },
        "reviews": {
            "objective": "Build trust and social proof.",
            "content_idea": "Feature a (placeholder) guest review as a quote graphic.",
            "hooks": [
                "Don't just take our word for it.",
                "This is what guests actually say after staying with us.",
            ],
            "visual_needed": "Simple quote-card graphic on brand background — no fabricated review text yet.",
            "caption": f"Guest experiences like this are why we do what we do. {hashtags}",
            "cta": "Book your stay and tell us about it.",
        },
        "seasonal": {
            "objective": "Stay culturally relevant and timely with the season.",
            "content_idea": "Tie current season/holidays to travel in London.",
            "hooks": [
                "This is the best time of year to visit.",
                "Here's what the city looks like right now.",
            ],
            "visual_needed": "Seasonal imagery of the city (lights, weather, events) — no specific property required.",
            "caption": f"There's something special about this time of year in the city. {hashtags}",
            "cta": "Plan your seasonal getaway — link in bio.",
        },
        "offers": {
            "objective": "Drive direct bookings through a promotional push.",
            "content_idea": "Promote a placeholder seasonal offer or discount.",
            "hooks": [
                "A limited-time reason to book your next stay.",
                "Worth booking before this one ends.",
            ],
            "visual_needed": "Bold offer graphic with clear terms placeholder — confirm real offer details before publishing.",
            "caption": f"Something special for our followers this week. {hashtags}",
            "cta": "Book now before the offer ends.",
        },
        "brand_lifestyle": {
            "objective": "Build brand personality and emotional connection.",
            "content_idea": "Lifestyle content around what it feels like to stay with us.",
            "hooks": [
                "Home, wherever you're headed.",
                "This is the feeling we're actually selling.",
            ],
            "visual_needed": "Warm lifestyle imagery — coffee, keys, cosy interior details, no specific unit required.",
            "caption": f"This is what a stay with us feels like. {hashtags}",
            "cta": "Follow along for more from Urban Nest Estates.",
        },
    }
    body = dict(templates[content_type["key"]])
    body["hook"] = _pick_hook(body.pop("hooks"), history_summary, rng)
    return body


def generate_post(
    brand: dict,
    content_type: dict,
    property_record: dict | None,
    history_summary: dict,
    reason: str,
    rng: random.Random | None = None,
) -> dict:
    rng = rng or random.Random()
    chosen_format = _pick_format(content_type, history_summary, rng)

    if os.environ.get("ANTHROPIC_API_KEY"):
        prompt = _build_prompt(brand, content_type, chosen_format, property_record, history_summary)
        try:
            body = _call_claude(prompt)
        except Exception as exc:  # network/parsing issues -> fall back, don't crash the run
            body = _template_fallback(brand, content_type, property_record, history_summary, rng)
            body["_generation_warning"] = f"Fell back to template (Claude call failed: {exc})"
    else:
        body = _template_fallback(brand, content_type, property_record, history_summary, rng)

    post = {
        "content_type": content_type["label"],
        "format": chosen_format,
        "property": property_record["name"] if property_record else None,
        "reason": reason,
    }
    post.update(body)
    return post
