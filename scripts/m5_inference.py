"""M5 inference: cursor-only DEFERRED-vs-EVALUATED_REJECTED classifier.

Loads coefficients from a pre-trained logistic regression (trained in
attentional-foraging/scripts/export_m5_cursor_only.py against NB22's
gaze-derived labels) and applies them to cursor + AOI inputs to predict
the four-class taxonomy without using gaze at runtime.

Model change, 2026-09-18. The default model is now
models/m5_cursor_only_v2.json: seven features (no final_dist / retreat_dist),
trained on the cursor-only typed stream (press-anchored buf500, native
mousemove sampling, 9,932 approached non-click rows), LOSO AUC 0.691,
Youden-J threshold 0.477. The previous default, models/m5_final_model.json
(2026-05-02, nine features, LOSO 0.769), is kept in place and copied to
models/m5_final_model.legacy-2026-05-02.json; its features were computed on
fixation-selected rows with gaze-to-cursor distances and fixation-weighted
dwell, so they carried part of the gaze-return label and were not the
measurement this module computes at runtime (see attentional-foraging/
docs/ablations/deferred_drop_decomposition.md). The extractor still returns
all nine values for other consumers; the classifier feeds the model only the
features its JSON `features` list names, in that order.

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

MODEL_JSON = Path(__file__).resolve().parent / "models/m5_cursor_only_v2.json"
# Retired 2026-09-18; nine features on the fixation-selected LAB stream. Load explicitly
# via M5Classifier(model_path=LEGACY_MODEL_JSON) if the old scores are ever needed.
LEGACY_MODEL_JSON = Path(__file__).resolve().parent / "models/m5_final_model.legacy-2026-05-02.json"
PROX_THRESHOLD = 100  # px — same as M4/M5 paper convention
MIN_VEL_DT_MS = 8  # tracker floors dt for the velocity divide only (~125 Hz ceiling)
MAX_PLAUSIBLE_VEL = 5000  # px/s; tracker's symmetric clamp


def extract_m5_features(cursor: list[dict], aoi_y_center: float, prox_threshold: int = PROX_THRESHOLD) -> dict | None:
    """Compute the M4 nine-feature approach vector for one cursor stream
    against one AOI center. Returns None if too few samples or never
    approached (min_dist >= prox_threshold).

    All nine values are returned for callers that want them; the v2 model
    consumes only the seven named in its `features` list (final_dist and
    retreat_dist are excluded by the click-buffer screen, CIKM section 3.4).

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

    # Mirror ResultFeatureTracker.update() in src/approach-retreat.js sample
    # for sample, because the v2 model was trained on that tracker's output
    # (attentional-foraging m4_cursor_aoi_rerun.py drives it over a bridge).
    # Rules that matter: a sample with dt <= 0 updates min/final only; the
    # velocity divide floors dt at MIN_VEL_DT_MS and clamps the magnitude at
    # MAX_PLAUSIBLE_VEL (symmetric, sign preserved); direction_changes counts
    # every sign transition including through zero (np.diff(np.sign(v)) != 0);
    # frac_decreasing and mean velocity are over dt > 0 transitions only.
    n = 1
    sum_dist = dists[0]
    final_dist_prev = dists[0]
    last_t = ts[0]
    dwell_ms = 0.0
    sum_vel = 0.0
    max_vel = -math.inf
    n_trans = 0
    n_decreasing = 0
    direction_changes = 0
    last_sign = None
    for i in range(1, len(dists)):
        dist, t = dists[i], ts[i]
        dt = t - last_t
        if dt <= 0:
            final_dist_prev = dist
            continue
        dt_vel = max(dt, MIN_VEL_DT_MS)
        raw_vel = -(dist - final_dist_prev) / dt_vel * 1000.0
        vel = max(-MAX_PLAUSIBLE_VEL, min(MAX_PLAUSIBLE_VEL, raw_vel))
        n_trans += 1
        sum_vel += vel
        if vel > max_vel:
            max_vel = vel
        if dist < final_dist_prev:
            n_decreasing += 1
        sign = 1 if vel > 0 else (-1 if vel < 0 else 0)
        if last_sign is not None and sign != last_sign:
            direction_changes += 1
        last_sign = sign
        if dist < prox_threshold and dt < 2000:
            dwell_ms += dt
        n += 1
        sum_dist += dist
        final_dist_prev = dist
        last_t = t

    if n_trans == 0:
        return None
    mean_dist = sum_dist / n
    final_dist = dists[-1]
    retreat_dist = final_dist - min_dist
    mean_vel = sum_vel / n_trans
    frac_decreasing = n_decreasing / n_trans

    return {
        "min_dist": min_dist,
        "mean_dist": mean_dist,
        "final_dist": final_dist,
        "retreat_dist": retreat_dist,
        "dwell_in_proximity_ms": dwell_ms,
        "mean_approach_velocity": mean_vel,
        "max_approach_velocity": max_vel if max_vel != -math.inf else 0.0,
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
        if not (len(self.features) == len(self.mean) == len(self.scale) == len(self.coef)):
            raise ValueError(f"{model_path}: features/scaler/coefficient lengths disagree")

    def predict_proba(self, feats: dict) -> float:
        """Return P(deferred | cursor features). Caller handles `feats is None`.

        Only the features the model JSON names are read, in the model's order;
        extra keys in `feats` (final_dist, retreat_dist) are ignored.
        """
        z = self.intercept
        for i, name in enumerate(self.features):
            v = feats[name]
            if not math.isfinite(v):
                raise ValueError(f"non-finite feature {name}={v!r}")
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
