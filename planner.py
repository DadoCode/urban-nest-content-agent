"""
Weekly content-type planner.

Picks 3 content types for the week from CONTENT_TYPES, guaranteeing variety:
at most one of the three posts is a property showcase, and all three types
are distinct.
"""

import random

from mock_data import CONTENT_TYPES, PROPERTIES


def pick_weekly_content_types(rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.Random()

    showcase = next(c for c in CONTENT_TYPES if c["key"] == "property_showcase")
    others = [c for c in CONTENT_TYPES if c["key"] != "property_showcase"]

    chosen_others = rng.sample(others, 2)
    include_showcase = rng.random() < 0.6  # showcase appears most weeks, not every week

    if include_showcase:
        selected = [showcase] + chosen_others
    else:
        third = rng.sample([c for c in others if c not in chosen_others], 1)
        selected = chosen_others + third

    rng.shuffle(selected)
    return selected


def pick_property_for_showcase(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    return rng.choice(PROPERTIES)
