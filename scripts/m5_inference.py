"""M5 inference: cursor-only DEFERRED-vs-EVALUATED_REJECTED classifier.

Loads coefficients from a pre-trained logistic regression (trained in
attentional-foraging/scripts/m5_cursor_only_taxonomy.py against NB22's
gaze-derived labels) and applies them to cursor + AOI inputs to predict
the four-class taxonomy without using gaze at runtime.

The feature extractor mirrors compute_features_py in
scripts/test_feature_tracker_parity.py (and ResultProximityTracker in
src/approach-retreat.js — both parity-tested against the upstream M4
extractor in attentional-foraging).

Public API:
    classifier = M5Classifier()
    feats = extract_m5_features(cursor_samples, aoi_y_center)
    proba = classifier.predict_proba(feats)
    label = classifier.predict_label(feats)  # "DEFERRED" or "EVALUATED_REJECTED"
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MODEL_JSON = Path(__file__).resolve().parent / "models/m5_final_model.json"
PROX_THRESHOLD = 100  # px — same as M4/M5 paper convention


def extract_m5_features(cursor: list[dict], aoi_y_center: float, prox_threshold: int = PROX_THRESHOLD) -> dict | None:
    """Compute the M4 nine-feature approach vector for one cursor stream
    against one AOI center. Returns None if too few samples or never
    approached (min_dist >= prox_threshold).

    cursor: list of {"t": ms, "x": int, "y": int, "event": str} samples,
            time-ordered. Only samples are used; no event filtering here.
    aoi_y_center: y in document space (page coords; matches cursor.y).
    """
    if len(cursor) < 2:
        return None

    ts = [s["t"] for s in cursor]
    ys = [s["y"] for s in cursor]
    dists = [abs(y - aoi_y_center) for y in ys]

    min_dist = min(dists)
    if min_dist >= prox_threshold:
        # Cursor never came within proximity — AOI not "approached" by M5's definition
        return None

    n = len(dists)
    mean_dist = sum(dists) / n
    final_dist = dists[-1]
    min_idx = dists.index(min_dist)
    retreat_dist = dists[-1] - dists[min_idx]

    # Dwell within proximity (skip gaps > 2s)
    dwell_ms = 0.0
    for i in range(1, n):
        if dists[i] < prox_threshold:
            dt = ts[i] - ts[i - 1]
            if 0 < dt < 2000:
                dwell_ms += dt

    # Velocities (negative diff of distance / dt, scaled to per-second)
    vels = []
    for i in range(1, n):
        dt = ts[i] - ts[i - 1] or 1
        vels.append(-(dists[i] - dists[i - 1]) / dt * 1000.0)
    if not vels:
        return None
    mean_vel = sum(vels) / len(vels)
    max_vel = max(vels)

    # Direction changes: sign flips of velocity
    direction_changes = 0
    for i in range(1, len(vels)):
        s0 = (vels[i - 1] > 0) - (vels[i - 1] < 0)
        s1 = (vels[i] > 0) - (vels[i] < 0)
        if s0 != s1 and (s0 != 0 and s1 != 0):
            direction_changes += 1

    # Frac decreasing: fraction of distance-diffs that are negative (closer)
    diffs = [dists[i] - dists[i - 1] for i in range(1, n)]
    n_decreasing = sum(1 for d in diffs if d < 0)
    frac_decreasing = n_decreasing / len(diffs) if diffs else 0.0

    return {
        "min_dist": min_dist,
        "mean_dist": mean_dist,
        "final_dist": final_dist,
        "retreat_dist": retreat_dist,
        "dwell_in_proximity_ms": dwell_ms,
        "mean_approach_velocity": mean_vel,
        "max_approach_velocity": max_vel,
        "direction_changes": float(direction_changes),
        "frac_decreasing": frac_decreasing,
    }


class M5Classifier:
    def __init__(self, model_path: Path = MODEL_JSON):
        self.model = json.loads(model_path.read_text())
        self.features = self.model["features"]
        self.mean = self.model["scaler_mean"]
        self.scale = self.model["scaler_scale"]
        self.coef = self.model["coefficients_raw"]
        self.intercept = self.model["intercept"]
        self.threshold = self.model["operating_threshold"]
        self.loso_auc = self.model["loso_auc"]

    def predict_proba(self, feats: dict) -> float:
        """Return P(deferred | cursor features). Caller handles `feats is None`."""
        z = self.intercept
        for i, name in enumerate(self.features):
            v = feats[name]
            standardized = (v - self.mean[i]) / self.scale[i] if self.scale[i] else 0.0
            z += self.coef[i] * standardized
        # Logistic
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        e = math.exp(z)
        return e / (1.0 + e)

    def predict_label(self, feats: dict) -> str:
        return "DEFERRED" if self.predict_proba(feats) >= self.threshold else "EVALUATED_REJECTED"


def aoi_y_center(bbox: dict) -> float:
    return bbox["location"]["y"] + bbox["size"]["height"] / 2.0
