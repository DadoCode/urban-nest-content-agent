"""
Weekly content decision-making.

Decides WHAT to post about this week (3 posts: content type + property, if
any) — the actual copywriting happens later in generator.py. Guarantees:
all 3 content types are distinct, and at most one is a property showcase.

Beyond that, decisions are history-aware: recently used content types,
properties, and formats are disfavored (not forbidden) so weeks stay varied
by default while still allowing a deliberate repeat.

If ANTHROPIC_API_KEY is set, Claude makes the actual call, given the content
catalogue, content-mix guidance, and a summary of recent history. Its output
is validated against the hard constraints above; anything invalid is dropped
and backfilled using the same offline heuristic used when there's no API key,
so the run never breaks because of a malformed model response.
"""

import json
import os
import random

import publishability
from history import describe_for_prompt, freshness_weight, rank_by_freshness, weighted_sample_without_replacement
from mock_data import CONTENT_MIX_GUIDANCE, CONTENT_TYPES
from real_properties import PROPERTIES

ANTHROPIC_MODEL = "claude-sonnet-5"

_TYPES_BY_KEY = {c["key"]: c for c in CONTENT_TYPES}
_PROPERTIES_BY_ID = {p["id"]: p for p in PROPERTIES}


def _pick_property(recency_map: dict[str, int], rng: random.Random, reason_prefix: str = "") -> tuple[dict, str]:
    ranked = rank_by_freshness(PROPERTIES, lambda p: p["name"], recency_map, rng)
    chosen = ranked[0]
    weeks_ago = recency_map.get(chosen["name"])
    if weeks_ago is None:
        reason = f"{reason_prefix}featuring {chosen['name']}, which hasn't appeared in recent history."
    else:
        reason = (
            f"{reason_prefix}featuring {chosen['name']} again since the other properties "
            f"were shown more recently."
        )
    return chosen, reason


def _fallback_decide(
    history_summary: dict,
    rng: random.Random,
    exclude_keys: set[str] | None = None,
    feasible_types: list[dict] | None = None,
) -> list[dict]:
    """Offline, deterministic-ish decision: weighted-random by freshness."""
    exclude_keys = exclude_keys or set()
    pool = feasible_types if feasible_types is not None else CONTENT_TYPES
    ct_recency = history_summary["content_type_recency"]
    prop_recency = history_summary["property_recency"]

    candidates = [c for c in pool if c["key"] not in exclude_keys]
    weights = [freshness_weight(c["label"], ct_recency) for c in candidates]
    picked_types = weighted_sample_without_replacement(candidates, weights, min(3, len(candidates)), rng)

    # Enforce: at most one property_showcase among the picks.
    showcases = [c for c in picked_types if c["key"] == "property_showcase"]
    if len(showcases) > 1:
        keep = rng.choice(showcases)
        non_showcase_pool = [c for c in candidates if c["key"] != "property_showcase" and c not in picked_types]
        replacements = weighted_sample_without_replacement(
            non_showcase_pool,
            [freshness_weight(c["label"], ct_recency) for c in non_showcase_pool],
            len(showcases) - 1,
            rng,
        )
        picked_types = [c for c in picked_types if c["key"] != "property_showcase" or c == keep] + replacements

    decisions = []
    for content_type in picked_types:
        weeks_ago = ct_recency.get(content_type["label"])
        if weeks_ago is None:
            reason = f"'{content_type['label']}' hasn't appeared in recent history, keeping this week varied."
        else:
            reason = (
                f"Repeating '{content_type['label']}' (last used {weeks_ago} week(s) ago in this history) "
                f"since fresher options were used more recently."
            )

        property_record = None
        if content_type["requires_property"]:
            property_record, prop_reason = _pick_property(prop_recency, rng, reason_prefix="Also ")
            reason = f"{reason} {prop_reason}"

        decisions.append({"content_type": content_type, "property": property_record, "reason": reason})

    return decisions


def _build_decision_prompt(brand: dict, history_summary: dict, feasible_types: list[dict]) -> str:
    type_lines = "\n".join(
        f"- {c['key']}: {c['label']} (bucket: {c['bucket']}, requires_property: {c['requires_property']})"
        for c in feasible_types
    )
    property_lines = "\n".join(
        f"- {p['id']}: {p['name']} ({p['area']}, {p['city']}, {p['type']})" for p in PROPERTIES
    )

    return "\n\n".join(
        [
            f"You are planning next week's Instagram content mix for {brand['name']}, "
            f"a short-let apartment company in {', '.join(brand['cities'])}.",
            f"Content-mix guidance: {CONTENT_MIX_GUIDANCE}",
            f"Available content types:\n{type_lines}",
            f"Available properties (only relevant for property_showcase):\n{property_lines}",
            f"Recent history:\n{describe_for_prompt(history_summary)}",
            "Choose exactly 3 posts for next week.\n"
            "Hard requirements:\n"
            "- All 3 content_type_key values must be different.\n"
            "- At most 1 of the 3 can be property_showcase.\n"
            "Guidance (not hard rules):\n"
            "- Default to variety: avoid content types, properties, and topics used recently.\n"
            "- Repeating something recent is fine when there's a genuinely good reason — "
            "explain that reason if you do.\n"
            "- The content-mix guidance above is a helpful default, not a formula you must "
            "follow every week.",
            "Return ONLY valid JSON (no markdown fences): a list of exactly 3 objects, each with "
            'keys "content_type_key" (one of the keys above), "property_id" (a valid id from the '
            'property list above if and only if content_type_key is "property_showcase", otherwise '
            'null), and "reason" (one short sentence grounded in the available content and the '
            "history above).",
        ]
    )


def _call_claude(prompt: str) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    return json.loads(text)


def _validate_claude_decisions(
    raw: list[dict], history_summary: dict, rng: random.Random, feasible_types: list[dict]
) -> list[dict]:
    """Turn Claude's raw picks into validated decisions, dropping anything
    that breaks the hard constraints — including a pick that isn't
    currently feasible (e.g. Claude proposes "Offers" despite the prompt
    not listing it) — and backfilling from the offline heuristic so the
    run always ends up with exactly 3 valid posts."""
    feasible_keys = {c["key"] for c in feasible_types}
    decisions = []
    used_keys: set[str] = set()
    showcase_used = False

    for item in raw:
        key = item.get("content_type_key")
        content_type = _TYPES_BY_KEY.get(key)
        if content_type is None or key not in feasible_keys or key in used_keys:
            continue
        if content_type["key"] == "property_showcase" and showcase_used:
            continue

        property_record = None
        if content_type["requires_property"]:
            property_id = item.get("property_id")
            property_record = _PROPERTIES_BY_ID.get(property_id)
            if property_record is None:
                property_record, _ = _pick_property(history_summary["property_recency"], rng)

        reason = item.get("reason") or f"Selected '{content_type['label']}' for this week."

        decisions.append({"content_type": content_type, "property": property_record, "reason": reason})
        used_keys.add(key)
        if content_type["key"] == "property_showcase":
            showcase_used = True

        if len(decisions) == 3:
            break

    if len(decisions) < 3:
        exclude = used_keys | ({"property_showcase"} if showcase_used else set())
        decisions += _fallback_decide(
            history_summary, rng, exclude_keys=exclude, feasible_types=feasible_types
        )[: 3 - len(decisions)]

    return decisions


def build_weekly_decisions(brand: dict, history_summary: dict, rng: random.Random | None = None) -> list[dict]:
    """Return exactly 3 decisions: [{content_type, property, reason}, ...]."""
    rng = rng or random.Random()
    feasible_types = publishability.feasible_content_types(CONTENT_TYPES, brand)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            prompt = _build_decision_prompt(brand, history_summary, feasible_types)
            raw = _call_claude(prompt)
            return _validate_claude_decisions(raw, history_summary, rng, feasible_types)
        except Exception:
            pass  # fall through to offline heuristic

    return _fallback_decide(history_summary, rng, feasible_types=feasible_types)


def pick_replacement_decision(
    brand: dict, history_summary: dict, rng: random.Random, exclude_keys: set[str]
) -> dict | None:
    """Used when a generated post turns out to be unproducible (see
    publishability.check_post): picks one alternative decision, excluding
    whatever's already been used or just failed."""
    feasible_types = publishability.feasible_content_types(CONTENT_TYPES, brand)
    decisions = _fallback_decide(history_summary, rng, exclude_keys=exclude_keys, feasible_types=feasible_types)
    return decisions[0] if decisions else None
