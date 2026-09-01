"""
Visual asset selection for property-based posts.

Local images live in assets/<property_id>/, alongside a metadata.json that
describes each file (shot_type, a short description, and a 1-5 quality
score). That metadata plays the same role for images that mock_data.py plays
for property facts: it's the only source of "what an image shows" that the
offline path is allowed to rely on, so it never invents visual content.

If ANTHROPIC_API_KEY is set, Claude actually looks at the images (vision)
to select, order, and critique them, using the metadata only as a hint it
can override. Otherwise a deterministic, metadata-driven heuristic picks the
strongest, most varied set. No images are generated here.
"""

import base64
import json
import mimetypes
import os
import random
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"
ANTHROPIC_MODEL = "claude-sonnet-5"

QUALITY_THRESHOLD = 3
MIN_ASSETS = 3
MAX_ASSETS = 4
PREFERRED_SHOT_ORDER = ["exterior", "garden", "living_room", "bedroom", "kitchen", "bathroom", "gym"]
CORE_SHOT_TYPES = ["exterior", "living_room", "bedroom", "kitchen"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_asset_records(property_id: str) -> list[dict]:
    """Load image records for a property: metadata entries whose file
    actually exists on disk, plus any image file present but not described
    in metadata.json (kept, but flagged as undescribed)."""
    property_dir = ASSETS_DIR / property_id
    if not property_dir.exists():
        return []

    metadata_path = property_dir / "metadata.json"
    metadata_by_filename = {}
    if metadata_path.exists():
        try:
            for entry in json.loads(metadata_path.read_text()):
                metadata_by_filename[entry["filename"]] = entry
        except (json.JSONDecodeError, OSError):
            pass

    records = []
    seen = set()
    for path in sorted(property_dir.iterdir()):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        entry = metadata_by_filename.get(path.name)
        if entry:
            records.append(
                {
                    "filename": path.name,
                    "path": path,
                    "shot_type": entry.get("shot_type", "other"),
                    "quality": entry.get("quality", 3),
                    "description": entry.get("description", ""),
                }
            )
        else:
            records.append(
                {
                    "filename": path.name,
                    "path": path,
                    "shot_type": "other",
                    "quality": 3,
                    "description": "No description available for this image.",
                }
            )
        seen.add(path.name)

    return records


def _missing_visual_notes(all_records: list[dict], selected: list[dict]) -> str | None:
    notes = []
    all_shot_types = {a["shot_type"] for a in all_records}
    missing_core = [s for s in CORE_SHOT_TYPES if s not in all_shot_types]
    if missing_core:
        notes.append(f"No {'/'.join(missing_core)} photo available — consider adding one.")

    weak = [a["filename"] for a in all_records if a["quality"] < QUALITY_THRESHOLD and a not in selected]
    if weak:
        notes.append(f"Skipped low-quality image(s): {', '.join(weak)}.")

    return " ".join(notes) if notes else None


def _pick_overlay_text(content_type_format: str, property_record: dict, hook: str) -> str | None:
    if content_type_format == "Reel concept":
        return hook if len(hook) <= 60 else hook[:57] + "..."

    if content_type_format == "Carousel":
        for feature in property_record["standout_features"]:
            if any(kw in feature.lower() for kw in ["walk", "minute", "station", "access"]):
                return feature.capitalize()
        return None

    return None


def _offline_select(
    property_record: dict,
    chosen_format: str,
    hook: str,
    asset_records: list[dict],
    rng: random.Random,
) -> dict:
    if not asset_records:
        return {
            "assets_selected": [],
            "cover_asset": None,
            "asset_reasons": {},
            "asset_descriptions": {},
            "overlay_text": None,
            "missing_visual_notes": (
                f"No image assets found for {property_record['name']} in "
                f"assets/{property_record['id']}/. Add a few photos (e.g. living room, "
                f"bedroom, exterior) to enable visual selection."
            ),
        }

    scored = sorted(asset_records, key=lambda a: (a["quality"], rng.random()), reverse=True)

    selected: list[dict] = []
    used_shot_types: set[str] = set()
    for asset in scored:
        if len(selected) >= MAX_ASSETS:
            break
        if asset["quality"] < QUALITY_THRESHOLD or asset["shot_type"] in used_shot_types:
            continue
        selected.append(asset)
        used_shot_types.add(asset["shot_type"])

    if len(selected) < min(MIN_ASSETS, len(asset_records)):
        for asset in scored:
            if len(selected) >= MIN_ASSETS or asset in selected:
                continue
            selected.append(asset)

    cover = max(selected, key=lambda a: a["quality"])

    def order_key(asset):
        try:
            return PREFERRED_SHOT_ORDER.index(asset["shot_type"])
        except ValueError:
            return len(PREFERRED_SHOT_ORDER)

    remaining = sorted((a for a in selected if a is not cover), key=order_key)
    ordered = [cover] + remaining

    reasons = {}
    descriptions = {}
    for asset in ordered:
        descriptions[asset["filename"]] = asset["description"]
        if asset is cover:
            reasons[asset["filename"]] = (
                f"Chosen as the cover/hero shot — the strongest available image "
                f"(quality {asset['quality']}/5, {asset['shot_type']})."
            )
        else:
            reasons[asset["filename"]] = (
                f"Adds a distinct '{asset['shot_type']}' view not covered by the other selected images."
            )

    return {
        "assets_selected": [a["filename"] for a in ordered],
        "cover_asset": cover["filename"],
        "asset_reasons": reasons,
        "asset_descriptions": descriptions,
        "overlay_text": _pick_overlay_text(chosen_format, property_record, hook),
        "missing_visual_notes": _missing_visual_notes(asset_records, selected),
    }


def _encode_image(path: Path) -> tuple[str, str]:
    media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return media_type, data


def _build_vision_message(
    brand: dict,
    property_record: dict,
    chosen_format: str,
    hook: str,
    asset_records: list[dict],
) -> list[dict]:
    hint_lines = "\n".join(
        f"- {a['filename']} (shot_type hint: {a['shot_type']}, quality hint: {a['quality']}/5): {a['description']}"
        for a in asset_records
    )
    instructions = (
        f"You are selecting visual assets for one Instagram {chosen_format} post for "
        f"{brand['name']} about the property '{property_record['name']}' ({property_record['area']}, "
        f"{property_record['city']}).\n\n"
        f"Post hook: {hook}\n\n"
        "Below are hints from our local catalogue (shot_type/quality/description), written before anyone "
        "looked at the actual images — treat them only as hints and correct them based on what you actually "
        "see in the attached images:\n"
        f"{hint_lines}\n\n"
        f"Look at each attached image and decide:\n"
        "- Which images are strong enough to use, and which are weak or too repetitive of another image.\n"
        f"- The best {'shot sequence for the Reel' if chosen_format == 'Reel concept' else 'slide order for the carousel'}.\n"
        "- Which single image should be the cover/hero.\n"
        "- Short overlay text ONLY if it would genuinely improve the post (often it won't — leave null "
        "if the images and caption already say enough).\n"
        "- Any visual content that's missing and would make the post stronger.\n\n"
        "Return ONLY valid JSON (no markdown fences) with exactly these keys: "
        '"assets_selected" (ordered list of filenames from the attached images, 2-4 items), '
        '"cover_asset" (one filename from assets_selected), '
        '"asset_reasons" (object mapping each selected filename to a one-sentence reason), '
        '"asset_descriptions" (object mapping each selected filename to a short factual description of '
        "what that image actually shows), "
        '"overlay_text" (string or null), '
        '"missing_visual_notes" (string or null).'
    )

    content = [{"type": "text", "text": instructions}]
    for asset in asset_records:
        media_type, data = _encode_image(asset["path"])
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            }
        )
        content.append({"type": "text", "text": f"^ this image is {asset['filename']}"})
    return content


def _call_claude_vision(brand, property_record, chosen_format, hook, asset_records) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    content = _build_vision_message(brand, property_record, chosen_format, hook, asset_records)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    text = response.content[0].text.strip()
    return json.loads(text)


def _validate_claude_result(raw: dict, asset_records: list[dict]) -> dict | None:
    valid_filenames = {a["filename"] for a in asset_records}
    selected = [f for f in raw.get("assets_selected", []) if f in valid_filenames]
    if not selected:
        return None
    cover = raw.get("cover_asset")
    if cover not in selected:
        cover = selected[0]

    return {
        "assets_selected": selected,
        "cover_asset": cover,
        "asset_reasons": {k: v for k, v in raw.get("asset_reasons", {}).items() if k in selected},
        "asset_descriptions": {k: v for k, v in raw.get("asset_descriptions", {}).items() if k in selected},
        "overlay_text": raw.get("overlay_text"),
        "missing_visual_notes": raw.get("missing_visual_notes"),
    }


def select_assets_for_post(
    brand: dict,
    property_record: dict,
    chosen_format: str,
    hook: str,
    rng: random.Random | None = None,
) -> dict:
    """Select, order, and critique visual assets for a property-based post.
    Returns a dict with assets_selected/cover_asset/asset_reasons/
    asset_descriptions/overlay_text/missing_visual_notes."""
    rng = rng or random.Random()
    asset_records = load_asset_records(property_record["id"])

    if os.environ.get("ANTHROPIC_API_KEY") and asset_records:
        try:
            raw = _call_claude_vision(brand, property_record, chosen_format, hook, asset_records)
            validated = _validate_claude_result(raw, asset_records)
            if validated is not None:
                return validated
        except Exception:
            pass  # fall through to offline heuristic

    return _offline_select(property_record, chosen_format, hook, asset_records, rng)
