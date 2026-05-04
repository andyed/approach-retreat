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

from PIL import Image
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


# ── LF/HF Butterworth (Duchowski 2026 IIR) ──────────────────────────────
# Ported from attentional-foraging/scripts/compute_butterworth_lfhf.py.
# Computes a sliding-window LF/HF track from raw pupil samples for the
# AR viewer's cognitive-load timeline.
LFHF_FS = 150          # Gazepoint GP3 HD sampling rate
LFHF_ORDER = 4
LFHF_LF_CUTOFF = 1.6   # Hz — lowpass for LF band (0–1.6 Hz)
LFHF_HF_BAND = (1.6, 4.0)
LFHF_WIN_SAMPLES = 750  # 5s window
LFHF_STEP_SAMPLES = 38  # ~250ms step


def compute_lfhf_track(pupil: list[dict]) -> list[dict]:
    """Time-varying LF/HF ratio computed in sliding 5s windows over the
    mean-pooled L+R pupil stream. Returns [{"t": ms, "lfhf": float}, ...].
    Empty if scipy unavailable or insufficient samples.
    """
    if len(pupil) < LFHF_WIN_SAMPLES:
        return []
    try:
        import numpy as np
        from scipy.signal import butter, sosfiltfilt
    except ImportError:
        return []

    ts = np.array([s["t"] for s in pupil])
    # Mean of available eyes (treat None as that-eye-missing)
    pd = np.array([
        ((s["lpd"] or 0) + (s["rpd"] or 0)) /
        max(1, (1 if s["lpd"] else 0) + (1 if s["rpd"] else 0))
        for s in pupil
    ], dtype=float)

    # Resample-uniform: pupil samples are already at ~150Hz but with jitter.
    # The AF reference implementation just uses the raw stream — we do the same.
    lf_sos = butter(LFHF_ORDER, LFHF_LF_CUTOFF, btype="low",  fs=LFHF_FS, output="sos")
    hf_sos = butter(LFHF_ORDER, LFHF_HF_BAND,  btype="band", fs=LFHF_FS, output="sos")
    try:
        lf_signal = sosfiltfilt(lf_sos, pd)
        hf_signal = sosfiltfilt(hf_sos, pd)
    except ValueError:
        return []

    out: list[dict] = []
    n = len(pd)
    half = LFHF_WIN_SAMPLES // 2
    for c in range(half, n - half, LFHF_STEP_SAMPLES):
        lo, hi = c - half, c + half
        lf_var = float(np.var(lf_signal[lo:hi]))
        hf_var = float(np.var(hf_signal[lo:hi]))
        if hf_var < 1e-20:
            continue
        ratio = lf_var / hf_var
        out.append({"t": int(ts[c]), "lfhf": round(ratio, 4)})
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


_M5_CLF = None  # lazy-loaded


def _m5() -> "m5_inference.M5Classifier":
    global _M5_CLF
    if _M5_CLF is None:
        import m5_inference
        _M5_CLF = m5_inference.M5Classifier()
    return _M5_CLF


_AOI_CORRECTIONS_PATH = AR_ROOT / "site/replay/data/aoi_corrections.json"
_AOI_CORRECTIONS_CACHE: dict | None = None


def _load_aoi_corrections() -> dict:
    global _AOI_CORRECTIONS_CACHE
    if _AOI_CORRECTIONS_CACHE is not None:
        return _AOI_CORRECTIONS_CACHE
    if _AOI_CORRECTIONS_PATH.exists():
        _AOI_CORRECTIONS_CACHE = json.loads(_AOI_CORRECTIONS_PATH.read_text())
    else:
        _AOI_CORRECTIONS_CACHE = {}
    return _AOI_CORRECTIONS_CACHE


def apply_aoi_corrections(trial_id: str, organic: dict) -> dict:
    """Apply human-adjudicated AOI corrections from aoi_corrections.json.

    Currently supports `demote_to_widget`: a list of organic positions to
    reclassify as widget. Remaining organic positions are renumbered
    contiguously. The demoted bbox is appended to organic['widget'] with
    `reason: 'manual_correction'`.
    """
    corrections = _load_aoi_corrections().get(trial_id)
    if not corrections:
        return organic
    demote = set(corrections.get("demote_to_widget", []))
    if not demote:
        return organic
    organics = organic.get("organic_result", [])
    kept, moved = [], []
    for r in organics:
        if r.get("position") in demote:
            moved.append({**r, "reason": "manual_correction"})
        else:
            kept.append(r)
    for i, r in enumerate(kept, 1):
        r["position"] = i
    organic["organic_result"] = kept
    organic["widget"] = list(organic.get("widget", [])) + moved
    return organic


def derive_aoi_labels(cursor: list[dict], bboxes: dict, min_dwell_ms: int = 100) -> dict:
    """For each AOI, assign a four-class label using M5 (primary) and a
    bbox episode-count heuristic (secondary, for comparison).

    Both classifiers operate on cursor + AOI bbox, no gaze. They disagree
    on what "DEFERRED" means:
      - HEURISTIC: cursor literally entered the bbox ≥2 times (with each
        episode dwell ≥ min_dwell_ms).
      - M5: cursor signature looks deferred-like (close approach + dwell
        + retreat) per LR coefficients learned against NB22 gaze labels.
        See scripts/m5_inference.py.

    Per-AOI output:
      label              — final canonical label (M5-primary, see below)
      m5_label           — M5's prediction (DEFERRED / EVALUATED_REJECTED / NOT_APPROACHED)
      m5_proba           — M5 P(deferred), or None if not approached
      heuristic_label    — bbox episode-count heuristic label
      episodes           — bbox episode count (heuristic input)
      total_dwell_ms     — sum of bbox episode dwells

    Final label rules (priority):
      CLICKED            — any bbox episode contains a click event
      M5 if extractable  — M5_label (DEFERRED or EVALUATED_REJECTED)
      NOT_APPROACHED     — M5 features not extractable AND no bbox episodes
    """
    import m5_inference  # noqa: E402  (module under scripts/, sys.path appended by caller)
    def hit(x: float, y: float, b: dict) -> bool:
        bx, by = b["location"]["x"], b["location"]["y"]
        bw, bh = b["size"]["width"], b["size"]["height"]
        return bx <= x <= bx + bw and by <= y <= by + bh

    clf = _m5()
    moves = [s for s in cursor if s.get("event") == "mousemove"]

    out: dict[str, list[dict]] = {}
    for kind, items in bboxes.items():
        out[kind] = []
        for idx, item in enumerate(items):
            # ── Heuristic: bbox episode count ────────────────────────────
            episodes = []
            inside = False
            enter_t = None
            had_click = False
            had_click_this_ep = False
            for s in cursor:
                in_now = hit(s["x"], s["y"], item)
                if in_now and not inside:
                    enter_t = s["t"]
                    inside = True
                    had_click_this_ep = False
                elif inside and (s.get("event") == "click" or s.get("event") == "mousedown") and in_now:
                    had_click_this_ep = True
                elif inside and not in_now:
                    dwell = s["t"] - (enter_t or s["t"])
                    if dwell >= min_dwell_ms:
                        episodes.append({"enter_t": enter_t, "exit_t": s["t"], "dwell": dwell, "click": had_click_this_ep})
                        if had_click_this_ep:
                            had_click = True
                    inside = False
                    had_click_this_ep = False
            if inside:
                dwell = (cursor[-1]["t"] if cursor else 0) - (enter_t or 0)
                if dwell >= min_dwell_ms:
                    episodes.append({"enter_t": enter_t, "exit_t": None, "dwell": dwell, "click": had_click_this_ep})
                    if had_click_this_ep:
                        had_click = True

            n_ep = len(episodes)
            if had_click:
                heuristic_label = "CLICKED"
            elif n_ep >= 2:
                heuristic_label = "DEFERRED"
            elif n_ep == 1:
                heuristic_label = "EVALUATED_REJECTED"
            else:
                heuristic_label = "NOT_APPROACHED"

            # ── M5 inference (organic AOIs only — M5's training population) ──
            m5_proba = None
            m5_label = "NOT_APPROACHED"
            if kind == "organic_result":
                feats = m5_inference.extract_m5_features(moves, m5_inference.aoi_y_center(item))
                if feats is not None:
                    m5_proba = clf.predict_proba(feats)
                    m5_label = clf.predict_label(feats)

            # ── Final canonical label: CLICKED > M5 (organic) > heuristic (ads) ──
            if had_click:
                label = "CLICKED"
            elif kind == "organic_result":
                label = m5_label
            else:
                label = heuristic_label

            entry = {
                "kind": kind,
                "label": label,
                "m5_label": m5_label,
                "m5_proba": round(m5_proba, 4) if m5_proba is not None else None,
                "heuristic_label": heuristic_label,
                "episodes": n_ep,
                "total_dwell_ms": sum(e["dwell"] for e in episodes),
            }
            if "position" in item:
                entry["position"] = item["position"]
            entry["bbox_index"] = idx
            out[kind].append(entry)
    return out


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
    lfhf = compute_lfhf_track(pupil)

    duration_ms = max(
        cursor[-1]["t"] if cursor else 0,
        fixations[-1]["t"] if fixations else 0,
        pupil[-1]["t"] if pupil else 0,
    )

    PNG_OUT.mkdir(parents=True, exist_ok=True)
    jpg_name = f"{trial_id}.jpg"
    jpg_out = PNG_OUT / jpg_name
    if not jpg_out.exists():
        Image.open(png).convert("RGB").save(jpg_out, "JPEG", quality=85, optimize=True)

    organic = json.loads(organic_json.read_text())
    organic = apply_aoi_corrections(trial_id, organic)

    # Load typed AOI map (HTML+vision joint typing) and pull non-ad widgets
    # into the `widget` bbox slot. When the typed map is available it
    # supersedes the unlabeled CV widgets in organic-boundary-data; when
    # absent we fall back to the legacy unlabeled widget list.
    typed_aoi_path = (Path.home() / "Documents/dev/attentional-foraging"
                      / "data/aoi-typed" / f"{trial_id}.json")
    if typed_aoi_path.exists():
        widget_bboxes = []
        typed_cards = json.loads(typed_aoi_path.read_text())
        widget_types = {"image_pack", "knowledge_panel", "paa", "top_places",
                        "related_searches", "other_widget", "unknown_widget"}
        for c in typed_cards:
            if c.get("position", -1) < 0:
                continue  # off-axis (chrome / dd_right / botstuff / rhs)
            if c.get("type") not in widget_types:
                continue
            if c.get("x") is None or c.get("y") is None:
                continue
            widget_bboxes.append({
                "location": {"x": float(c["x"]), "y": float(c["y"])},
                "size": {"width": float(c["width"]), "height": float(c["height"])},
                "type": c["type"],
                "html_handle": c.get("html_handle"),
            })

        # Pagination + related_searches live in #botstuff. Pagination has no
        # CV bbox; related_searches has none either. Estimate both:
        #   - pagination: anchored on JPG bottom (last 150 px of screenshot)
        #   - related_searches: between deepest main-axis card and pagination
        # Also: surface CV-detected chrome bboxes (footer/pagination-zone
        # cells the chrome heuristic swept off-axis but have real coords).
        pagination_cards = [c for c in typed_cards if c.get('type') == 'pagination']
        related_searches_cards = [c for c in typed_cards if c.get('type') == 'related_searches']
        chrome_with_coords = [c for c in typed_cards
                              if c.get('type') == 'chrome'
                              and c.get('x') is not None and c.get('y') is not None]

        # Compute pagination y from JPG height
        pag_y = None
        pag_h = 80.0
        if pagination_cards and jpg_out.exists():
            try:
                _img = Image.open(jpg_out)
                jpg_h = _img.height
            except Exception:
                jpg_h = None
            if jpg_h:
                pag_y = max(0.0, float(jpg_h) - 150.0)

        # Deepest main-axis card bottom (organic + ad in display order)
        last_card_bottom = 0.0
        for c in typed_cards:
            if (c.get('position', -1) >= 0 and c.get('y') is not None
                    and c.get('height') is not None):
                last_card_bottom = max(last_card_bottom,
                                        float(c['y']) + float(c['height']))

        # related_searches: spans from last_card_bottom to pagination_y
        if related_searches_cards and last_card_bottom > 0 and pag_y is not None:
            rs_y = last_card_bottom + 30.0
            rs_h = max(60.0, pag_y - rs_y - 20.0)
            widget_bboxes.append({
                "location": {"x": 162.0, "y": rs_y},
                "size": {"width": 586.0, "height": rs_h},
                "type": "related_searches",
                "html_handle": related_searches_cards[0].get("html_handle"),
                "estimated": True,
            })

        # chrome cells (CV-detected with coords; page-furniture-zone)
        for c in chrome_with_coords:
            widget_bboxes.append({
                "location": {"x": float(c['x']), "y": float(c['y'])},
                "size": {"width": float(c['width']), "height": float(c['height'])},
                "type": "chrome",
                "html_handle": None,
            })

        # pagination overlay (after rs_searches so it visually layers on top)
        if pagination_cards and pag_y is not None:
            widget_bboxes.append({
                "location": {"x": 162.0, "y": pag_y},
                "size": {"width": 586.0, "height": pag_h},
                "type": "pagination",
                "html_handle": pagination_cards[0].get("html_handle"),
                "estimated": True,
            })
    else:
        widget_bboxes = list(organic.get("widget", []))

    bboxes = {
        "organic_result": organic.get("organic_result", []),
        "native_ad":  organic.get("native_ad", []),
        "dd_top":     organic.get("dd_top", []),
        "dd_right":   organic.get("dd_right", []),
        "widget":     widget_bboxes,
    }
    aoi_labels = derive_aoi_labels(cursor, bboxes)

    return {
        "trial_id": trial_id,
        "screenshot": f"png/{jpg_name}",
        "screenshot_width": SCREENSHOT_WIDTH,
        "doc_height": meta["doc_height"],
        "win_width": meta["win_width"],
        "ratio_x": round(ratio_x, 4),
        "duration_ms": duration_ms,
        "task": meta["task"],
        "url": meta["url"],
        "bboxes": bboxes,
        "aoi_labels": aoi_labels,
        "cursor": cursor,
        "xy_delta": xy_delta,
        "fixations": fixations,
        "pupil": pupil,
        "lfhf": lfhf,
        "_meta": {
            "source": "AdSERP raw signals — no NB15 derivatives",
            "t0_unix_ms": t0,
            "n_cursor": len(cursor),
            "n_fixations": len(fixations),
            "n_pupil": len(pupil),
            "label_summary": {
                lbl: sum(1 for kind in aoi_labels.values() for it in kind if it["label"] == lbl)
                for lbl in ("CLICKED", "DEFERRED", "EVALUATED_REJECTED", "NOT_APPROACHED")
            },
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
