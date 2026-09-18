#!/usr/bin/env python3
"""Unit tests for scripts/m5_inference.py.

Stdlib only (no pytest, no numpy) — matches test_viewport_bands_parity.py's
style: plain functions, asserts, print PASS/FAIL per case, exit 1 on any
failure. Run with system python3; nothing here needs the project .venv.

Run:
    python3 scripts/test_m5_inference.py
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import m5_inference as m5  # noqa: E402
from test_viewport_bands_parity import compute_viewport_bands_py  # noqa: E402

FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}  {detail}")
        FAILURES.append(label)


def hand_sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


# ── (a) v2 model reproduces a hand-computed sigmoid ─────────────────────
def test_v2_hand_sigmoid() -> None:
    clf = m5.M5Classifier(model_path=m5.MODEL_JSON)
    # Feature values pinned to the model's own scaler means -> every
    # standardized term is exactly 0 -> z == intercept. This is a
    # hand-computable sigmoid independent of the coefficients themselves.
    feats = dict(zip(clf.features, clf.mean))
    expected = hand_sigmoid(clf.intercept)
    got = clf.predict_score(feats)
    check("v2: predict_score at scaler means == sigmoid(intercept)",
          abs(got - expected) < 1e-12, f"expected={expected!r} got={got!r}")

    # A displaced point: bump every feature one scale-unit above its mean ->
    # z == intercept + sum(coef_i), by construction of standardization.
    feats2 = {name: mean + scale for name, mean, scale
              in zip(clf.features, clf.mean, clf.scale)}
    expected2 = hand_sigmoid(clf.intercept + sum(clf.coef))
    got2 = clf.predict_score(feats2)
    check("v2: predict_score one scale-unit above mean matches hand sigmoid",
          abs(got2 - expected2) < 1e-12, f"expected={expected2!r} got={got2!r}")

    # predict_proba is still the same function (back-compat alias).
    check("v2: predict_proba aliases predict_score",
          clf.predict_proba is clf.predict_score or clf.predict_proba(feats) == got)

    # A v2-only model has no operating_points / calibration block.
    check("v2: operating_points() is None on a v2-only model",
          clf.operating_points() is None)
    check("v2: calibration() is None on a v2-only model",
          clf.calibration() is None)


# ── (b) stub v3-schema model: bands wired in, missing-feature KeyError ──
def _stub_v3_model() -> dict:
    features = [
        "min_dist", "mean_dist", "dwell_in_proximity_ms",
        "mean_approach_velocity", "max_approach_velocity",
        "direction_changes", "frac_decreasing",
        "vt_top", "vt_mid", "vt_bot",
    ]
    n = len(features)
    return {
        "features": features,
        "scaler_mean": [10.0 * (i + 1) for i in range(n)],
        "scaler_scale": [2.0 for _ in range(n)],
        "coefficients_raw": [0.1 * (i + 1) for i in range(n)],
        "intercept": -0.3,
        "operating_threshold": 0.5,
        "operating_threshold_method": "Youden-J on LOSO out-of-fold predictions",
        "loso_auc": 0.789,
        "operating_points": [
            {"threshold": 0.5, "predicted_deferred_share": 0.6,
             "deferred_precision": 0.80, "deferred_recall": 0.75,
             "rejected_precision": 0.55, "rejected_recall": 0.60},
            {"threshold": 0.62, "predicted_deferred_share": 0.4,
             "deferred_precision": 0.85, "deferred_recall": 0.60,
             "rejected_precision": 0.65, "rejected_recall": 0.75},
        ],
        "calibration": {"bins": [], "brier": 0.19, "max_abs_gap": 0.05,
                         "verdict": "stub — not a real fit"},
    }


def test_v3_stub_model() -> None:
    model = _stub_v3_model()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m5_v3_stub.json"
        p.write_text(json.dumps(model))
        clf = m5.M5Classifier(model_path=p)

        check("v3 stub: features list carries seven cursor + three band names",
              clf.features == model["features"])

        cursor_feats = {
            "min_dist": 10.0, "mean_dist": 20.0, "dwell_in_proximity_ms": 30.0,
            "mean_approach_velocity": 40.0, "max_approach_velocity": 50.0,
            "direction_changes": 60.0, "frac_decreasing": 70.0,
        }
        bands = {"vt_top": 80.0, "vt_mid": 90.0, "vt_bot": 100.0, "vp_any": 999.0}
        vec = m5.build_feature_vector(cursor_feats, bands=bands)
        check("v3 stub: build_feature_vector drops vp_any (not a model feature)",
              "vp_any" not in vec)

        # z at these exact values (scaler_mean[i] = 10*(i+1), matching the
        # feature values above component-for-component) -> every
        # standardized term is 0 -> z == intercept, another hand sigmoid.
        expected = hand_sigmoid(model["intercept"])
        got = clf.predict_score(vec)
        check("v3 stub: predict_score uses the band features (hand sigmoid at means)",
              abs(got - expected) < 1e-12, f"expected={expected!r} got={got!r}")

        # Missing a band feature -> KeyError naming it.
        vec_missing = dict(vec)
        del vec_missing["vt_top"]
        try:
            clf.predict_score(vec_missing)
            check("v3 stub: missing vt_top raises KeyError", False, "no exception raised")
        except KeyError as e:
            check("v3 stub: missing vt_top raises KeyError naming the feature",
                  "vt_top" in str(e), f"exception was: {e!r}")

        check("v3 stub: operating_points() returns the block verbatim",
              clf.operating_points() == model["operating_points"])
        check("v3 stub: calibration() returns the block verbatim",
              clf.calibration() == model["calibration"])

        # predict_label still resolves at the model's own operating_threshold.
        label_hi = clf.predict_label(vec, threshold=-100.0)
        label_lo = clf.predict_label(vec, threshold=100.0)
        check("v3 stub: predict_label respects an explicit threshold override",
              label_hi == "DEFERRED" and label_lo == "EVALUATED_REJECTED",
              f"label_hi={label_hi!r} label_lo={label_lo!r}")


# ── (c) extract_viewport_bands agrees with compute_viewport_bands_py ────
def test_extract_viewport_bands_parity() -> None:
    # Tiny synthetic trial: 900px viewport (thirds at 300/600), one AOI
    # whose centre starts in the top third, then a scroll drags it into
    # the bottom third for the second half of the window.
    scr_h = 900.0
    aoi = {"position": 0, "page_top": 100.0, "page_bot": 200.0}  # centre y=150
    timeline = [
        {"t": 0.0, "scrollY": 0.0},        # centre-in-viewport y = 150 -> top third [0,300)
        {"t": 1000.0, "scrollY": 700.0},   # centre-in-viewport y = 150-700=-550 -> off-screen (not intersecting): AOI [100,200] vs viewport [700,1600] don't overlap
        {"t": 2000.0, "scrollY": 2000.0},  # closing boundary, holds prior scrollY for the last interval
    ]
    # Reference computation (imported straight from the parity test module —
    # this IS the ground truth extract_viewport_bands wraps, not a
    # reimplementation).
    ref = compute_viewport_bands_py(timeline, [aoi], scr_h)[0]
    got = m5.extract_viewport_bands(timeline, aoi, scr_h)

    check("bands: vt_top matches compute_viewport_bands_py exactly",
          got["vt_top"] == ref["top_ms"], f"got={got['vt_top']} ref={ref['top_ms']}")
    check("bands: vt_mid matches compute_viewport_bands_py exactly",
          got["vt_mid"] == ref["mid_ms"], f"got={got['vt_mid']} ref={ref['mid_ms']}")
    check("bands: vt_bot matches compute_viewport_bands_py exactly",
          got["vt_bot"] == ref["bot_ms"], f"got={got['vt_bot']} ref={ref['bot_ms']}")
    check("bands: vp_any matches compute_viewport_bands_py exactly",
          got["vp_any"] == ref["any_ms"], f"got={got['vp_any']} ref={ref['any_ms']}")

    # Sanity: the first 1000ms interval has the AOI's centre in-viewport at
    # y=150 (top third of a 900px viewport), so top_ms should be exactly
    # 1000 and mid/bot should be 0 for that interval. The AOI never
    # intersects the viewport again (scrollY 700 puts [700,1600] against
    # AOI [100,200] -- no overlap), so totals should equal exactly 1000.
    check("bands: sanity — top_ms is exactly the first 1000ms interval",
          got["vt_top"] == 1000.0, f"vt_top={got['vt_top']}")
    check("bands: sanity — vp_any equals vt_top (AOI never in mid/bot)",
          got["vp_any"] == got["vt_top"] and got["vt_mid"] == 0.0 and got["vt_bot"] == 0.0)


def main() -> int:
    print("m5_inference unit tests")
    print("\n-- (a) v2 hand-computed sigmoid --")
    test_v2_hand_sigmoid()
    print("\n-- (b) v3-schema stub model --")
    test_v3_stub_model()
    print("\n-- (c) extract_viewport_bands parity --")
    test_extract_viewport_bands_parity()

    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
