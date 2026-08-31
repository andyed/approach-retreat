"""Build a per-trial replay bundle for the approach-retreat AdSERP viewer.

For each trial:
- Copy the full-page screenshot into site/replay/data/png/
- Read raw mouse-movement, fixation, pupil CSVs from the AdSERP cache
- Read ad-boundary + organic-boundary JSONs
- Read trial metadata XML for window/document dims
- Scale cursor xpos AND ypos from document space into screenshot/AOI space
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
# Cell-aware AOI snapshot from AF's typed cascade (probe_cellsplit_features.py
# / m4_nb21_hybrid_rerun_cellsplit.py). Provides dd_top_cell / dd_right_cell /
# organic_cell sub-bboxes that the parent dd_top / dd_right entries split into.
# Coverage: 1,708 / 2,776 trials had cells emitted (69% — the rest had no
# horizontal carousel or sub-cell structure to split).
AF_CASCADE_DIR = (Path.home() /
                  "Documents/dev/attentional-foraging/scripts/output/cascade-baseline/aoi-snapshot-v1")
# When the AdSERP screenshot volume isn't mounted, fall back to the local
# cache. The cache covers a subset of trials (~111 of 2,776) but is enough
# for visual verification on the curated replay set.
SCREENSHOT_FALLBACK = AF_ROOT / "full-page-screenshots.local-cache.bak"
AR_ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = AR_ROOT / "site/replay/data"
PNG_OUT = SITE_DATA / "png"
TRIALS_OUT = SITE_DATA / "trials"


def _resolve_screenshot(trial_id: str) -> Path | None:
    primary = AF_ROOT / "full-page-screenshots" / f"{trial_id}.png"
    if primary.exists():
        return primary
    fallback = SCREENSHOT_FALLBACK / f"{trial_id}.png"
    if fallback.exists():
        return fallback
    return None

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


def read_cursor(trial_id: str, t0_ms: int, ratio_x: float,
                ratio_y: float) -> tuple[list[dict], list[dict]]:
    """Return (cursor_samples, xy_delta_samples), cursor mapped into screenshot space.

    evtrack records xpos/ypos in DOCUMENT space (1403 wide). Screenshots, and
    the AOI boxes drawn over them, are SCREENSHOT space (1280 wide). The scale
    is anisotropic -- x 0.9123, y 0.9000 -- so both axes need it and they need
    different factors.

    Previously only x was scaled, and by SCREENSHOT_WIDTH / window_width
    (1280/1422 = 0.9001) rather than document width (1280/1403 = 0.9123). The
    window overhangs the display on Windows, so it is the wrong denominator.
    Net effect: x was off ~1.3% and y was off ~10%, which put every cursor
    sample systematically BELOW the AOI it was nearest (median +8.5px) and
    inflated mean cursor-to-AOI distance from 37.5px to 57.3px.
    """
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
            y = int(round(float(row["ypos"]) * ratio_y))
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

# AF's alignment_suspect quality gate (y-DP geometric card<->bbox alignment).
# Trials on this list have shift-periodic pages where a one-slot-wrong AOI
# lattice cannot be ruled out geometrically; AF excludes them from every
# typed-flavor feature derivation. AR keeps building their bundles (they are
# pedagogically useful and pulling published pages is an editorial call) but
# stamps them `alignment_suspect: true` so the viewer and index can badge
# them. The list applies to BOTH typed and typed_gapfill — the exclusion
# derives from render geometry, not flavor.
_ALIGNMENT_EXCLUSIONS_PATH = (Path.home() / "Documents/dev/attentional-foraging"
                              / "data/aoi-typed/alignment-exclusions.json")
_ALIGNMENT_EXCLUSIONS_CACHE: dict | None = None


def load_alignment_exclusions() -> dict:
    """AF's canonical exclusion list: {'date', 'reason', 'rule', 'tids'}.

    Returns {} when the file is missing (bundle then carries
    alignment_suspect: false, which is the pre-gate behavior)."""
    global _ALIGNMENT_EXCLUSIONS_CACHE
    if _ALIGNMENT_EXCLUSIONS_CACHE is None:
        if _ALIGNMENT_EXCLUSIONS_PATH.exists():
            _ALIGNMENT_EXCLUSIONS_CACHE = json.loads(
                _ALIGNMENT_EXCLUSIONS_PATH.read_text())
        else:
            _ALIGNMENT_EXCLUSIONS_CACHE = {}
    return _ALIGNMENT_EXCLUSIONS_CACHE


# AF publishes its substrate identity (branch, commit, typed-maps content
# hash) beside the exclusion list. Bundles stamp it into _meta so a page can
# be traced to the exact map generation it was rendered from.
_SUBSTRATE_PATH = (Path.home() / "Documents/dev/attentional-foraging"
                   / "data/aoi-typed/substrate.json")
_SUBSTRATE_CACHE: dict | None = None


def load_substrate() -> dict:
    """AF's substrate stamp; {} when AF hasn't published one (pre-2026-08-30)."""
    global _SUBSTRATE_CACHE
    if _SUBSTRATE_CACHE is None:
        if _SUBSTRATE_PATH.exists():
            _SUBSTRATE_CACHE = json.loads(_SUBSTRATE_PATH.read_text())
        else:
            _SUBSTRATE_CACHE = {}
    return _SUBSTRATE_CACHE


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

    Guard rails (2026-08-30, post AllSERP v1.1.0 realignment):
    - A correction entry may carry `expected_bbox: {"<pos>": {"y", "height"}}`.
      When present, the demotion only applies if the organic bbox at that
      position still matches (±4 px). A bare integer position is not a
      stable key across upstream regenerations — a drifted bbox means the
      correction now points at a different result, so it is skipped loudly
      instead of silently demoting the wrong AOI.
    - Renumbered survivors keep their upstream position as
      `source_position`, so the join back to AF's organic-boundary rank
      space stays recoverable from the bundle.
    """
    corrections = _load_aoi_corrections().get(trial_id)
    if not corrections:
        return organic
    demote = set(corrections.get("demote_to_widget", []))
    if not demote:
        return organic
    expected = corrections.get("expected_bbox", {})
    organics = organic.get("organic_result", [])
    kept, moved = [], []
    for r in organics:
        pos = r.get("position")
        if pos in demote:
            exp = expected.get(str(pos))
            if exp is not None:
                got_y = float(r["location"]["y"])
                got_h = float(r["size"]["height"])
                if (abs(got_y - float(exp["y"])) > 4
                        or abs(got_h - float(exp["height"])) > 4):
                    print(f"  WARN {trial_id}: aoi_correction demote_to_widget"
                          f"[{pos}] bbox drifted (expected y={exp['y']} "
                          f"h={exp['height']}, got y={got_y} h={got_h}) — "
                          f"correction skipped, re-adjudicate against the "
                          f"current upstream maps", file=sys.stderr)
                    kept.append(r)
                    continue
            moved.append({**r, "reason": "manual_correction"})
        else:
            kept.append(r)
    for i, r in enumerate(kept, 1):
        if r.get("position") != i:
            r["source_position"] = r.get("position")
        r["position"] = i
    organic["organic_result"] = kept
    organic["widget"] = list(organic.get("widget", [])) + moved
    return organic


# Main-axis membership for typed AOI cards (phase-07 join fix, 2026-08-30).
#
# The old gate was `card['position'] >= 0` — a positional test on the exact
# field the y-DP realignment renumbers, so a card that shifted a slot was
# silently added to or dropped from the widget overlay. The stable key the
# maps already carry is `html_handle` (e.g. 'rso[2]', 'Odp5De[0]',
# 'botstuff.nav[0]', '#rhs[0]'): the DOM container namespace survives
# re-ranking. Namespace census over all 2,776 typed_gapfill maps
# (2026-08-30): rso / Odp5De are main-column, botstuff.* / #rhs are
# off-axis; chrome / native_ad / dd_top / dd_right / some unknown_widget
# carry no handle and fall back to the positional test.
_MAIN_AXIS_HANDLE_ROOTS = {"rso", "Odp5De"}
_OFF_AXIS_HANDLE_ROOTS = {"botstuff", "#rhs", "chrome"}


def _on_main_axis(card: dict) -> bool:
    """True when a typed AOI card sits in the main scroll column.

    Keyed on the html_handle namespace when the card has one; falls back
    to the sign of `position` only for handle-less cards. An unrecognized
    handle namespace also falls back rather than guessing."""
    handle = card.get("html_handle") or ""
    if handle:
        root = handle.split("[", 1)[0].split(".", 1)[0]
        if root in _OFF_AXIS_HANDLE_ROOTS:
            return False
        if root in _MAIN_AXIS_HANDLE_ROOTS:
            return True
    return card.get("position", -1) >= 0


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


def _load_cell_subbboxes(trial_id: str) -> dict:
    """Pull enriched cell sub-bboxes from AF's cell-aware cascade snapshot.

    Returns a dict with any of dd_top_cell / dd_right_cell / organic_cell
    that are non-empty for this trial. Returns {} when the snapshot file
    is missing or carries no cells (typical for SERPs without horizontal
    carousels — about 31% of trials in the 2,776-trial AdSERP corpus).

    Schema mirrors organic-boundary-data entries: each cell has
    `position`, `location.{x,y}`, `size.{width,height}`. The viewer
    template (site/replay/template.html) renders these via AOI_STYLE
    entries keyed by kind (dd_top_cell / dd_right_cell), inheriting
    the parent's color at a slightly higher fill opacity.
    """
    snap_path = AF_CASCADE_DIR / f"{trial_id}.json"
    if not snap_path.exists():
        return {}
    snap = json.loads(snap_path.read_text())
    return {
        kind: snap[kind]
        for kind in ("dd_top_cell", "dd_right_cell", "organic_cell")
        if snap.get(kind)
    }


def build_trial(trial_id: str, flavor: str = "typed_gapfill") -> dict | None:
    """Build a per-trial replay JSON.

    flavor (post-2026-05-05 cascade):
      - 'typed_gapfill' (default) — reads from organic-boundary-data-gapfill/
        and aoi-typed-gapfill/. The midpoint-split AOI bboxes match the
        ones used by `attribute_click_to_typed_gapfill` upstream, so the
        replay's overlay rectangles align with the click/fixation
        attribution that downstream analyses use.
      - 'typed' — legacy tight bboxes from organic-boundary-data/ and
        aoi-typed/. Retained for cascade audits.
    """
    png = _resolve_screenshot(trial_id)
    ad_json = AF_ROOT / "ad-boundary-data" / f"{trial_id}.json"

    if flavor == "typed_gapfill":
        organic_dir = "organic-boundary-data-gapfill"
        aoi_typed_dir = "data/aoi-typed-gapfill"
    elif flavor == "typed":
        organic_dir = "organic-boundary-data"
        aoi_typed_dir = "data/aoi-typed"
    else:
        raise ValueError(f"unknown flavor: {flavor!r}")
    organic_json = AF_ROOT / organic_dir / f"{trial_id}.json"

    if png is None:
        print(f"  SKIP {trial_id}: screenshot missing", file=sys.stderr)
        return None
    if not ad_json.exists() or not organic_json.exists():
        print(f"  SKIP {trial_id}: bbox JSONs missing", file=sys.stderr)
        return None

    meta = parse_metadata(trial_id)
    t0 = trial_t0(trial_id)
    # Derive both ratios from the shipped artifacts rather than hardcoding, so a
    # trial captured differently carries its own factors and the wrong
    # denominator (window vs document) becomes inexpressible.
    shot_w, shot_h = Image.open(png).size
    ratio_x = shot_w / meta["doc_width"]
    ratio_y = shot_h / meta["doc_height"]

    cursor, xy_delta = read_cursor(trial_id, t0, ratio_x, ratio_y)
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
                      / aoi_typed_dir / f"{trial_id}.json")
    if typed_aoi_path.exists():
        widget_bboxes = []
        typed_cards = json.loads(typed_aoi_path.read_text())
        widget_types = {"image_pack", "knowledge_panel", "paa", "top_places",
                        "related_searches", "other_widget", "unknown_widget"}
        for c in typed_cards:
            if not _on_main_axis(c):
                continue  # off-axis (chrome / dd_right / botstuff.* / #rhs)
            if c.get("type") not in widget_types:
                continue
            if c.get("x") is None or c.get("y") is None:
                continue  # unplaced card (e.g. demoted phantom knowledge_panel)
            widget_bboxes.append({
                "location": {"x": float(c["x"]), "y": float(c["y"])},
                "size": {"width": float(c["width"]), "height": float(c["height"])},
                "type": c["type"],
                "html_handle": c.get("html_handle"),
            })

        # Pagination + related_searches estimated overlays. Bounds are
        # carved so they don't overlap each other:
        #   pagination: y = jpg_h - 220, h = 140 (covers Goooooogle row)
        #   related_searches: from last_main_card_bottom + 30 to pagination - 10
        # Type-specific labels (PG / RS) keep them distinguishable in the
        # viewer template (TAG_PREFIX / WIDGET_TAG).
        pagination_cards = [c for c in typed_cards if c.get('type') == 'pagination']
        related_searches_cards = [c for c in typed_cards if c.get('type') == 'related_searches']

        jpg_h = None
        if jpg_out.exists():
            try:
                jpg_h = Image.open(jpg_out).height
            except Exception:
                jpg_h = None

        # Deepest main-axis card bottom
        last_card_bottom = 0.0
        for c in typed_cards:
            if (c.get('position', -1) >= 0 and c.get('y') is not None
                    and c.get('height') is not None):
                last_card_bottom = max(last_card_bottom,
                                        float(c['y']) + float(c['height']))

        pag_y = None
        pag_h = 140.0  # tall enough to cover Goooooogle + page-numbers row
        if pagination_cards and jpg_h:
            pag_y = max(0.0, float(jpg_h) - 220.0)

        # related_searches: between last main-axis card and pagination top
        if (related_searches_cards and last_card_bottom > 0 and pag_y is not None):
            rs_y = last_card_bottom + 30.0
            rs_h = pag_y - rs_y - 10.0  # 10 px gap above pagination box
            if rs_h >= 60.0:
                widget_bboxes.append({
                    "location": {"x": 162.0, "y": rs_y},
                    "size": {"width": 586.0, "height": rs_h},
                    "type": "related_searches",
                    "html_handle": related_searches_cards[0].get("html_handle"),
                    "estimated": True,
                })

        if pag_y is not None:
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
    # Augment with cell-aware sub-bboxes from AF's cellsplit cascade.
    # Cells inherit the parent's color in the viewer template but render
    # their own four-class heuristic label per cell (M5 stays organic-only).
    cells = _load_cell_subbboxes(trial_id)
    bboxes.update(cells)
    aoi_labels = derive_aoi_labels(cursor, bboxes)

    exclusions = load_alignment_exclusions()
    alignment_suspect = trial_id in set(exclusions.get("tids", []))
    if alignment_suspect:
        print(f"  NOTE {trial_id}: on AF's alignment_suspect exclusion list "
              f"({exclusions.get('date')}) — bundle flagged", file=sys.stderr)

    return {
        "trial_id": trial_id,
        "alignment_suspect": alignment_suspect,
        "screenshot": f"png/{jpg_name}",
        "screenshot_width": SCREENSHOT_WIDTH,
        "doc_height": meta["doc_height"],
        "win_width": meta["win_width"],
        "ratio_x": round(ratio_x, 4),
        "ratio_y": round(ratio_y, 4),
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
            "flavor": flavor,
            "substrate": {
                k: load_substrate().get(k)
                for k in ("branch", "substrate_commit", "typed_maps_content_hash")
            } if load_substrate() else None,
            "alignment_exclusion": {
                "listed": alignment_suspect,
                "list_date": exclusions.get("date"),
                "reason": exclusions.get("reason") if alignment_suspect else None,
            },
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
    import argparse
    parser = argparse.ArgumentParser(description=(__doc__ or "build replay JSON"))
    parser.add_argument("trials", nargs="+", help="Trial IDs, e.g. p005-b2-t2")
    parser.add_argument(
        "--flavor", default="typed_gapfill",
        choices=["typed_gapfill", "typed"],
        help="AOI source flavor (default typed_gapfill — midpoint-split bboxes "
             "matching attribute_click_to_typed_gapfill).",
    )
    args = parser.parse_args()
    TRIALS_OUT.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    for tid in args.trials:
        bundle = build_trial(tid, flavor=args.flavor)
        if bundle is None:
            continue
        out = TRIALS_OUT / f"{tid}.json"
        out.write_text(json.dumps(bundle))
        m = bundle["_meta"]
        print(f"  {tid}: {m['n_cursor']} cursor, {m['n_fixations']} fix, {m['n_pupil']} pupil — {bundle['duration_ms']}ms")
        n_ok += 1
    print(f"\nWrote {n_ok}/{len(args.trials)} → {TRIALS_OUT} (flavor={args.flavor})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
