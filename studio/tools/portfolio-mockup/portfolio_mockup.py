"""
portfolio-mockup — wrap a website screenshot in a browser frame.

Canvas proportions matched to the original Bain Design portfolio template.
Screenshot is centred. Top 1px is cropped (browser chrome artefact).

Usage:
    portfolio-mockup input.jpg [output.jpg] [--text "Label"] [--bg "#414548"]
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_BG = (65, 70, 74)   # dark neutral — high contrast

# Canvas is 1.317× wide and 1.364× tall relative to the screenshot
CANVAS_W_RATIO = 1.317
CANVAS_H_RATIO = 1.364

RADIUS_RATIO = 0.027   # corner radius as fraction of screenshot width


def _parse_hex(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _corner_mask(size, radius):
    """
    Mask of pixels that should be background (not image content).
    White = paint background. Fill-then-cut: avoids seam artefacts.
    """
    w, h = size
    r = radius
    mask = Image.new("L", (w, h), 255)       # start: everything is background
    draw = ImageDraw.Draw(mask)
    # Cut out the rounded rectangle — these pixels stay as image
    draw.rectangle([r, 0, w - r, h], fill=0)
    draw.rectangle([0, r, w,     h - r], fill=0)
    draw.ellipse([0,         0,         r * 2, r * 2], fill=0)
    draw.ellipse([w - r * 2, 0,         w,     r * 2], fill=0)
    draw.ellipse([0,         h - r * 2, r * 2, h    ], fill=0)
    draw.ellipse([w - r * 2, h - r * 2, w,     h    ], fill=0)
    return mask


def _overlay_text(canvas, text, pad_px):
    draw = ImageDraw.Draw(canvas)
    font_size = max(18, canvas.width // 40)
    try:
        font = ImageFont.truetype(
            "/media/data/dev/bain-studio/studio/tools/brand-doc/fonts/"
            "JetBrainsMono-Medium.ttf",
            font_size,
        )
    except (IOError, OSError):
        font = ImageFont.load_default()
    x = pad_px
    y = canvas.height - pad_px - font_size - 6
    draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 90), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 210), font=font)


def make_mockup(
    input_path,
    output_path=None,
    text=None,
    bg=None,
    corner_radius=None,
):
    img = Image.open(input_path).convert("RGB")

    # Auto-detect and crop browser chrome artefacts on any edge.
    # Chrome pixels are: high brightness, near-neutral (low saturation),
    # AND perfectly flat across the entire edge (near-zero variance).
    # Website backgrounds can be light/grey but are rarely all three at once.
    import numpy as np
    def _is_chrome(pixels):
        a = np.array(pixels, dtype=float)
        brightness = a.mean()
        saturation = (a.max(axis=1) - a.min(axis=1)).mean()
        variance = a.std()
        return brightness > 195 and saturation < 8 and variance < 6

    arr = np.array(img)
    H2, W2 = arr.shape[:2]
    t = 1 if _is_chrome(arr[0,    :, :3]) else 0
    b = 1 if _is_chrome(arr[H2-1, :, :3]) else 0
    l = 1 if _is_chrome(arr[:,    0, :3]) else 0
    r = 1 if _is_chrome(arr[:,  W2-1, :3]) else 0
    if t or b or l or r:
        img = img.crop((l, t, W2 - r, H2 - b))

    W, H = img.size
    bg = bg or DEFAULT_BG
    radius = corner_radius if corner_radius is not None else max(6, int(W * RADIUS_RATIO))

    canvas_w = int(W * CANVAS_W_RATIO)
    canvas_h = int(H * CANVAS_H_RATIO)

    # Centre the screenshot
    pad_x = (canvas_w - W) // 2
    pad_y = (canvas_h - H) // 2

    # Compose: paste image, then paint background over corners
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg)
    canvas.paste(img, (pad_x, pad_y))
    bg_patch = Image.new("RGB", (W, H), bg)
    canvas.paste(bg_patch, (pad_x, pad_y), _corner_mask((W, H), radius))

    if text:
        _overlay_text(canvas, text, pad_x)

    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / (p.stem + "-mockup.jpg"))

    canvas.save(output_path, "JPEG", quality=95)
    return output_path


def main():
    p = argparse.ArgumentParser(description="Wrap a screenshot in a portfolio mockup frame.")
    p.add_argument("input", help="Input screenshot (PNG or JPG)")
    p.add_argument("output", nargs="?", help="Output path (default: input-mockup.jpg)")
    p.add_argument("--text", help="Optional label text overlay")
    p.add_argument("--bg", metavar="HEX", help="Background colour e.g. #414548")
    p.add_argument("--radius", type=int, help="Corner radius in px (default: auto)")
    p.add_argument("--no-crop", action="store_true",
                   help="Skip the 1px top crop (if source has no chrome artefact)")
    args = p.parse_args()

    out = make_mockup(
        args.input,
        args.output,
        text=args.text,
        bg=_parse_hex(args.bg) if args.bg else None,
        corner_radius=args.radius,
    )
    print(f"Done -> {out}")


if __name__ == "__main__":
    main()
