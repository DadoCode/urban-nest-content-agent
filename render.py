"""
Renders finished, ready-to-use post assets from a generated weekly plan.

- Property carousel posts: real photos are cropped/resized (a copy — the
  originals in assets/ are never modified) to a consistent Instagram size,
  with a text overlay only on the cover slide, and only if the plan calls
  for one.
- Story / normal-post text-led content (no property involved): a finished
  branded graphic is composed from the plan's own hook/content idea/CTA —
  nothing invented beyond what's already in the plan.
- Reel concepts: no video. A plain-text shot list/storyboard is written
  instead, using the selected assets' order and descriptions when the reel
  is about a property, or the plan's own visual direction when it isn't.

Every rendered post folder also gets a caption.txt with the final caption.
"""

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import assets

OUTPUT_POSTS_DIR = Path(__file__).parent / "output" / "posts"

CAROUSEL_SIZE = (1080, 1350)  # 4:5, Instagram's recommended feed/carousel size
STORY_SIZE = (1080, 1920)  # 9:16
SQUARE_SIZE = (1080, 1080)  # 1:1, for normal-post graphics

# Urban Nest Estates' real brand palette, taken from their site's own
# CSS custom properties (urbannestestates.co.uk/css/styles.css), including
# their own usage notes: brass is their editorial accent/hairlines/labels
# color, clay is reserved for actions (buttons/CTAs) only, and pine is their
# primary brand color (also the site's theme-color) used for structure/dark
# bands/footer.
PAPER = (250, 246, 240)  # --ivory
INK = (35, 43, 39)  # --ink
INK_SOFT = (91, 101, 95)  # --stone
BRASS = (178, 153, 108)  # --brass (labels, hairlines, wordmark)
CLAY = (164, 65, 63)  # --clay (action only — CTAs)
PINE = (34, 57, 47)  # --pine (structure, dark bands, footer)

FOOTER_BAND_RATIO = 0.085

_SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]
_SANS_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _find_font_path(candidates: list[str]) -> str | None:
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    path = _find_font_path(candidates)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _serif(size: int) -> ImageFont.FreeTypeFont:
    return _font(_SERIF_CANDIDATES, size)


def _sans(size: int) -> ImageFont.FreeTypeFont:
    return _font(_SANS_CANDIDATES, size)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "post"


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_centered_lines(draw, lines, font, center_x, top_y, line_height, fill):
    y = top_y
    for line in lines:
        width = draw.textlength(line, font=font)
        draw.text((center_x - width / 2, y), line, font=font, fill=fill)
        y += line_height
    return y


# ---------------------------------------------------------------------
# Property carousel: real photos, cropped/resized, optional cover overlay
# ---------------------------------------------------------------------

def _draw_overlay_text(canvas: Image.Image, text: str) -> None:
    """Pine-tinted scrim across the bottom third of the slide, with the
    overlay text in white — kept short, since this is meant for a brief
    callout. Pine (not plain black) ties it to the brand's own dark-band
    color."""
    w, h = canvas.size
    scrim_top = int(h * 0.52)

    scrim = Image.new("RGBA", (w, h - scrim_top), (0, 0, 0, 0))
    scrim_draw = ImageDraw.Draw(scrim)
    for y in range(scrim.height):
        alpha = int(210 * (y / scrim.height))
        scrim_draw.line([(0, y), (w, y)], fill=(*PINE, alpha))
    canvas.paste(scrim, (0, scrim_top), scrim)

    draw = ImageDraw.Draw(canvas)
    font = _serif(52)
    max_width = w - 140
    lines = _wrap(draw, text, font, max_width)
    line_height = 62
    total_height = line_height * len(lines)
    _draw_centered_lines(draw, lines, font, w / 2, h - 60 - total_height, line_height, (255, 255, 255))


def render_carousel_slides(post: dict, folder: Path) -> list[Path]:
    va = post["visual_assets"]
    asset_records = assets.load_asset_records(post["property_id"])
    path_by_filename = {r["filename"]: r["path"] for r in asset_records}

    written = []
    for i, filename in enumerate(va["assets_selected"], start=1):
        source_path = path_by_filename[filename]
        with Image.open(source_path) as src:
            canvas = ImageOps.fit(src.convert("RGB"), CAROUSEL_SIZE, Image.LANCZOS)

        if filename == va["cover_asset"] and va.get("overlay_text"):
            _draw_overlay_text(canvas, va["overlay_text"])

        out_path = folder / f"slide_{i}.jpg"
        canvas.save(out_path, "JPEG", quality=92)
        written.append(out_path)
    return written


# ---------------------------------------------------------------------
# Text-led graphics: Story / normal post / non-property carousel slides
# ---------------------------------------------------------------------

def _brand_footer(draw, size, label):
    """A solid pine band across the bottom, echoing the brand's own use of
    pine for 'structure, dark bands, footer' — not just an accent color."""
    w, h = size
    band_h = int(h * FOOTER_BAND_RATIO)
    draw.rectangle([(0, h - band_h), (w, h)], fill=PINE)

    font = _sans(24)
    text_y = h - band_h / 2 - 12
    draw.text((70, text_y), "URBAN NEST ESTATES", font=font, fill=BRASS)
    if label:
        text = label.upper()
        tw = draw.textlength(text, font=font)
        draw.text((w - 70 - tw, text_y), text, font=font, fill=PAPER)


def render_text_card(size: tuple[int, int], headline: str | None, subtext: str | None,
                      cta: str | None, footer_label: str | None) -> Image.Image:
    w, h = size
    canvas = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(canvas)

    margin = int(w * 0.11)
    max_width = w - 2 * margin
    y = h * 0.36

    if headline:
        font = _serif(int(w * 0.075))
        lines = _wrap(draw, headline, font, max_width)
        line_height = int(w * 0.09)
        y = _draw_centered_lines(draw, lines, font, w / 2, y, line_height, INK)
        y += int(w * 0.025)
        # a brass hairline, echoing the brand's own use of brass for hairlines/labels
        rule_width = int(w * 0.09)
        draw.line([(w / 2 - rule_width / 2, y), (w / 2 + rule_width / 2, y)], fill=BRASS, width=2)
        y += int(w * 0.035)

    if subtext:
        font = _sans(int(w * 0.035))
        lines = _wrap(draw, subtext, font, max_width)
        line_height = int(w * 0.05)
        y = _draw_centered_lines(draw, lines, font, w / 2, y, line_height, INK_SOFT)
        y += int(w * 0.04)

    if cta:
        font = _sans(int(w * 0.032))
        pad_x, pad_y = int(w * 0.045), int(w * 0.028)
        line_height = int(w * 0.042)
        lines = _wrap(draw, cta.upper(), font, max_width - 2 * pad_x)
        block_width = max(draw.textlength(line, font=font) for line in lines) + 2 * pad_x
        block_height = line_height * len(lines) + 2 * pad_y

        box = (w / 2 - block_width / 2, y, w / 2 + block_width / 2, y + block_height)
        draw.rectangle(box, outline=CLAY, width=3)
        _draw_centered_lines(draw, lines, font, w / 2, y + pad_y, line_height, CLAY)

    _brand_footer(draw, size, footer_label)
    return canvas


def render_story_graphic(post: dict) -> Image.Image:
    return render_text_card(
        STORY_SIZE,
        headline=post["hook"],
        subtext=post["content_idea"],
        cta=post["cta"],
        footer_label=post["content_type"],
    )


def render_normal_graphic(post: dict) -> Image.Image:
    return render_text_card(
        SQUARE_SIZE,
        headline=post["hook"],
        subtext=post["content_idea"],
        cta=post["cta"],
        footer_label=post["content_type"],
    )


def render_non_property_carousel_slides(post: dict, folder: Path) -> list[Path]:
    """No real photos to work with, so this uses only text already present
    in the plan, split across two cards: hook+idea, then the CTA."""
    slide_1 = render_text_card(CAROUSEL_SIZE, headline=post["hook"], subtext=post["content_idea"],
                                cta=None, footer_label=post["content_type"])
    slide_2 = render_text_card(CAROUSEL_SIZE, headline=None, subtext=None,
                                cta=post["cta"], footer_label=post["content_type"])
    written = []
    for i, canvas in enumerate((slide_1, slide_2), start=1):
        out_path = folder / f"slide_{i}.jpg"
        canvas.save(out_path, "JPEG", quality=92)
        written.append(out_path)
    return written


# ---------------------------------------------------------------------
# Reel concept: storyboard text file, never video
# ---------------------------------------------------------------------

def render_reel_storyboard(post: dict) -> str:
    lines = [
        f"Reel concept storyboard — {post['property'] or post['content_type']}",
        f"Hook (open on-screen text): {post['hook']}",
        "",
    ]

    va = post.get("visual_assets")
    if va and va.get("assets_selected"):
        lines.append("Suggested shot sequence (from the property's real photos):")
        for i, filename in enumerate(va["assets_selected"], start=1):
            desc = va["asset_descriptions"].get(filename, "")
            reason = va["asset_reasons"].get(filename, "")
            lines.append(f"  {i}. {filename} — {desc}")
            if reason:
                lines.append(f"     why: {reason}")
    else:
        lines.append("Suggested visual direction (no property footage available for this post):")
        lines.append(f"  {post['visual_needed']}")

    lines += ["", f"CTA (end card): {post['cta']}", "Caption: see caption.txt"]
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------

def _folder_name(index: int, post: dict) -> str:
    slug = slugify(post["content_type"])
    if post.get("property"):
        slug += f"--{slugify(post['property'])}"
    return f"post_{index}_{slug}"


def render_post(post: dict, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    if post["format"] == "Reel concept":
        (folder / "storyboard.txt").write_text(render_reel_storyboard(post))
    elif post["property"] is not None:
        render_carousel_slides(post, folder)
    elif post["format"] == "Story":
        render_story_graphic(post).save(folder / "story.jpg", "JPEG", quality=92)
    elif post["format"] == "Carousel":
        render_non_property_carousel_slides(post, folder)
    else:  # Normal post
        render_normal_graphic(post).save(folder / "graphic.jpg", "JPEG", quality=92)

    (folder / "caption.txt").write_text(post["caption"])


def render_plan(plan: dict) -> Path:
    """Render every post in a weekly plan. Returns the week's output folder."""
    week_dir = OUTPUT_POSTS_DIR / plan["week_of"]
    for i, post in enumerate(plan["posts"], start=1):
        render_post(post, week_dir / _folder_name(i, post))
    return week_dir
