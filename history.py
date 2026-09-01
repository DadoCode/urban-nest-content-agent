"""
Local content history.

Reuses the weekly plans already saved to output/weekly_plan_*.json as the
history store (no separate database/file format needed). Provides a summary
of what was used recently so the planner and generator can favor variety.

"Weeks ago" here is an ordinal rank among saved plans (0 = most recent saved
week, 1 = the one before that, ...), not a literal calendar distance.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_LOOKBACK_WEEKS = 4


def load_recent_plans(lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS, before: str | None = None) -> list[dict]:
    """Load up to `lookback_weeks` most recent saved plans, most recent first.

    If `before` (an ISO date string) is given, only plans strictly earlier than
    that date are included — so generating this week's plan never counts a
    plan already saved for this same week (or later) as "history".
    """
    if not OUTPUT_DIR.exists():
        return []

    plans = []
    for path in OUTPUT_DIR.glob("weekly_plan_*.json"):
        try:
            plan = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "week_of" not in plan or "posts" not in plan:
            continue
        if before is not None and plan["week_of"] >= before:
            continue
        plans.append(plan)

    plans.sort(key=lambda p: p["week_of"], reverse=True)
    return plans[:lookback_weeks]


def summarize(plans: list[dict]) -> dict:
    """Turn recent plans (most-recent-first) into recency stats: for each
    content type / property / format, the ordinal "weeks ago" it was last
    used, plus a flat list of recent hooks."""
    content_type_recency: dict[str, int] = {}
    property_recency: dict[str, int] = {}
    format_recency: dict[str, int] = {}
    recent_hooks: list[str] = []

    for weeks_ago, plan in enumerate(plans):
        for post in plan.get("posts", []):
            content_type = post.get("content_type")
            if content_type and content_type not in content_type_recency:
                content_type_recency[content_type] = weeks_ago

            prop = post.get("property")
            if prop and prop not in property_recency:
                property_recency[prop] = weeks_ago

            fmt = post.get("format")
            if fmt and fmt not in format_recency:
                format_recency[fmt] = weeks_ago

            hook = post.get("hook")
            if hook:
                recent_hooks.append(hook)

    return {
        "weeks_considered": len(plans),
        "content_type_recency": content_type_recency,
        "property_recency": property_recency,
        "format_recency": format_recency,
        "recent_hooks": recent_hooks[:12],
    }


def describe_for_prompt(summary: dict) -> str:
    """Render the history summary as compact text for an LLM prompt."""
    if summary["weeks_considered"] == 0:
        return "No prior weeks recorded yet — this is the first plan, so there is no repetition to avoid."

    def _fmt(recency_map: dict[str, int]) -> str:
        return ", ".join(
            f"{name} ({weeks_ago} week(s) ago)"
            for name, weeks_ago in sorted(recency_map.items(), key=lambda kv: kv[1])
        )

    lines = [f"History covers the last {summary['weeks_considered']} saved week(s)."]
    if summary["content_type_recency"]:
        lines.append(f"Content types used recently: {_fmt(summary['content_type_recency'])}.")
    if summary["property_recency"]:
        lines.append(f"Properties featured recently: {_fmt(summary['property_recency'])}.")
    if summary["format_recency"]:
        lines.append(f"Formats used recently: {_fmt(summary['format_recency'])}.")
    if summary["recent_hooks"]:
        lines.append(
            "Recent hooks (avoid repeating these or very similar phrasing): "
            + " | ".join(summary["recent_hooks"])
        )
    return "\n".join(lines)


def rank_by_freshness(items: list, key_fn, recency_map: dict[str, int], rng) -> list:
    """Sort items from freshest (never used, or used longest ago) to most
    recently used. Random jitter breaks ties instead of always resolving
    them the same way."""

    def sort_key(item):
        weeks_ago = recency_map.get(key_fn(item))
        if weeks_ago is None:
            return (0, 0, rng.random())
        return (1, -weeks_ago, rng.random())

    return sorted(items, key=sort_key)


def weighted_sample_without_replacement(items: list, weights: list[float], k: int, rng) -> list:
    """Pick k distinct items, biased by weight, without replacement. Every
    item with positive weight keeps a nonzero chance, so a repeat is always
    possible — just less likely than a fresher option."""
    items = list(items)
    weights = list(weights)
    chosen = []
    for _ in range(min(k, len(items))):
        total = sum(weights)
        r = rng.uniform(0, total)
        upto = 0.0
        for i, w in enumerate(weights):
            upto += w
            if upto >= r:
                chosen.append(items.pop(i))
                weights.pop(i)
                break
    return chosen


def freshness_weight(key: str, recency_map: dict[str, int]) -> float:
    """Higher weight = more likely to be picked. Weight grows with how long
    ago an item was last used (weeks_ago), so something used further back is
    treated as fresher; never-used items get the highest weight of all. A
    just-used item still gets a small nonzero weight, so a repeat stays
    possible when there's no fresher alternative."""
    weeks_ago = recency_map.get(key)
    if weeks_ago is None:
        oldest = max(recency_map.values(), default=0)
        return float(oldest + 2)
    return float(weeks_ago + 1)
