#!/usr/bin/env python3
"""Parity test (Python side) for computeViewportBandsPure.

Lifted from the inner loop of viewport_ms_for_trial in
attentional-foraging/scripts/viewport_time_calibration.py. Reads the
trajectory fixture written by test_viewport_bands_parity.js, computes
per-position {any_ms, top_ms, mid_ms, bot_ms} totals using the canonical
piecewise-constant Python logic, and writes the result to
fixtures/py_viewport_bands.json. Compares to the JS output if present and
asserts field-wise match to 1e-6.

Run AFTER the JS script:
    python3 scripts/test_viewport_bands_parity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
TRAJECTORY = FIXTURES / "viewport_bands_trajectory.json"
JS_BANDS = FIXTURES / "js_viewport_bands.json"
PY_BANDS = FIXTURES / "py_viewport_bands.json"

TOL = 1e-6


def compute_viewport_bands_py(timeline, aois, scr_h):
    """Canonical reference — exactly mirrors viewport_ms_for_trial's inner loop."""
    third = scr_h / 3.0
    out = [
        {"position": a["position"], "any_ms": 0.0,
         "top_ms": 0.0, "mid_ms": 0.0, "bot_ms": 0.0}
        for a in aois
    ]
    for i in range(len(timeline) - 1):
        t0 = timeline[i]["t"]
        t1 = timeline[i + 1]["t"]
        dt = t1 - t0
        if dt <= 0:
            continue
        y0 = timeline[i]["scrollY"]
        vp_top, vp_bot = y0, y0 + scr_h
        for j, a in enumerate(aois):
            a_top, a_bot = a["page_top"], a["page_bot"]
            if min(a_bot, vp_bot) <= max(a_top, vp_top):
                continue  # not intersecting
            out[j]["any_ms"] += dt
            center_vp_y = (a_top + a_bot) / 2.0 - y0
            if 0 <= center_vp_y < third:
                out[j]["top_ms"] += dt
            elif third <= center_vp_y < 2 * third:
                out[j]["mid_ms"] += dt
            elif 2 * third <= center_vp_y <= scr_h:
                out[j]["bot_ms"] += dt
    out.sort(key=lambda r: r["position"])
    return out


def main():
    if not TRAJECTORY.exists():
        print(f"error: {TRAJECTORY} not found. Run the JS script first.",
              file=sys.stderr)
        sys.exit(1)

    traj = json.load(open(TRAJECTORY))
    scr_h = traj["scr_h"]
    events = traj["scroll_events"]
    aois = traj["aois"]
    print(f"trajectory: {len(events)} scroll events, {len(aois)} AOIs, scr_h={scr_h}")

    py_bands = compute_viewport_bands_py(events, aois, scr_h)

    print("\n── Python reference ──")
    print(f"{'pos':<4} {'any_ms':>8} {'top_ms':>8} {'mid_ms':>8} {'bot_ms':>8}")
    for r in py_bands:
        print(f"{r['position']:<4} {r['any_ms']:>8.0f} {r['top_ms']:>8.0f} "
              f"{r['mid_ms']:>8.0f} {r['bot_ms']:>8.0f}")

    with open(PY_BANDS, "w") as f:
        json.dump(py_bands, f, indent=2)
    print(f"\nwrote {PY_BANDS}")

    if not JS_BANDS.exists():
        print(f"\n(skipping JS diff: {JS_BANDS} not present — run JS script first)")
        return

    js_bands = json.load(open(JS_BANDS))
    print("\n── JS ↔ Python parity check ──")
    if len(js_bands) != len(py_bands):
        print(f"FAIL: length mismatch — JS {len(js_bands)}, PY {len(py_bands)}")
        sys.exit(1)

    fail = False
    for j, p in zip(js_bands, py_bands):
        if j["position"] != p["position"]:
            print(f"FAIL: position mismatch {j['position']} vs {p['position']}")
            fail = True
            continue
        for f in ("any_ms", "top_ms", "mid_ms", "bot_ms"):
            d = abs(float(j[f]) - float(p[f]))
            mark = "ok" if d < TOL else "FAIL"
            print(f"  pos {p['position']}  {f:<7}  "
                  f"JS={j[f]:>8}  PY={p[f]:>8}  Δ={d:.2e}  {mark}")
            if d >= TOL:
                fail = True

    if fail:
        print("\nPARITY TEST FAILED")
        sys.exit(1)
    print(f"\nAll fields match within {TOL}.")


if __name__ == "__main__":
    main()
