#!/usr/bin/env python3
"""Python side of the ResultFeatureTracker parity test.

Reads fixtures/trajectory.json, applies the same nine-feature extraction
logic as attentional-foraging/scripts/m4_nb21_hybrid_rerun.py
(compute_hybrid_features's inner per-result loop, lifted verbatim), and
compares against fixtures/js_features.json.

Exit 0 on match, 1 on mismatch beyond 1e-6 tolerance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"

PROX_THRESHOLD = 100  # same as paper


def compute_features_py(samples, center_pageY, prox_threshold=PROX_THRESHOLD):
    """Mirror of m4_nb21_hybrid_rerun.py's inner feature loop on a single
    (cursor trajectory, result center) pair. Feature-for-feature parity
    with `compute_hybrid_features`."""
    ts_all = np.array([s["t"] for s in samples], dtype=np.float64)
    ys_all = np.array([s["pageY"] for s in samples], dtype=np.float64)
    dist = np.abs(ys_all - center_pageY)

    min_dist = float(dist.min())
    mean_dist = float(dist.mean())
    final_dist = float(dist[-1])
    min_idx = int(np.argmin(dist))
    retreat_dist = float(dist[-1] - dist[min_idx])

    in_prox = dist < prox_threshold
    dwell_ms = 0.0
    for i in range(1, len(ts_all)):
        if in_prox[i]:
            dt = float(ts_all[i] - ts_all[i - 1])
            if 0 < dt < 2000:
                dwell_ms += dt

    dts = np.diff(ts_all).astype(float)
    dts[dts == 0] = 1.0
    vels = -np.diff(dist) / dts * 1000.0
    mean_vel = float(vels.mean())
    max_vel = float(vels.max())
    direction_changes = int(np.sum(np.diff(np.sign(vels)) != 0))
    frac_decreasing = float(np.mean(np.diff(dist) < 0))

    return {
        "min_dist": min_dist,
        "mean_dist": mean_dist,
        "final_dist": final_dist,
        "retreat_dist": retreat_dist,
        "dwell_in_proximity_ms": dwell_ms,
        "mean_approach_velocity": mean_vel,
        "max_approach_velocity": max_vel,
        "direction_changes": direction_changes,
        "frac_decreasing": frac_decreasing,
        "sample_count": len(samples),
    }


def main():
    traj = json.loads((FIX / "trajectory.json").read_text())
    js_features = json.loads((FIX / "js_features.json").read_text())
    py_features = compute_features_py(traj["samples"], traj["center_pageY"])

    (FIX / "py_features.json").write_text(json.dumps(py_features, indent=2))
    print("── Python canonical features ──")
    for k, v in py_features.items():
        js_v = js_features.get(k, "MISSING")
        print(f"  {k:<24}  py={v!r:<22}  js={js_v!r}")

    print("\n── Parity check ──")
    tolerance = 1e-6
    mismatches = []
    for k, py_v in py_features.items():
        js_v = js_features.get(k)
        if js_v is None:
            mismatches.append(f"  MISSING in JS: {k}")
            continue
        if isinstance(py_v, int) and isinstance(js_v, int):
            if py_v != js_v:
                mismatches.append(f"  {k}: py={py_v} js={js_v}")
        else:
            try:
                delta = abs(float(py_v) - float(js_v))
            except (TypeError, ValueError):
                mismatches.append(f"  {k}: py={py_v!r} js={js_v!r}  TYPE MISMATCH")
                continue
            if delta > tolerance:
                mismatches.append(f"  {k}: py={py_v:.9f} js={js_v:.9f} Δ={delta:.2e}")

    if mismatches:
        print("  MISMATCH:")
        for m in mismatches:
            print(m)
        sys.exit(1)
    print(f"  ✓ all features match within {tolerance}")
    sys.exit(0)


if __name__ == "__main__":
    main()
