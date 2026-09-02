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


def _measure_draw() -> ImageDraw.ImageDraw:
    """A throwaway 1x1 canvas, used only to measure text — lets fit_text_to_box
    predict wrapping/truncation without needing the real canvas."""
    return ImageDraw.Draw(Image.new("RGB", (1, 1)))


def fit_text_to_box(
    text: str,
    max_width: int,
    max_lines: int,
    font_fn,
    start_size: int,
    min_size: int,
    step: int = 4,
) -> tuple[ImageFont.FreeTypeFont, list[str], bool]:
    """Shrinks the font until the wrapped text fits within max_lines; if it
    still doesn't fit at min_size, truncates the last line with an ellipsis
    rather than letting it clip or run past its allotted space. This is the
    one place text-fitting happens, so the renderer and the publishability
    checker agree on whether something needed shrinking/truncating."""
    draw = _measure_draw()
    size = start_size
    while size >= min_size:
        font = font_fn(size)
        lines = _wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines, False
        size -= step

    font = font_fn(min_size)
    lines = _wrap(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return font, lines, False

    lines = lines[:max_lines]
    last = lines[-1]
    while last and draw.textlength(last + "…", font=font) > max_width:
        last = last[:-1]
    lines[-1] = last.rstrip() + "…"
    return font, lines, True


# ---------------------------------------------------------------------
# Property carousel: real photos, cropped/resized, optional cover overlay
# ---------------------------------------------------------------------

def _draw_overlay_text(canvas: Image.Image, text: str) -> bool:
    """Pine-tinted scrim across the bottom third of the slide, with the
    overlay text in white — kept short, since this is meant for a brief
    callout. Pine (not plain black) ties it to the brand's own dark-band
    color. Returns False (drawing nothing) rather than force-fitting a
    sentence that's too long to sit cleanly on a photo in 2 lines."""
    w, h = canvas.size
    max_width = w - 140
    font, lines, truncated = fit_text_to_box(text, max_width, max_lines=2, font_fn=_serif, start_size=52, min_size=40)
    if truncated:
        return False

    scrim_top = int(h * 0.52)
    scrim = Image.new("RGBA", (w, h - scrim_top), (0, 0, 0, 0))
    scrim_draw = ImageDraw.Draw(scrim)
    for y in range(scrim.height):
        alpha = int(210 * (y / scrim.height))
        scrim_draw.line([(0, y), (w, y)], fill=(*PINE, alpha))
    canvas.paste(scrim, (0, scrim_top), scrim)

    draw = ImageDraw.Draw(canvas)
    line_height = int(font.size * 1.2)
    total_height = line_height * len(lines)
    _draw_centered_lines(draw, lines, font, w / 2, h - 60 - total_height, line_height, (255, 255, 255))
    return True


def render_carousel_slides(post: dict, folder: Path) -> tuple[list[Path], list[str]]:
    va = post["visual_assets"]
    asset_records = assets.load_asset_records(post["property_id"])
    path_by_filename = {r["filename"]: r["path"] for r in asset_records}

    written = []
    warnings = []
    for i, filename in enumerate(va["assets_selected"], start=1):
        source_path = path_by_filename[filename]
        with Image.open(source_path) as src:
            canvas = ImageOps.fit(src.convert("RGB"), CAROUSEL_SIZE, Image.LANCZOS)

        if filename == va["cover_asset"] and va.get("overlay_text"):
            drawn = _draw_overlay_text(canvas, va["overlay_text"])
            if not drawn:
                warnings.append(
                    f"Overlay text was too long to fit cleanly on the cover photo, so it was left off "
                    f"('{va['overlay_text']}')."
                )

        out_path = folder / f"slide_{i}.jpg"
        canvas.save(out_path, "JPEG", quality=92)
        written.append(out_path)
    return written, warnings


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
                      cta: str | None, footer_label: str | None) -> tuple[Image.Image, list[str]]:
    """Two passes: first measure every block (with auto-fit), then vertically
    center the whole stack within the safe area above the footer band. This
    keeps consistent margins regardless of copy length, instead of starting
    from a fixed y that's only comfortable for one particular length."""
    w, h = size
    canvas = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(canvas)
    warnings: list[str] = []

    margin = int(w * 0.11)
    max_width = w - 2 * margin
    top_margin = int(h * 0.09)
    safe_bottom = h - int(h * FOOTER_BAND_RATIO) - int(h * 0.03)
    available_height = safe_bottom - top_margin

    blocks = []  # each: dict with everything the draw pass needs

    if headline:
        font, lines, truncated = fit_text_to_box(
            headline, max_width, max_lines=3, font_fn=_serif,
            start_size=int(w * 0.075), min_size=int(w * 0.045),
        )
        if truncated:
            warnings.append("Headline was too long and had to be truncated to fit.")
        line_height = int(font.size * 1.15)
        hairline_gap = int(w * 0.022)
        rule_width = int(w * 0.09)
        gap_after = hairline_gap + 2 + int(w * 0.03)
        blocks.append({
            "kind": "headline", "font": font, "lines": lines, "line_height": line_height,
            "height": line_height * len(lines) + gap_after,
            "hairline_gap": hairline_gap, "rule_width": rule_width,
        })

    if subtext:
        font, lines, truncated = fit_text_to_box(
            subtext, max_width, max_lines=3, font_fn=_sans,
            start_size=int(w * 0.033), min_size=int(w * 0.023),
        )
        if truncated:
            warnings.append("Supporting text was too long and had to be truncated to fit.")
        line_height = int(font.size * 1.3)
        gap_after = int(w * 0.032)
        blocks.append({
            "kind": "subtext", "font": font, "lines": lines, "line_height": line_height,
            "height": line_height * len(lines) + gap_after,
        })

    if cta:
        font, lines, truncated = fit_text_to_box(
            cta.upper(), max_width - int(w * 0.09), max_lines=2, font_fn=_sans,
            start_size=int(w * 0.03), min_size=int(w * 0.021),
        )
        if truncated:
            warnings.append("CTA text was too long and had to be truncated to fit.")
        pad_x, pad_y = int(w * 0.042), int(w * 0.024)
        line_height = int(font.size * 1.25)
        block_height = line_height * len(lines) + 2 * pad_y
        blocks.append({
            "kind": "cta", "font": font, "lines": lines, "line_height": line_height,
            "height": block_height, "pad_x": pad_x, "pad_y": pad_y, "block_height": block_height,
        })

    total_height = sum(b["height"] for b in blocks)
    y = top_margin + max(0, (available_height - total_height) / 2)

    for block in blocks:
        if block["kind"] == "headline":
            y = _draw_centered_lines(draw, block["lines"], block["font"], w / 2, y, block["line_height"], INK)
            y += block["hairline_gap"]
            draw.line(
                [(w / 2 - block["rule_width"] / 2, y), (w / 2 + block["rule_width"] / 2, y)],
                fill=BRASS, width=2,
            )
            y += int(w * 0.03)
        elif block["kind"] == "subtext":
            y = _draw_centered_lines(draw, block["lines"], block["font"], w / 2, y, block["line_height"], INK_SOFT)
            y += int(w * 0.032)
        elif block["kind"] == "cta":
            font, lines = block["font"], block["lines"]
            pad_x, pad_y = block["pad_x"], block["pad_y"]
            block_width = max(draw.textlength(line, font=font) for line in lines) + 2 * pad_x
            box = (w / 2 - block_width / 2, y, w / 2 + block_width / 2, y + block["block_height"])
            draw.rectangle(box, outline=CLAY, width=3)
            _draw_centered_lines(draw, lines, font, w / 2, y + pad_y, block["line_height"], CLAY)
            y += block["block_height"]

    if y > safe_bottom:
        warnings.append("Text content ran close to the footer — consider shorter copy for this post.")

    _brand_footer(draw, size, footer_label)
    return canvas, warnings


def render_story_graphic(post: dict) -> tuple[Image.Image, list[str]]:
    return render_text_card(
        STORY_SIZE,
        headline=post["hook"],
        subtext=post["content_idea"],
        cta=post["cta"],
        footer_label=post["content_type"],
    )


def render_normal_graphic(post: dict) -> tuple[Image.Image, list[str]]:
    return render_text_card(
        SQUARE_SIZE,
        headline=post["hook"],
        subtext=post["content_idea"],
        cta=post["cta"],
        footer_label=post["content_type"],
    )


def render_non_property_carousel_slides(post: dict, folder: Path) -> tuple[list[Path], list[str]]:
    """No real photos to work with, so this uses only text already present
    in the plan, split across two cards: hook+idea, then the CTA."""
    slide_1, warnings_1 = render_text_card(CAROUSEL_SIZE, headline=post["hook"], subtext=post["content_idea"],
                                            cta=None, footer_label=post["content_type"])
    slide_2, warnings_2 = render_text_card(CAROUSEL_SIZE, headline=None, subtext=None,
                                            cta=post["cta"], footer_label=post["content_type"])
    written = []
    for i, canvas in enumerate((slide_1, slide_2), start=1):
        out_path = folder / f"slide_{i}.jpg"
        canvas.save(out_path, "JPEG", quality=92)
        written.append(out_path)
    return written, warnings_1 + warnings_2


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
    """Renders the post's files to disk. Also attaches post['_render_warnings']
    (mutating the dict in place) so publishability.check_post can report on
    any text that needed shrinking/truncating or an overlay that got skipped.

    A post already carrying a "cannot_produce" verdict (set before rendering,
    from publishability.check_post on the generated copy) is never rendered
    as a finished, ready-looking asset — a BLOCKED.txt explaining why is
    written instead, so nothing that failed grounding could be mistaken for
    something ready to publish."""
    folder.mkdir(parents=True, exist_ok=True)

    prior_check = post.get("_publishability")
    if prior_check and prior_check["status"] == "cannot_produce":
        reasons = "\n".join(f"- [{i['severity']}] {i['code']}: {i['message']}" for i in prior_check["issues"])
        (folder / "BLOCKED.txt").write_text(
            "This post was NOT rendered because it failed a publishability check:\n\n"
            f"{reasons}\n\nChoose a different content idea, or fix the source data, and regenerate."
        )
        (folder / "caption.txt").write_text(post["caption"])
        return

    warnings: list[str] = []

    if post["format"] == "Reel concept":
        (folder / "storyboard.txt").write_text(render_reel_storyboard(post))
    elif post["property"] is not None:
        _, warnings = render_carousel_slides(post, folder)
    elif post["format"] == "Story":
        image, warnings = render_story_graphic(post)
        image.save(folder / "story.jpg", "JPEG", quality=92)
    elif post["format"] == "Carousel":
        _, warnings = render_non_property_carousel_slides(post, folder)
    else:  # Normal post
        image, warnings = render_normal_graphic(post)
        image.save(folder / "graphic.jpg", "JPEG", quality=92)

    post["_render_warnings"] = warnings
    (folder / "caption.txt").write_text(post["caption"])


def render_plan(plan: dict) -> Path:
    """Render every post in a weekly plan. Returns the week's output folder."""
    week_dir = OUTPUT_POSTS_DIR / plan["week_of"]
    for i, post in enumerate(plan["posts"], start=1):
        render_post(post, week_dir / _folder_name(i, post))
    return week_dir
