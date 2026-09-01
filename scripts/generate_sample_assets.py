"""
Dev-only helper: generates placeholder JPG images for assets/<property_id>/
that match the checked-in metadata.json files, so the repo has something to
test image selection against without needing real property photos.

Not needed to run the agent — only needed if you want to regenerate the
sample images. Requires Pillow (`pip install pillow`), which is NOT a
runtime dependency of the agent itself.

Usage:
    python3 scripts/generate_sample_assets.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent.parent / "assets"

COLORS_BY_SHOT_TYPE = {
    "living_room": (194, 168, 130),
    "bedroom": (150, 176, 190),
    "kitchen": (176, 156, 156),
    "exterior": (120, 140, 120),
    "gym": (160, 120, 160),
    "garden": (120, 160, 120),
}


def make_placeholder(path: Path, label: str, shot_type: str) -> None:
    color = COLORS_BY_SHOT_TYPE.get(shot_type, (150, 150, 150))
    img = Image.new("RGB", (480, 320), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 469, 309], outline=(255, 255, 255), width=3)
    draw.text((20, 140), label, fill=(255, 255, 255))
    img.save(path, "JPEG")


def main():
    for property_dir in sorted(ASSETS_DIR.iterdir()):
        metadata_path = property_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        records = json.loads(metadata_path.read_text())
        for record in records:
            out_path = property_dir / record["filename"]
            label = f"{property_dir.name}\n{record['shot_type']}"
            make_placeholder(out_path, label, record["shot_type"])
            print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
