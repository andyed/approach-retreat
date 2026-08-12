#!/usr/bin/env python3
"""Export AdSERP replay-trial AOIs as EyeLink .ias files for the PAI demo.

Target consumer: Duchowski's glias2poly_1920x1080.py (b2b PAI demo,
http://andrewd.ces.clemson.edu/pai/b2b/). Its parser:

  - skips lines starting with '#' or '!'
  - matches: FREEHAND <int-id> <x,y x,y ...> <label>  (label = \\S+, no spaces)
  - keys polygons by LABEL, so labels must be unique per file
  - OGD = min distance to a VERTEX (not to an edge), so rectangle perimeters
    are densified (~VERTEX_STEP_PX spacing) to make OGD approximate true
    boundary distance, matching the ~1px vertex spacing of his freehand files
  - shoelace area uses abs(), so winding is cosmetic; we emit visually-CCW
    (TL -> BL -> BR -> TR in y-down screen coords) per his note

Coordinates: screenshot pixel space of the replay JPGs (1280 wide, y-down),
identical to site/replay/data/trials/*.json bboxes. Two variants per trial:

  full/  — full-page canvas (1280 x doc image height), every AOI
  fold/  — above-the-fold crop (1280 x 1080): AOIs fully below the fold are
           dropped; straddlers are clipped to y <= 1080

Usage:
  python3 scripts/export_ias.py [trial_id ...]     # default: the 3 hero trials
  python3 scripts/export_ias.py --all              # all curated trials
Output: scripts/output/ias/{full,fold}/<trial>.ias (+ copied screenshots)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRIALS_DIR = REPO / "site" / "replay" / "data" / "trials"
PNG_DIR = REPO / "site" / "replay" / "data" / "png"
OUT_DIR = REPO / "scripts" / "output" / "ias"

HERO_TRIALS = ["p006-b4-t7", "p047-b6-t1", "p019-b1-t8"]

VERTEX_STEP_PX = 4.0   # perimeter sampling step; OGD error <= step/2
FOLD_HEIGHT = 1080     # above-the-fold crop height (his demo default window)
CANVAS_W = 1280        # replay screenshot width

# AOI kinds to export, in z-order. Parent containers (dd_top, dd_right) are
# skipped when their cells are present — nested polygons double-count in a
# per-AOI PAI display. Widgets are included: they're real competition for
# peripheral attention on the SERP.
KIND_ORDER = ["organic_result", "native_ad", "dd_top", "dd_right",
              "dd_top_cell", "dd_right_cell", "widget"]
PARENT_OF = {"dd_top_cell": "dd_top", "dd_right_cell": "dd_right"}


def rect_perimeter(x, y, w, h, step=VERTEX_STEP_PX):
    """Densified rectangle perimeter, visually-CCW in y-down coords:
    top-left -> down left edge -> bottom edge -> up right edge -> top edge."""
    import numpy as np
    x2, y2 = x + w, y + h
    left = [(x, yy) for yy in np.arange(y, y2, step)]
    bottom = [(xx, y2) for xx in np.arange(x, x2, step)]
    right = [(x2, yy) for yy in np.arange(y2, y, -step)]
    top = [(xx, y) for xx in np.arange(x2, x, -step)]
    return left + bottom + right + top


def aoi_label(kind, item, widget_seen):
    """Unique single-token label per AOI (his parser keys a dict by label)."""
    if kind == "organic_result":
        return f"organic_{item.get('position')}"
    if kind in ("dd_top_cell", "dd_right_cell"):
        return f"{kind}_{item.get('position')}"
    if kind == "widget":
        wtype = item.get("type") or "widget"
        widget_seen[wtype] = widget_seen.get(wtype, 0) + 1
        return f"{wtype}_{widget_seen[wtype]}"
    if kind in ("dd_top", "dd_right"):
        return kind
    if kind == "native_ad":
        widget_seen["native_ad"] = widget_seen.get("native_ad", 0) + 1
        return f"native_ad_{widget_seen['native_ad']}"
    widget_seen[kind] = widget_seen.get(kind, 0) + 1
    return f"{kind}_{widget_seen[kind]}"


def export_trial(trial_id, fold=False):
    data = json.loads((TRIALS_DIR / f"{trial_id}.json").read_text())
    bboxes = data["bboxes"]
    lines = [
        f"# EyeLink Interest Area Set — AdSERP trial {trial_id}",
        "# Source: AllSERP AOIs (arXiv:2605.04949) on AdSERP "
        "(Latifzadeh, Gwizdka & Leiva, SIGIR 2025)",
        f"# Canvas: {CANVAS_W}x{FOLD_HEIGHT if fold else 'full-page'} px, "
        "y=0 at top, screenshot pixel space",
        "# Rect perimeters densified to ~%gpx vertex spacing so vertex-based "
        "OGD approximates boundary distance" % VERTEX_STEP_PX,
    ]
    widget_seen = {}
    next_id = 1
    n_dropped = 0
    for kind in KIND_ORDER:
        items = bboxes.get(kind) or []
        # Skip parent containers whose cells are present (avoid nesting)
        if kind in ("dd_top", "dd_right") and bboxes.get(kind + "_cell"):
            continue
        for item in items:
            x = float(item["location"]["x"])
            y = float(item["location"]["y"])
            w = float(item["size"]["width"])
            h = float(item["size"]["height"])
            if fold:
                if y >= FOLD_HEIGHT:      # entirely below the fold
                    n_dropped += 1
                    continue
                h = min(h, FOLD_HEIGHT - y)  # clip straddlers
            label = aoi_label(kind, item, widget_seen)
            verts = rect_perimeter(x, y, w, h)
            coords = " ".join(f"{vx:.1f},{vy:.1f}" for vx, vy in verts)
            lines.append(f"FREEHAND\t{next_id}\t{coords} \t{label}")
            next_id += 1
    return "\n".join(lines) + "\n", next_id - 1, n_dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trials", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        trial_ids = sorted(p.stem for p in TRIALS_DIR.glob("*.json"))
    else:
        trial_ids = args.trials or HERO_TRIALS

    for variant in ("full", "fold"):
        (OUT_DIR / variant).mkdir(parents=True, exist_ok=True)

    for tid in trial_ids:
        for variant, fold in (("full", False), ("fold", True)):
            text, n, dropped = export_trial(tid, fold=fold)
            out = OUT_DIR / variant / f"{tid}.ias"
            out.write_text(text)
            note = f" ({dropped} below-fold AOIs dropped)" if dropped else ""
            print(f"{out.relative_to(REPO)}: {n} AOIs{note}")
        jpg = PNG_DIR / f"{tid}.jpg"
        if jpg.exists():
            shutil.copy(jpg, OUT_DIR / "full" / jpg.name)


if __name__ == "__main__":
    main()
