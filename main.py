"""
Urban Nest Estates — Instagram Content Agent (V1, local prototype)

Generates a plan of 3 varied Instagram posts for the week using local mock
data only. No external integrations (no Google Drive, Instagram API, n8n,
or GitHub Actions). Optionally uses the Anthropic API for copywriting if
ANTHROPIC_API_KEY is set in the environment; otherwise runs fully offline
with template-based content.

Usage:
    python main.py
"""

import json
import random
from datetime import date
from pathlib import Path

from generator import generate_post
from mock_data import BRAND
from planner import pick_property_for_showcase, pick_weekly_content_types

OUTPUT_DIR = Path(__file__).parent / "output"


def build_weekly_plan(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    content_types = pick_weekly_content_types(rng)

    posts = []
    for content_type in content_types:
        property_record = (
            pick_property_for_showcase(rng) if content_type["requires_property"] else None
        )
        posts.append(generate_post(BRAND, content_type, property_record, rng))

    return {
        "brand": BRAND["name"],
        "week_of": date.today().isoformat(),
        "posts": posts,
    }


def print_plan(plan: dict) -> None:
    print(f"\nWeekly Instagram Content Plan — {plan['brand']} — week of {plan['week_of']}\n")
    for i, post in enumerate(plan["posts"], start=1):
        print(f"POST {i}: {post['content_type']}  [{post['format']}]")
        if post["property"]:
            print(f"  Property: {post['property']}")
        print(f"  Objective:      {post['objective']}")
        print(f"  Content idea:   {post['content_idea']}")
        print(f"  Hook:           {post['hook']}")
        print(f"  Visual needed:  {post['visual_needed']}")
        print(f"  Caption:        {post['caption']}")
        print(f"  CTA:            {post['cta']}")
        if post.get("_generation_warning"):
            print(f"  [warning] {post['_generation_warning']}")
        print()


def save_plan(plan: dict) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"weekly_plan_{plan['week_of']}.json"
    out_path.write_text(json.dumps(plan, indent=2))
    return out_path


def main():
    plan = build_weekly_plan()
    print_plan(plan)
    out_path = save_plan(plan)
    print(f"Saved plan to {out_path}")


if __name__ == "__main__":
    main()
