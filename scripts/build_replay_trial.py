"""Build a per-trial replay bundle for the approach-retreat AdSERP viewer.

For each trial:
- Copy the full-page screenshot into site/replay/data/png/
- Read raw mouse-movement, fixation, pupil CSVs from the AdSERP cache
- Read ad-boundary + organic-boundary JSONs
- Read trial metadata XML for window/document dims
- Scale cursor xpos to 1280-wide screenshot space (ypos stays document-space)
- Compute xy-delta (cursor speed in px/ms per sample)
- Emit one consolidated site/replay/data/trials/{trial_id}.json

Run:
    python3 scripts/build_replay_trial.py p007-b6-t8 p013-b2-t3 ...
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

AF_ROOT = Path.home() / "Documents/dev/attentional-foraging/AdSERP/data"
AR_ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = AR_ROOT / "site/replay/data"
PNG_OUT = SITE_DATA / "png"
TRIALS_OUT = SITE_DATA / "trials"

SCREENSHOT_WIDTH = 1280  # all shipped PNGs are 1280px wide


def parse_metadata(trial_id: str) -> dict:
    xml = AF_ROOT / "trial-metadata" / f"{trial_id}.xml"
    root = ET.fromstring(xml.read_text())
    win = root.findtext("window") or "1280x1024"
    doc = root.findtext("document") or "1280x1024"
    win_w, win_h = (int(v) for v in win.split("x"))
    doc_w, doc_h = (int(v) for v in doc.split("x"))
    return {
        "url": root.findtext("url") or "",
        "task": root.findtext("task") or "",
        "win_width": win_w, "win_height": win_h,
        "doc_width": doc_w, "doc_height": doc_h,
    }


def read_cursor(trial_id: str, t0_ms: int, ratio_x: float) -> tuple[list[dict], list[dict]]:
    """Return (cursor_samples, xy_delta_samples). Cursor xpos scaled to screenshot space."""
    csv_path = AF_ROOT / "mouse-movement-data" / f"{trial_id}.csv"
    cursor: list[dict] = []
    last_x = last_y = last_t = None
    deltas: list[dict] = []
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            event = row["event"]
            if event not in {"mousemove", "click", "scroll"}:
                continue
            t = int(row["timestamp"]) - t0_ms
            x = int(round(int(row["xpos"]) * ratio_x))
            y = int(float(row["ypos"]))  # document-space — no scaling
            cursor.append({"t": t, "x": x, "y": y, "event": event})
            if event == "mousemove" and last_x is not None and t > last_t:
                dx, dy, dt = x - last_x, y - last_y, t - last_t
                speed = (dx * dx + dy * dy) ** 0.5 / dt  # px per ms
                deltas.append({"t": t, "speed": round(speed, 2)})
            if event == "mousemove":
                last_x, last_y, last_t = x, y, t
    return cursor, deltas


def read_fixations(trial_id: str, t0_ms: int) -> list[dict]:
    csv_path = AF_ROOT / "fixation-data" / f"{trial_id}.csv"
    out: list[dict] = []
    if not csv_path.exists():
        return out
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            out.append({
                "t": int(row["timestamp"]) - t0_ms,
                "x": int(float(row["FPOGX"])),
                "y": int(float(row["FPOGY"])),
                "duration": int(row["FPOGD"]),
            })
    return out


def read_pupil(trial_id: str, t0_ms: int) -> list[dict]:
    csv_path = AF_ROOT / "pupil-data" / f"{trial_id}.csv"
    out: list[dict] = []
    if not csv_path.exists():
        return out
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            lpd = float(row["LPD"]) if row["LPV"] == "1" else None
            rpd = float(row["RPD"]) if row["RPV"] == "1" else None
            if lpd is None and rpd is None:
                continue
            out.append({
                "t": int(row["timestamp"]) - t0_ms,
                "lpd": lpd, "rpd": rpd,
            })
    return out


def trial_t0(trial_id: str) -> int:
    """Earliest timestamp across mouse + fixation + pupil — defines t=0."""
    candidates: list[int] = []
    for sub in ("mouse-movement-data", "fixation-data", "pupil-data"):
        p = AF_ROOT / sub / f"{trial_id}.csv"
        if not p.exists():
            continue
        with p.open() as fh:
            reader = csv.reader(fh)
            next(reader)  # header
            for row in reader:
                candidates.append(int(row[0]))
                break
    if not candidates:
        raise FileNotFoundError(f"no signal data for {trial_id}")
    return min(candidates)


def build_trial(trial_id: str) -> dict | None:
    png = AF_ROOT / "full-page-screenshots" / f"{trial_id}.png"
    ad_json = AF_ROOT / "ad-boundary-data" / f"{trial_id}.json"
    organic_json = AF_ROOT / "organic-boundary-data" / f"{trial_id}.json"

    if not png.exists():
        print(f"  SKIP {trial_id}: screenshot missing", file=sys.stderr)
        return None
    if not ad_json.exists() or not organic_json.exists():
        print(f"  SKIP {trial_id}: bbox JSONs missing", file=sys.stderr)
        return None

    meta = parse_metadata(trial_id)
    t0 = trial_t0(trial_id)
    ratio_x = SCREENSHOT_WIDTH / meta["win_width"]

    cursor, xy_delta = read_cursor(trial_id, t0, ratio_x)
    fixations = read_fixations(trial_id, t0)
    pupil = read_pupil(trial_id, t0)

    duration_ms = max(
        cursor[-1]["t"] if cursor else 0,
        fixations[-1]["t"] if fixations else 0,
        pupil[-1]["t"] if pupil else 0,
    )

    PNG_OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(png, PNG_OUT / png.name)

    organic = json.loads(organic_json.read_text())

    return {
        "trial_id": trial_id,
        "screenshot": f"png/{png.name}",
        "screenshot_width": SCREENSHOT_WIDTH,
        "doc_height": meta["doc_height"],
        "win_width": meta["win_width"],
        "ratio_x": round(ratio_x, 4),
        "duration_ms": duration_ms,
        "task": meta["task"],
        "url": meta["url"],
        "bboxes": {
            "organic_result": organic.get("organic_result", []),
            "native_ad":  organic.get("native_ad", []),
            "dd_top":     organic.get("dd_top", []),
            "dd_right":   organic.get("dd_right", []),
        },
        "cursor": cursor,
        "xy_delta": xy_delta,
        "fixations": fixations,
        "pupil": pupil,
        "_meta": {
            "source": "AdSERP raw signals — no NB15 derivatives",
            "t0_unix_ms": t0,
            "n_cursor": len(cursor),
            "n_fixations": len(fixations),
            "n_pupil": len(pupil),
        },
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    TRIALS_OUT.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    for tid in sys.argv[1:]:
        bundle = build_trial(tid)
        if bundle is None:
            continue
        out = TRIALS_OUT / f"{tid}.json"
        out.write_text(json.dumps(bundle))
        m = bundle["_meta"]
        print(f"  {tid}: {m['n_cursor']} cursor, {m['n_fixations']} fix, {m['n_pupil']} pupil — {bundle['duration_ms']}ms")
        n_ok += 1
    print(f"\nWrote {n_ok}/{len(sys.argv) - 1} → {TRIALS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
