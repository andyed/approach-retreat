#!/usr/bin/env python3
"""Approach/Retreat visual identity generator.

Generates:
  - favicon (32x32, 128x128, 512x512)
  - wordmark logo (1400x300)
  - social header (1200x630 — OG image standard)
  - brand mark alone (transparent PNG, 512x512)

Core visual — faithful to real SERP cursor behavior:
  Result AOI sits on the LEFT where content lives. Cursor parks on the RIGHT
  (near the scrollbar — where most cursors live between interactions). The
  approach crosses RIGHT-to-LEFT into the result, then three outcomes:
    - CLICK: continues into the result text (leftward)
    - DEFERRED (minor retreat): pulls back right a short distance
    - REJECTED (major retreat): retreats far right, back to the home zone

All text verified ≥8:1 contrast.

Usage: python3 brand.py
"""
import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent.parent / "site/assets/brand"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Palette ---
BG = (10, 10, 12)
AOI_BORDER = (110, 175, 255)  # blue — the result rectangle
CLICK = (130, 220, 170)        # mint — commit
DEFERRED = (220, 170, 50)      # amber — minor retreat (coming back)
REJECTED = (255, 140, 130)     # coral — major retreat (gone)
APPROACH = (180, 180, 175)     # neutral — the incoming approach
HOME_ZONE = (60, 60, 70)       # subtle — cursor parking indicator
TEXT = (228, 228, 216)
SUBTEXT = (170, 170, 165)


def luminance(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


print("=== Contrast check (target 8:1+) ===")
for name, color in [
    ("AOI_BORDER", AOI_BORDER),
    ("CLICK", CLICK),
    ("DEFERRED", DEFERRED),
    ("REJECTED", REJECTED),
    ("APPROACH", APPROACH),
    ("TEXT", TEXT),
    ("SUBTEXT", SUBTEXT),
]:
    r = contrast_ratio(color, BG)
    status = "✓" if r >= 8.0 else "✗"
    print(f"  {status} {name:11s} {r:.1f}:1")
print()


FONT_PATHS = [
    '/System/Library/Fonts/Helvetica.ttc',
    '/System/Library/Fonts/SFCompact.ttf',
    '/Library/Fonts/Arial Bold.ttf',
]
FONT_PATH = next((f for f in FONT_PATHS if os.path.exists(f)), None)


def font(size, weight='regular'):
    if not FONT_PATH:
        return ImageFont.load_default()
    if FONT_PATH.endswith('.ttc'):
        idx = {'regular': 0, 'bold': 1, 'light': 2}.get(weight, 0)
        return ImageFont.truetype(FONT_PATH, size, index=idx)
    return ImageFont.truetype(FONT_PATH, size)


def draw_hourglass(draw, cx, cy, height, color, line_width=2):
    """Draw a simple hourglass icon centered at (cx, cy)."""
    half_h = height // 2
    half_w = int(height * 0.42)

    # Top cap
    draw.line(
        [(cx - half_w - 2, cy - half_h), (cx + half_w + 2, cy - half_h)],
        fill=color, width=line_width
    )
    # Bottom cap
    draw.line(
        [(cx - half_w - 2, cy + half_h), (cx + half_w + 2, cy + half_h)],
        fill=color, width=line_width
    )
    # Top triangle outline
    draw.polygon([
        (cx - half_w, cy - half_h),
        (cx + half_w, cy - half_h),
        (cx, cy),
    ], outline=color, width=line_width)
    # Bottom triangle outline
    draw.polygon([
        (cx - half_w, cy + half_h),
        (cx + half_w, cy + half_h),
        (cx, cy),
    ], outline=color, width=line_width)
    # Sand at the bottom
    sand_h = max(2, height // 5)
    draw.polygon([
        (cx - sand_h, cy + half_h - 1),
        (cx + sand_h, cy + half_h - 1),
        (cx, cy + half_h - sand_h - 1),
    ], fill=color)


def draw_input_box(draw, cx, top_y, width, scale, query_text):
    """Draw a search input box with query text and hourglass icon."""
    height = int(44 * scale)
    left = cx - width // 2
    right = left + width
    bottom = top_y + height
    radius = height // 2

    border_w = max(2, int(2 * scale))
    box_color = SUBTEXT  # muted border so it doesn't compete with AOI

    # Rounded rectangle — use draw.rounded_rectangle (Pillow ≥ 8.2)
    try:
        draw.rounded_rectangle(
            [left, top_y, right, bottom],
            radius=radius,
            outline=box_color,
            width=border_w,
        )
    except AttributeError:
        draw.rectangle([left, top_y, right, bottom], outline=box_color, width=border_w)

    # Query text (lowercase, muted)
    query_font = font(max(14, int(22 * scale)), 'regular')
    text_x = left + int(22 * scale)
    text_y = top_y + (height - int(22 * scale)) // 2
    draw.text((text_x, text_y), query_text, fill=TEXT, font=query_font)

    # Hourglass on the right side of the box
    hg_height = int(22 * scale)
    hg_cx = right - int(24 * scale)
    hg_cy = top_y + height // 2
    draw_hourglass(draw, hg_cx, hg_cy, hg_height, box_color, line_width=max(1, int(1.8 * scale)))

    return (left, top_y, right, bottom)


def draw_arrowhead(draw, end, direction_angle, size, color):
    """Arrowhead at `end` pointing in `direction_angle` (radians)."""
    ex, ey = end
    draw.polygon([
        (ex, ey),
        (ex - size * math.cos(direction_angle - 0.45),
         ey - size * math.sin(direction_angle - 0.45)),
        (ex - size * math.cos(direction_angle + 0.45),
         ey - size * math.sin(direction_angle + 0.45)),
    ], fill=color)


def draw_brand_glyph(draw, cx, cy, scale=1.0, show_labels=False, show_home_zone=True):
    """Draw the brand glyph.

    Coordinate system: (cx, cy) is the approximate CENTER of the glyph's
    bounding box. Glyph footprint at scale=1:
      width:  ~260 px (from left edge of AOI to right edge of home zone)
      height: ~80 px (AOI is ~42 tall, plus slight padding)

    The AOI sits on the left half, cursor enters from the right, retreats
    back to the right home zone.
    """
    # === Geometry ===
    box_w = int(140 * scale)
    box_h = int(46 * scale)
    box_l = cx - int(120 * scale)
    box_t = cy - box_h // 2
    box_r = box_l + box_w
    box_b = box_t + box_h

    # Cursor entry point: just right of the AOI's right edge
    entry_x = box_r + int(4 * scale)
    entry_y = box_t + int(box_h * 0.55)  # slightly lower than center

    # Home zone: far right, at the margin
    home_x = cx + int(110 * scale)
    home_y = entry_y

    border_w = max(2, int(3 * scale))
    line_w = max(2, int(3 * scale))

    # === Optional home zone indicator (subtle dashed right-edge hint) ===
    if show_home_zone:
        dash_len = int(4 * scale)
        dash_gap = int(4 * scale)
        dash_x = home_x + int(18 * scale)
        y = box_t - int(6 * scale)
        y_end = box_b + int(6 * scale)
        while y < y_end:
            draw.line(
                [(dash_x, y), (dash_x, min(y + dash_len, y_end))],
                fill=HOME_ZONE, width=max(1, int(1.5 * scale))
            )
            y += dash_len + dash_gap

    # === AOI rectangle (the search result) ===
    draw.rectangle([box_l, box_t, box_r, box_b], outline=AOI_BORDER, width=border_w)

    # Two text lines inside the AOI
    line_pad = int(12 * scale)
    line_y1 = box_t + int(12 * scale)
    line_y2 = box_t + int(26 * scale)
    draw.line(
        [(box_l + line_pad, line_y1), (box_r - line_pad - int(22 * scale), line_y1)],
        fill=AOI_BORDER, width=max(1, int(2 * scale))
    )
    draw.line(
        [(box_l + line_pad, line_y2), (box_r - int(45 * scale), line_y2)],
        fill=AOI_BORDER, width=max(1, int(1.5 * scale))
    )

    # === Approach line (from home zone, coming left into AOI) ===
    approach_start = (home_x, home_y)
    draw.line([approach_start, (entry_x, entry_y)], fill=APPROACH, width=line_w)
    # Small arrowhead at the AOI boundary to indicate direction
    draw_arrowhead(draw, (entry_x, entry_y), math.pi, int(5 * scale), APPROACH)

    # === Three outcomes diverging from entry point ===

    # 1. CLICK — continues LEFT, into the result (stops inside the text region)
    click_end = (box_l + int(box_w * 0.45), entry_y)
    draw.line([(entry_x, entry_y), click_end], fill=CLICK, width=line_w + 1)
    draw_arrowhead(draw, click_end, math.pi, int(7 * scale), CLICK)

    # 2. DEFERRED — minor retreat: short curve pulling back right
    # slightly up or down to avoid overlapping the approach line
    deferred_pts = []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        # Start at entry, curve right and slightly up (lifts off the approach line)
        cpx = entry_x + int(30 * scale)
        cpy = entry_y - int(18 * scale)
        ex = entry_x + int(58 * scale)
        ey = entry_y - int(24 * scale)
        x = (1 - t) ** 2 * entry_x + 2 * (1 - t) * t * cpx + t ** 2 * ex
        y = (1 - t) ** 2 * entry_y + 2 * (1 - t) * t * cpy + t ** 2 * ey
        deferred_pts.append((x, y))
    for i in range(len(deferred_pts) - 1):
        draw.line([deferred_pts[i], deferred_pts[i + 1]], fill=DEFERRED, width=line_w)
    # Arrowhead at the curve's end
    prev_pt = deferred_pts[-3]
    end_pt = deferred_pts[-1]
    angle = math.atan2(end_pt[1] - prev_pt[1], end_pt[0] - prev_pt[0])
    draw_arrowhead(draw, end_pt, angle, int(6 * scale), DEFERRED)

    # 3. REJECTED — major retreat: long straight line all the way back to home zone
    # Slightly below the approach line to distinguish them
    reject_end = (home_x + int(8 * scale), entry_y + int(22 * scale))
    draw.line([(entry_x, entry_y + int(3 * scale)), reject_end], fill=REJECTED, width=line_w)
    angle = math.atan2(reject_end[1] - entry_y, reject_end[0] - entry_x)
    draw_arrowhead(draw, reject_end, angle, int(7 * scale), REJECTED)

    # === Optional labels ===
    if show_labels and scale >= 2.0:
        label_font = font(max(14, int(16 * scale / 2)), 'regular')
        # click label: inside the AOI, above the line
        draw.text(
            (click_end[0] + int(6 * scale), click_end[1] - int(22 * scale)),
            "click", fill=CLICK, font=label_font
        )
        # deferred label: above the curve end
        draw.text(
            (deferred_pts[-1][0] + int(6 * scale), deferred_pts[-1][1] - int(18 * scale)),
            "deferred", fill=DEFERRED, font=label_font
        )
        # rejected label: near the reject end, below
        draw.text(
            (reject_end[0] - int(40 * scale), reject_end[1] + int(6 * scale)),
            "rejected", fill=REJECTED, font=label_font
        )

    # Return bounding box for layout purposes
    left = box_l - int(4 * scale)
    right = home_x + int(30 * scale) if show_home_zone else home_x + int(14 * scale)
    top = box_t - int(30 * scale) if show_labels else box_t - int(4 * scale)
    bottom = reject_end[1] + int(28 * scale) if show_labels else reject_end[1] + int(6 * scale)
    return (left, top, right, bottom)


# === 1. Brand mark alone (512x512 transparent) ===
print("=== Brand mark (512x512 transparent) ===")
mark = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
draw = ImageDraw.Draw(mark)
draw_brand_glyph(draw, 256, 256, scale=1.7, show_labels=False)
mark.save(OUT_DIR / "brand-mark.png")
print(f"  → brand-mark.png")


# === 2. Favicons ===
print("=== Favicons (32, 128, 512) ===")
for size in [32, 128, 512]:
    fav = Image.new('RGB', (size, size), BG)
    draw = ImageDraw.Draw(fav)
    scale = size / 280
    draw_brand_glyph(draw, size // 2, size // 2, scale=scale, show_home_zone=(size >= 128))
    fav.save(OUT_DIR / f"favicon-{size}.png")
    print(f"  → favicon-{size}.png")

# Save 32x32 as favicon.ico
fav32 = Image.open(OUT_DIR / "favicon-32.png")
fav32.save(OUT_DIR / "favicon.ico", format='ICO', sizes=[(32, 32)])
print(f"  → favicon.ico")


# === 3. Wordmark logo (1400x280) ===
print("=== Wordmark (1400x280) ===")
W, H = 1400, 280
wordmark = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(wordmark)

# Glyph on left — more compact, no labels
glyph_cx = 260
glyph_cy = H // 2
draw_brand_glyph(draw, glyph_cx, glyph_cy, scale=1.4, show_labels=False)

# Text block on right
title_font = font(80, 'bold')
subtitle_font = font(28, 'regular')

title = "approach / retreat"
tagline = "cursor dynamics on search result pages"

title_x = 520
title_y = 82

draw.text((title_x, title_y), title, fill=TEXT, font=title_font)

# Measure title height for tagline placement
bbox = draw.textbbox((title_x, title_y), title, font=title_font)
tagline_y = bbox[3] + 16
draw.text((title_x + 4, tagline_y), tagline, fill=SUBTEXT, font=subtitle_font)

wordmark.save(OUT_DIR / "wordmark.png")
print(f"  → wordmark.png")


# === 4. Social header (1200x630 — OG image standard) ===
print("=== Social header (1200x630) ===")
W, H = 1200, 630
social = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(social)

# Input box at top — query + hourglass, positioned above the AOI
# The AOI in the glyph (scale 2.0) sits at cy=250, box_l = 250-240=10 from cx
# AOI width at scale 2.0 is 280, so we center the input box over the AOI's cx
GLYPH_SCALE = 2.0
GLYPH_CX = W // 2 - int(40 * GLYPH_SCALE)  # shift glyph slightly left so labels have room
GLYPH_CY = 270

# Compute AOI center within the glyph
aoi_cx = GLYPH_CX - int(50 * GLYPH_SCALE)  # box_l offset from cx is -120*scale, box center is -50*scale
aoi_top_y = GLYPH_CY - int(23 * GLYPH_SCALE)  # box_h/2 = 23*scale

# Input box centered on the AOI's x, above it
input_width = int(360 * GLYPH_SCALE)
input_top = 100
draw_input_box(draw, aoi_cx, input_top, input_width, scale=1.4, query_text="cognac glasses set of 2")

# Connector line from input box down to the AOI (suggests query → result flow)
input_bottom = input_top + int(44 * 1.4)
conn_gap = 10
draw.line(
    [(aoi_cx, input_bottom + conn_gap), (aoi_cx, aoi_top_y - conn_gap)],
    fill=(80, 80, 85),
    width=2,
)
# Tiny arrowhead at the AOI
draw_arrowhead(draw, (aoi_cx, aoi_top_y - conn_gap), math.pi / 2, 5, (80, 80, 85))

# The brand glyph
draw_brand_glyph(draw, GLYPH_CX, GLYPH_CY, scale=GLYPH_SCALE, show_labels=True)

# Divider line
divider_y = 420
draw.line([(200, divider_y), (W - 200, divider_y)], fill=(40, 40, 45), width=1)

# Title centered below
title_font = font(84, 'bold')
subtitle_font = font(30, 'regular')
attribution_font = font(22, 'regular')

title = "approach / retreat"
tagline = "cursor dynamics on search result pages"
attribution = "a task model for the evaluation phase  ·  github.com/andyed/approach-retreat"

bbox = draw.textbbox((0, 0), title, font=title_font)
title_w = bbox[2] - bbox[0]
draw.text(((W - title_w) // 2, 455), title, fill=TEXT, font=title_font)

bbox = draw.textbbox((0, 0), tagline, font=subtitle_font)
tag_w = bbox[2] - bbox[0]
draw.text(((W - tag_w) // 2, 553), tagline, fill=SUBTEXT, font=subtitle_font)

bbox = draw.textbbox((0, 0), attribution, font=attribution_font)
attr_w = bbox[2] - bbox[0]
draw.text(((W - attr_w) // 2, 597), attribution, fill=SUBTEXT, font=attribution_font)

social.save(OUT_DIR / "social-header.png")
print(f"  → social-header.png")

print()
print(f"All assets saved to {OUT_DIR}")
