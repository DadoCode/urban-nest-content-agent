"""
Urban Nest Estates — Instagram Content Agent (V2, local prototype)

Generates a plan of 3 varied Instagram posts for the week using local mock
data and local history only. No external integrations (no Google Drive,
Instagram API, n8n, or GitHub Actions). Optionally uses the Anthropic API for
planning + copywriting if ANTHROPIC_API_KEY is set in the environment;
otherwise runs fully offline with history-aware, freshness-weighted rules.

Usage:
    python main.py
    python main.py --week-of 2026-09-08   # override the week label (for demos/tests)
"""

import argparse
import json
import random
from datetime import date
from pathlib import Path

import history
from generator import generate_post
from mock_data import BRAND
from planner import build_weekly_decisions

OUTPUT_DIR = Path(__file__).parent / "output"


def build_weekly_plan(week_of: str | None = None, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    week_of = week_of or date.today().isoformat()

    recent_plans = history.load_recent_plans(before=week_of)
    history_summary = history.summarize(recent_plans)

    decisions = build_weekly_decisions(BRAND, history_summary, rng)

    posts = [
        generate_post(BRAND, d["content_type"], d["property"], history_summary, d["reason"], rng)
        for d in decisions
    ]

    return {
        "brand": BRAND["name"],
        "week_of": week_of,
        "posts": posts,
    }


def print_plan(plan: dict) -> None:
    print(f"\nWeekly Instagram Content Plan — {plan['brand']} — week of {plan['week_of']}\n")
    for i, post in enumerate(plan["posts"], start=1):
        print(f"POST {i}: {post['content_type']}  [{post['format']}]")
        if post["property"]:
            print(f"  Property: {post['property']}")
        print(f"  Reason:         {post['reason']}")
        print(f"  Objective:      {post['objective']}")
        print(f"  Content idea:   {post['content_idea']}")
        print(f"  Hook:           {post['hook']}")
        print(f"  Visual needed:  {post['visual_needed']}")
        print(f"  Caption:        {post['caption']}")
        print(f"  CTA:            {post['cta']}")
        if post.get("_generation_warning"):
            print(f"  [warning] {post['_generation_warning']}")
        if post.get("visual_assets"):
            print_visual_assets(post["visual_assets"])
        print()


def print_visual_assets(visual_assets: dict) -> None:
    print("  Visual assets:")
    if not visual_assets["assets_selected"]:
        print(f"    (none available) {visual_assets['missing_visual_notes']}")
        return
    print(f"    Order:   {' -> '.join(visual_assets['assets_selected'])}")
    print(f"    Cover:   {visual_assets['cover_asset']}")
    for filename in visual_assets["assets_selected"]:
        description = visual_assets["asset_descriptions"].get(filename, "")
        reason = visual_assets["asset_reasons"].get(filename, "")
        print(f"      - {filename}: {description}")
        print(f"          why: {reason}")
    print(f"    Overlay text: {visual_assets['overlay_text']}")
    print(f"    Missing:      {visual_assets['missing_visual_notes']}")


def save_plan(plan: dict) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"weekly_plan_{plan['week_of']}.json"
    out_path.write_text(json.dumps(plan, indent=2))
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate this week's Instagram content plan.")
    parser.add_argument(
        "--week-of",
        default=None,
        help="ISO date label for this week's plan (defaults to today). Useful for demos/tests.",
    )
    args = parser.parse_args()

    plan = build_weekly_plan(week_of=args.week_of)
    print_plan(plan)
    out_path = save_plan(plan)
    print(f"Saved plan to {out_path}")


if __name__ == "__main__":
    main()
