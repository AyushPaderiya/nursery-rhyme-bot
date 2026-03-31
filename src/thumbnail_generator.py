"""Thumbnail generator module for the Nursery Rhyme Bot pipeline.

Generates a 1280×720 YouTube thumbnail image using Pillow with
a gradient overlay, playful font, auto-sized title text, and
a "WATCH NOW" badge.
"""

import os
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

from src.utils import ensure_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
THUMBNAIL_WIDTH: int = 1280
THUMBNAIL_HEIGHT: int = 720
THUMBNAIL_SIZE: tuple[int, int] = (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)
FONT_DIR: str = os.path.join(
    os.path.dirname(__file__), "..", "assets", "fonts"
)
FONT_FILENAME: str = "FredokaOne-Regular.ttf"
FONT_URL: str = (
    "https://github.com/google/fonts/raw/main/ofl/fredokaone/FredokaOne-Regular.ttf"
)
TITLE_COLOR: str = "#FFE600"
STROKE_COLOR: str = "#000000"
STROKE_WIDTH: int = 4
MAX_TEXT_WIDTH: int = 1100
BADGE_COLOR: tuple[int, int, int] = (255, 0, 0)
BADGE_TEXT_COLOR: str = "white"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Load Fredoka One font at the given size, downloading if needed.

    Downloads the font from Google Fonts to assets/fonts/ on first use
    and caches it for subsequent calls.

    Args:
        size: Font size in pixels.

    Returns:
        A Pillow FreeTypeFont object.
    """
    font_path = os.path.join(FONT_DIR, FONT_FILENAME)

    if not os.path.exists(font_path):
        ensure_dir(FONT_DIR)
        resp = requests.get(FONT_URL, timeout=30)
        resp.raise_for_status()
        with open(font_path, "wb") as f:
            f.write(resp.content)

    return ImageFont.truetype(font_path, size)


def _draw_gradient_overlay(image: Image.Image) -> Image.Image:
    """Add a semi-transparent dark gradient to the bottom 40% of the image.

    Creates a gradient from fully transparent at the top edge of the
    gradient region to semi-opaque dark at the bottom.

    Args:
        image: The source RGBA image to overlay on.

    Returns:
        The image with the gradient applied.
    """
    width, height = image.size
    gradient_start = int(height * 0.60)  # Top of gradient region
    gradient_height = height - gradient_start

    # Create gradient overlay
    gradient = Image.new("RGBA", (width, gradient_height), (0, 0, 0, 0))
    for y in range(gradient_height):
        alpha = int(180 * (y / gradient_height))
        for x in range(width):
            gradient.putpixel((x, y), (0, 0, 0, alpha))

    image.paste(gradient, (0, gradient_start), gradient)
    return image


def _draw_watch_badge(draw: ImageDraw.ImageDraw, image_width: int) -> None:
    """Draw a red "▶ WATCH NOW" badge at the top-right corner.

    Args:
        draw: The Pillow ImageDraw object to draw on.
        image_width: Width of the image for positioning.
    """
    badge_text = "▶ WATCH NOW"
    try:
        badge_font = _get_font(28)
    except Exception:
        badge_font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding_x = 16
    padding_y = 10
    badge_w = text_w + padding_x * 2
    badge_h = text_h + padding_y * 2

    # Position at top-right with margin
    margin = 20
    x1 = image_width - badge_w - margin
    y1 = margin
    x2 = x1 + badge_w
    y2 = y1 + badge_h

    # Draw rounded rectangle
    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=12,
        fill=BADGE_COLOR,
    )

    # Draw badge text centred in rectangle
    text_x = x1 + (badge_w - text_w) // 2
    text_y = y1 + (badge_h - text_h) // 2
    draw.text(
        (text_x, text_y),
        badge_text,
        font=badge_font,
        fill=BADGE_TEXT_COLOR,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_thumbnail(
    image_path: str,
    title: str,
    output_path: str,
) -> str:
    """Generate a 1280×720 YouTube thumbnail from a background image.

    Pipeline:
    1. Resize source image to 1280×720 with LANCZOS resampling
    2. Add dark gradient overlay on bottom 40%
    3. Render title text with playful font, auto-sized to fit
    4. Add red "WATCH NOW" badge at top-right
    5. Save as JPEG with quality=95

    Args:
        image_path: Path to the base image (e.g. first stanza image).
        title: The rhyme title to overlay.
        output_path: Path to save the thumbnail JPEG.

    Returns:
        The output file path.
    """
    ensure_dir(os.path.dirname(output_path))

    # 1. Open and resize
    img = Image.open(image_path).convert("RGBA")
    img = img.resize(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

    # 2. Gradient overlay
    img = _draw_gradient_overlay(img)

    # 3. Draw title text with auto-sizing
    draw = ImageDraw.Draw(img)

    font_size = 90
    font = None
    text_w = MAX_TEXT_WIDTH + 1  # Force at least one iteration

    while text_w > MAX_TEXT_WIDTH and font_size >= 20:
        try:
            font = _get_font(font_size)
        except Exception:
            font = ImageFont.load_default()
            break
        bbox = draw.textbbox((0, 0), title, font=font, stroke_width=STROKE_WIDTH)
        text_w = bbox[2] - bbox[0]
        if text_w > MAX_TEXT_WIDTH:
            font_size -= 4

    if font is None:
        font = ImageFont.load_default()

    # Recalculate final bbox
    bbox = draw.textbbox((0, 0), title, font=font, stroke_width=STROKE_WIDTH)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position: horizontally centred, vertically at 75%
    text_x = (THUMBNAIL_WIDTH - text_w) // 2
    text_y = int(THUMBNAIL_HEIGHT * 0.75) - text_h // 2

    draw.text(
        (text_x, text_y),
        title,
        font=font,
        fill=TITLE_COLOR,
        stroke_width=STROKE_WIDTH,
        stroke_fill=STROKE_COLOR,
    )

    # 4. WATCH NOW badge
    _draw_watch_badge(draw, THUMBNAIL_WIDTH)

    # 5. Save as JPEG
    # Convert RGBA back to RGB for JPEG compatibility
    rgb_img = Image.new("RGB", img.size, (0, 0, 0))
    rgb_img.paste(img, mask=img.split()[3])
    rgb_img.save(output_path, "JPEG", quality=95)

    return output_path


if __name__ == "__main__":
    print("thumbnail_generator.py — all functions defined ✓")
