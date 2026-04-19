#!/usr/bin/env python3
"""Parity test for JS `computeViewportAnalyticsPure` against the reference
logic in attentional-foraging/scripts/nb30_scroll_trajectory.py's
`compute_features_for_trial`.

Reads fixtures/viewport_analytics_trajectory.json (written by the JS script),
computes the analytics using the reference algorithm (inlined here so the
test is self-contained), and writes fixtures/py_viewport_analytics.json.
Then compares against fixtures/js_viewport_analytics.json. Every field must
match within 1e-6.

Run:
    node scripts/test_viewport_analytics_parity.js
    python3 scripts/test_viewport_analytics_parity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "fixtures"


def compute_reference(scroll_events, aois, scr_h, center_tol_px,
                      iab_viewable_threshold_ms=1000):
    """Inlined reference for computeViewportAnalyticsPure (including the
    IAB/MRC Viewable Impression fields). Piecewise-constant attribution:
    interval [timeline[i], timeline[i+1]) uses scrollY at timeline[i]."""
    center_y = scr_h / 2.0
    accum = []
    for a in aois:
        accum.append({
            "position": a["position"],
            "any_ms": 0.0, "center_ms": 0.0, "sum_center_y_ms": 0.0,
            "max_overlap_frac": 0.0,
            "min_abs_v": float("inf"),
            "n_reversals": 0, "last_v_sign": 0,
            "ms_at_50pct_or_more": 0.0,
            "current_50pct_stretch_ms": 0.0,
            "iab_viewable": False,
        })
    for i in range(len(scroll_events) - 1):
        dt = scroll_events[i + 1]["t"] - scroll_events[i]["t"]
        if dt <= 0:
            continue
        dt_s = dt / 1000.0
        scroll_y = scroll_events[i]["scrollY"]
        v = (scroll_events[i + 1]["scrollY"] - scroll_y) / dt_s if dt_s > 0 else 0.0
        abs_v = abs(v)
        sign = 0 if abs_v < 1e-6 else (1 if v > 0 else -1)
        for j, a in enumerate(aois):
            vp_top = scroll_y
            vp_bot = scroll_y + scr_h
            overlap = min(a["page_bot"], vp_bot) - max(a["page_top"], vp_top)
            r = accum[j]
            if overlap <= 0:
                r["current_50pct_stretch_ms"] = 0.0
                continue
            center_vp_y = (a["page_top"] + a["page_bot"]) / 2.0 - scroll_y
            aoi_h = a["page_bot"] - a["page_top"]
            overlap_frac = overlap / aoi_h if aoi_h > 0 else 0
            r["any_ms"] += dt
            r["sum_center_y_ms"] += center_vp_y * dt
            if overlap_frac > r["max_overlap_frac"]:
                r["max_overlap_frac"] = overlap_frac
            if abs(center_vp_y - center_y) <= center_tol_px:
                r["center_ms"] += dt
            if abs_v < r["min_abs_v"]:
                r["min_abs_v"] = abs_v
            if r["last_v_sign"] != 0 and sign != 0 and sign != r["last_v_sign"]:
                r["n_reversals"] += 1
            if sign != 0:
                r["last_v_sign"] = sign
            # IAB / MRC: ≥ 50 % pixel overlap sustained ≥ threshold_ms continuously
            if overlap_frac >= 0.5:
                r["ms_at_50pct_or_more"] += dt
                r["current_50pct_stretch_ms"] += dt
                if r["current_50pct_stretch_ms"] >= iab_viewable_threshold_ms:
                    r["iab_viewable"] = True
            else:
                r["current_50pct_stretch_ms"] = 0.0
    out = []
    for r in accum:
        avg_vp_y = r["sum_center_y_ms"] / r["any_ms"] if r["any_ms"] > 0 else 0.0
        min_abs_v = 0.0 if r["min_abs_v"] == float("inf") else r["min_abs_v"]
        out.append({
            "position": r["position"],
            "vt_any_ms": r["any_ms"],
            "vt_center_ms": r["center_ms"],
            "avg_viewport_y_px": avg_vp_y,
            "max_overlap_frac": r["max_overlap_frac"],
            "min_abs_velocity_px_per_s": min_abs_v,
            "n_reversals": r["n_reversals"],
            "ms_at_50pct_or_more": r["ms_at_50pct_or_more"],
            "iab_viewable": r["iab_viewable"],
        })
    out.sort(key=lambda x: x["position"])
    return out


def main():
    traj_path = FIX / "viewport_analytics_trajectory.json"
    if not traj_path.exists():
        print(f"ERROR: {traj_path} not found. Run the JS script first.")
        sys.exit(1)
    trajectory = json.loads(traj_path.read_text())

    py_out = compute_reference(
        trajectory["scroll_events"],
        trajectory["aois"],
        trajectory["scr_h"],
        trajectory["center_tol_px"],
        trajectory.get("iab_viewable_threshold_ms", 1000),
    )
    (FIX / "py_viewport_analytics.json").write_text(json.dumps(py_out, indent=2))

    js_out = json.loads((FIX / "js_viewport_analytics.json").read_text())

    tol = 1e-6
    fields = ("vt_any_ms", "vt_center_ms", "avg_viewport_y_px",
              "max_overlap_frac", "min_abs_velocity_px_per_s", "n_reversals",
              "ms_at_50pct_or_more", "iab_viewable")
    all_ok = True
    for py, js in zip(py_out, js_out):
        assert py["position"] == js["position"]
        for f in fields:
            d = abs(py[f] - js[f])
            ok = d < tol
            mark = "ok" if ok else "FAIL"
            print(f"  pos {py['position']}  {f:28s}  JS={js[f]!s:>10}  PY={py[f]!s:>10}  Δ={d:.2e}  {mark}")
            if not ok:
                all_ok = False

    if all_ok:
        print(f"\nAll fields match within {tol:.0e}.")
        sys.exit(0)
    else:
        print(f"\nPARITY FAILURE — fields exceed {tol:.0e}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
