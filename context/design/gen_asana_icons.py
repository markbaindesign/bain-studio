#!/usr/bin/env python3
"""Generate Bain Design Asana project icons — coloured square + Bd mark."""

from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = "/media/data/dev/bain-studio/context/design/asana-icons"
FONT_PATH = "/home/bain/.local/share/fonts/JetBrainsMono-Bold.ttf"
SIZE = 128
TEXT = "Bd"
TEXT_COLOR = "#E8DFCC"  # --paper from design system

COLORS = [
    ("grey",        "#B2B2B2"),
    ("salmon",      "#F06A6A"),
    ("orange",      "#FFAC00"),
    ("yellow",      "#ECC94B"),
    ("green",       "#62D256"),
    ("mint",        "#37C5AB"),
    ("sky-blue",    "#4BC3E0"),
    ("blue-purple", "#7B68EE"),
    ("lavender",    "#9D7AE0"),
    ("hot-pink",    "#E362AE"),
    ("light-pink",  "#F9C8E0"),
    ("mauve",       "#C8909A"),
]

font = ImageFont.truetype(FONT_PATH, size=58)

for name, hex_color in COLORS:
    img = Image.new("RGB", (SIZE, SIZE), hex_color)
    draw = ImageDraw.Draw(img)

    tw, th = draw.textsize(TEXT, font=font)
    x = (SIZE - tw) / 2
    y = (SIZE - th) / 2

    draw.text((x, y), TEXT, font=font, fill=TEXT_COLOR)

    path = os.path.join(OUT_DIR, f"bd-{name}.png")
    img.save(path)
    print(f"  {path}")

print(f"\n{len(COLORS)} icons written to {OUT_DIR}")
