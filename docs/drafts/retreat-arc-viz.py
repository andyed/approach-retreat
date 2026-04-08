#!/usr/bin/env python3
"""Retreat arc geometry visualization for CIKM 2026 paper.

Three panels:
1. Arc shape comparison (organic / top-ad / native-ad)
2. Fitts' law ID by element type
3. Lateral displacement as uncertainty signal

Data from NB24 (attentional-foraging/notebooks-v2/24_retreat_arc_geometry_executed.ipynb)
"""

from PIL import Image, ImageDraw, ImageFont
import math, os

# --- Config ---
W, H = 1800, 700
BG = (10, 10, 12)
PANEL_W = W // 3

# Colors — 8:1+ contrast on #0a0a0c
ORGANIC = (110, 175, 255)   # blue — 8.4:1
TOP_AD = (255, 140, 130)    # red — 8.5:1
NATIVE = (220, 170, 50)     # amber — 9.3:1
TEXT = (228, 228, 216)       # cream — 15.4:1
META = (180, 180, 175)      # secondary — 9.5:1
GRID = (40, 40, 42)         # subtle grid

# Font
FONT_PATHS = [
    '/System/Library/Fonts/Helvetica.ttc',
    '/System/Library/Fonts/SFCompact.ttf',
    '/Library/Fonts/Arial Bold.ttf',
]
font_path = next((f for f in FONT_PATHS if os.path.exists(f)), None)

def font(size, bold=False):
    idx = 1 if bold else 0
    if font_path and font_path.endswith('.ttc'):
        return ImageFont.truetype(font_path, size, index=idx)
    elif font_path:
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# --- Contrast check ---
def luminance(rgb):
    r, g, b = [c/255.0 for c in rgb]
    r = r/12.92 if r <= 0.03928 else ((r+0.055)/1.055)**2.4
    g = g/12.92 if g <= 0.03928 else ((g+0.055)/1.055)**2.4
    b = b/12.92 if b <= 0.03928 else ((b+0.055)/1.055)**2.4
    return 0.2126*r + 0.7152*g + 0.0722*b

def cr(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    if l1 < l2: l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

for name, color in [("TEXT", TEXT), ("META", META), ("ORGANIC", ORGANIC), ("TOP_AD", TOP_AD), ("NATIVE", NATIVE)]:
    ratio = cr(color, BG)
    status = "OK" if ratio >= 8.0 else f"WARN ({ratio:.1f}:1)"
    print(f"  {name:>10s} {color} on {BG}: {ratio:.1f}:1 {status}")

# --- Create canvas ---
img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)

# Panel dividers
for x in [PANEL_W, PANEL_W * 2]:
    draw.line([(x, 30), (x, H - 30)], fill=GRID, width=1)

# === Panel 1: Arc shapes ===
p1_cx, p1_cy = PANEL_W // 2, H // 2 + 20

# Draw a simplified SERP result AOI
aoi_w, aoi_h = 200, 50
aoi_left = p1_cx - aoi_w // 2
aoi_top = p1_cy - aoi_h // 2
draw.rectangle([aoi_left, aoi_top, aoi_left + aoi_w, aoi_top + aoi_h],
               outline=(60, 60, 65), width=2)
draw.text((aoi_left + 8, aoi_top + 14), "Result AOI", fill=META, font=font(16))

# Draw retreat arcs from AOI center
# Organic: short, straight (arc_ratio 1.08, lateral 3px)
# Top Ad: long, curved (arc_ratio 2.36, lateral 37px)
# Native Ad: medium, mostly straight (arc_ratio 1.17, lateral 11px)

def draw_arc(cx, cy, retreat_dist, arc_ratio, lateral, color, label, label_side='right'):
    """Draw a retreat arc from AOI center outward."""
    # Scale for visualization
    scale = 0.4
    dist = retreat_dist * scale
    lat = lateral * scale * 8  # amplify lateral for visibility

    # Generate arc points (quadratic bezier approximation)
    points = []
    n_steps = 40
    # Start at AOI bottom center
    sx, sy = cx, cy + aoi_h // 2
    # End point: below, offset by lateral
    ex = cx + lat
    ey = sy + dist
    # Control point: adds the curvature
    cpx = cx + lat * arc_ratio * 0.6
    cpy = sy + dist * 0.5

    for i in range(n_steps + 1):
        t = i / n_steps
        # Quadratic bezier
        x = (1-t)**2 * sx + 2*(1-t)*t * cpx + t**2 * ex
        y = (1-t)**2 * sy + 2*(1-t)*t * cpy + t**2 * ey
        points.append((x, y))

    # Draw the arc
    for i in range(len(points) - 1):
        # Fade alpha along the arc
        alpha = max(0.3, 1.0 - i / len(points) * 0.6)
        c = tuple(int(v * alpha) for v in color)
        draw.line([points[i], points[i+1]], fill=c, width=3)

    # Arrowhead at end
    ex, ey = points[-1]
    draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=color)

    # Max retreat distance marker
    max_pt = max(points, key=lambda p: math.sqrt((p[0]-cx)**2 + (p[1]-cy)**2))
    draw.line([(cx, max_pt[1]), (max_pt[0], max_pt[1])], fill=(*color[:3], 80), width=1)

    # Label
    lx = ex + (12 if label_side == 'right' else -12)
    anchor = 'la' if label_side == 'right' else 'ra'
    draw.text((lx, ey - 8), label, fill=color, font=font(14, bold=True))


draw_arc(p1_cx - 30, p1_cy, 530, 1.08, 3, ORGANIC, "Organic", 'left')
draw_arc(p1_cx, p1_cy, 384, 2.36, 37, TOP_AD, "Top Ad", 'right')
draw_arc(p1_cx + 25, p1_cy, 433, 1.17, 11, NATIVE, "Native Ad", 'right')

# Panel 1 title
draw.text((PANEL_W // 2, 35), "Retreat Arc Shape", fill=TEXT, font=font(20, bold=True), anchor='mt')
draw.text((PANEL_W // 2, 60), "Arc ratio: path length / direct distance", fill=META, font=font(13), anchor='mt')

# Panel 1 stats
stats_y = H - 90
draw.text((30, stats_y), "Arc ratio (median)", fill=META, font=font(12))
draw.text((30, stats_y + 18), "Organic: 1.08", fill=ORGANIC, font=font(13, bold=True))
draw.text((30, stats_y + 36), "Top Ad:  2.36  (p = 1.4e-9)", fill=TOP_AD, font=font(13, bold=True))
draw.text((30, stats_y + 54), "Native:  1.17", fill=NATIVE, font=font(13, bold=True))

# === Panel 2: Fitts' Law ID ===
p2_x = PANEL_W + 40
p2_right = PANEL_W * 2 - 40
bar_w = p2_right - p2_x - 120

draw.text((PANEL_W + PANEL_W // 2, 35), "Fitts' Law ID", fill=TEXT, font=font(20, bold=True), anchor='mt')
draw.text((PANEL_W + PANEL_W // 2, 60), "ID = log\u2082(2D/W)  \u2014  re-acquisition cost in bits", fill=META, font=font(13), anchor='mt')

# Data: Fitts ID by type and re-approach status
fitts_data = [
    ("Organic", 2.56, 530, ORGANIC),
    ("Native Ad", 2.27, 433, NATIVE),
    ("Top Ad", 2.09, 384, TOP_AD),
]

# Horizontal bar chart
bar_top = 110
bar_h = 55
bar_gap = 25
max_fitts = 3.0

for i, (label, fitts_id, retreat_px, color) in enumerate(fitts_data):
    y = bar_top + i * (bar_h + bar_gap)

    # Label
    draw.text((p2_x, y + 4), label, fill=color, font=font(15, bold=True))

    # Bar
    bx = p2_x + 100
    bw = int((fitts_id / max_fitts) * bar_w)
    draw.rectangle([bx, y + 2, bx + bw, y + bar_h - 2], fill=(*color, 180))

    # Value label
    draw.text((bx + bw + 8, y + 14), f"{fitts_id:.2f} bits", fill=TEXT, font=font(16, bold=True))

    # Retreat distance annotation
    draw.text((bx + bw + 8, y + 34), f"({retreat_px} px retreat)", fill=META, font=font(11))

# Re-approach comparison
reapp_y = bar_top + 3 * (bar_h + bar_gap) + 20
draw.line([(p2_x, reapp_y), (p2_right, reapp_y)], fill=GRID, width=1)
draw.text((p2_x, reapp_y + 12), "Re-approached (deferred):", fill=META, font=font(13))
draw.text((p2_x + 200, reapp_y + 12), "2.21 bits", fill=TEXT, font=font(14, bold=True))
draw.text((p2_x, reapp_y + 32), "Not re-approached (rejected):", fill=META, font=font(13))
draw.text((p2_x + 200, reapp_y + 32), "2.31 bits", fill=TEXT, font=font(14, bold=True))
draw.text((p2_x, reapp_y + 55), "U = 2980, p = .035  \u2014  lower cost \u2192 more likely to return", fill=META, font=font(12))

# Interpretation
interp_y = reapp_y + 85
draw.text((p2_x, interp_y), "Shorter retreat = lower re-acquisition cost", fill=TEXT, font=font(13))
draw.text((p2_x, interp_y + 20), "= cursor stays close = still considering", fill=TEXT, font=font(13))
draw.text((p2_x, interp_y + 40), "= DEFERRED, not REJECTED", fill=(*ORGANIC, 200), font=font(14, bold=True))

# === Panel 3: Lateral displacement ===
p3_x = PANEL_W * 2 + 40
p3_right = W - 40

draw.text((PANEL_W * 2 + PANEL_W // 2, 35), "Lateral Displacement", fill=TEXT, font=font(20, bold=True), anchor='mt')
draw.text((PANEL_W * 2 + PANEL_W // 2, 60), "Sideways drift = uncertainty / deliberation", fill=META, font=font(13), anchor='mt')

# Lateral ratio data
lat_data = [
    ("Organic", 0.006, 0.061, 149, ORGANIC),
    ("Native Ad", 0.027, 0.077, 75, NATIVE),
    ("Top Ad", 0.103, 0.150, 94, TOP_AD),
]

# Dot plot with median + mean
plot_top = 120
plot_h = 300
plot_left = p3_x + 100
plot_right = p3_right - 30
max_lat = 0.20

# Axis
draw.line([(plot_left, plot_top + plot_h), (plot_right, plot_top + plot_h)], fill=META, width=1)
# Tick marks
for v in [0.0, 0.05, 0.10, 0.15, 0.20]:
    x = plot_left + int((v / max_lat) * (plot_right - plot_left))
    draw.line([(x, plot_top + plot_h), (x, plot_top + plot_h + 6)], fill=META, width=1)
    draw.text((x, plot_top + plot_h + 10), f"{v:.2f}", fill=META, font=font(11), anchor='mt')

draw.text((plot_left + (plot_right - plot_left) // 2, plot_top + plot_h + 30),
          "Lateral ratio (lateral / max retreat dist)", fill=META, font=font(12), anchor='mt')

row_h = plot_h // 3
for i, (label, median, mean, n, color) in enumerate(lat_data):
    y = plot_top + i * row_h + row_h // 2

    # Label
    draw.text((p3_x, y - 8), label, fill=color, font=font(14, bold=True))
    draw.text((p3_x, y + 10), f"n={n}", fill=META, font=font(11))

    # Median marker (diamond)
    mx = plot_left + int((median / max_lat) * (plot_right - plot_left))
    diamond_size = 8
    draw.polygon([(mx, y - diamond_size), (mx + diamond_size, y),
                  (mx, y + diamond_size), (mx - diamond_size, y)], fill=color)

    # Mean marker (circle)
    mean_x = plot_left + int((mean / max_lat) * (plot_right - plot_left))
    draw.ellipse([mean_x - 5, y - 5, mean_x + 5, y + 5], outline=color, width=2)

    # Connect median to mean
    draw.line([(mx, y), (mean_x, y)], fill=(*color, 120), width=2)

# Legend
leg_y = plot_top + plot_h + 55
draw.polygon([(p3_x + 10, leg_y), (p3_x + 18, leg_y + 8),
              (p3_x + 10, leg_y + 16), (p3_x + 2, leg_y + 8)], fill=META)
draw.text((p3_x + 24, leg_y + 1), "= median", fill=META, font=font(12))
draw.ellipse([p3_x + 100, leg_y + 2, p3_x + 112, leg_y + 14], outline=META, width=2)
draw.text((p3_x + 118, leg_y + 1), "= mean", fill=META, font=font(12))

# Key finding
key_y = leg_y + 30
draw.text((p3_x, key_y), "Top Ads: 17x more lateral drift than Organic", fill=TOP_AD, font=font(14, bold=True))
draw.text((p3_x, key_y + 22), "U = 4129, p = 4.7e-8", fill=META, font=font(12))
draw.text((p3_x, key_y + 44), "Lateral = cursor exploring alternatives", fill=TEXT, font=font(13))
draw.text((p3_x, key_y + 64), "during retreat \u2014 the discrimination cost", fill=TEXT, font=font(13))
draw.text((p3_x, key_y + 84), "made visible in motor behavior", fill=TEXT, font=font(13))

# Save
out_path = os.path.expanduser('~/Documents/dev/approach-retreat/docs/drafts/retreat-arc-geometry.png')
img.save(out_path, 'PNG')
print(f"\nSaved: {out_path}")
print(f"Size: {W}x{H}")
