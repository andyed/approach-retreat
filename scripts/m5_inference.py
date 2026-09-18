"""M5 inference: cursor-only DEFERRED-vs-EVALUATED_REJECTED classifier.

Loads coefficients from a pre-trained logistic regression (trained in
attentional-foraging/scripts/export_m5_cursor_only.py against NB22's
gaze-derived labels) and applies them to cursor + AOI inputs to predict
the four-class taxonomy without using gaze at runtime.

Decision, 2026-09-19 (docs/CURATION.md): the cursor-only deferred classifier
cannot cleanly separate DEFERRED from EVALUATED_REJECTED — at v2's own
Youden threshold a REJECTED call is right 48.5% of the time (TPR 0.7276,
FPR 0.4425 on 6,800 deferred / 3,132 rejected). So **M5 emits a score, not
a label**: `predict_score` is the primary output, `predict_label` is a
one-threshold convenience kept for callers that need a hard call. Hard
four-class labels for the replay viewer now come from the bbox-episode
heuristic (observed cursor re-entry), not from this module.

Model change, 2026-09-18. The default model is models/m5_cursor_only_v2.json
unless models/m5_v3_cursor_bands.json exists, in which case that becomes the
default automatically (see DEFAULT_MODEL below) — v2 is seven features (no
final_dist / retreat_dist), trained on the cursor-only typed stream
(press-anchored buf500, native mousemove sampling, 9,932 approached
non-click rows), LOSO AUC 0.691, Youden-J threshold 0.477. v3 adds three
viewport-band features (vt_top, vt_mid, vt_bot — ms the AOI's centre spent
in the top/middle/bottom third of the viewport, `edmonds-2026-vpbands-v1`)
and optionally `position` (0-based SERP rank). The previous default,
models/m5_final_model.json (2026-05-02, nine features, LOSO 0.769), is kept
in place and copied to models/m5_final_model.legacy-2026-05-02.json; its
features were computed on fixation-selected rows with gaze-to-cursor
distances and fixation-weighted dwell, so they carried part of the
gaze-return label and were not the measurement this module computes at
runtime (see attentional-foraging/docs/ablations/deferred_drop_decomposition.md).
The extractor still returns all nine cursor values for other consumers; the
classifier feeds the model only the features its JSON `features` list
names, in that order, whichever model is loaded.

The cursor feature extractor mirrors compute_features_py in
scripts/test_feature_tracker_parity.py (and ResultProximityTracker in
src/approach-retreat.js — both parity-tested against the upstream M4
extractor in attentional-foraging). The viewport-band extractor wraps
compute_viewport_bands_py in scripts/test_viewport_bands_parity.py (the
`edmonds-2026-vpbands-v1` rule) rather than duplicating it.

Public API:
    classifier = M5Classifier()
    feats = extract_m5_features(cursor_samples, aoi_y_center)
    bands = extract_viewport_bands(timeline, aoi, scr_h)          # v3 only
    vec = build_feature_vector(feats, bands=bands, position=pos)
    score = classifier.predict_score(vec)      # P(deferred), primary output
    label = classifier.predict_label(vec)      # convenience at one threshold
    ops = classifier.operating_points()        # None on a v2-only model
    cal = classifier.calibration()             # None on a v2-only model
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MODEL_JSON = Path(__file__).resolve().parent / "models/m5_cursor_only_v2.json"
# Retired 2026-09-18; nine features on the fixation-selected LAB stream. Load explicitly
# via M5Classifier(model_path=LEGACY_MODEL_JSON) if the old scores are ever needed.
LEGACY_MODEL_JSON = Path(__file__).resolve().parent / "models/m5_final_model.legacy-2026-05-02.json"
# v3: adds viewport-band features (+ optional `position`) to the v2 seven.
# Produced by a separate pipeline in attentional-foraging; may not exist yet.
MODEL_JSON_V3 = Path(__file__).resolve().parent / "models/m5_v3_cursor_bands.json"

PROX_THRESHOLD = 100  # px — same as M4/M5 paper convention
MIN_VEL_DT_MS = 8  # tracker floors dt for the velocity divide only (~125 Hz ceiling)
MAX_PLAUSIBLE_VEL = 5000  # px/s; tracker's symmetric clamp

_DEFAULT_ANNOUNCED = False


def _select_default_model() -> Path:
    """v3 becomes the default automatically the moment its file exists, so a
    model swap reaches every consumer of DEFAULT_MODEL (build_replay_trial.py,
    select_testbed.py) without a second edit here. The choice is announced
    once to stderr because it is otherwise invisible — replay bundles carried
    a retired model's scores through several rebuilds with nothing in the
    log to show it (docs/validation/2026-09-18-claims-inventory.md §0)."""
    global _DEFAULT_ANNOUNCED
    path = MODEL_JSON_V3 if MODEL_JSON_V3.exists() else MODEL_JSON
    if not _DEFAULT_ANNOUNCED:
        print(f"m5_inference: default model -> {path.name}", file=sys.stderr)
        _DEFAULT_ANNOUNCED = True
    return path


DEFAULT_MODEL = _select_default_model()


def extract_m5_features(cursor: list[dict], aoi_y_center: float, prox_threshold: int = PROX_THRESHOLD) -> dict | None:
    """Compute the M4 nine-feature approach vector for one cursor stream
    against one AOI center. Returns None if too few samples or never
    approached (min_dist >= prox_threshold).

    All nine values are returned for callers that want them; a model
    consumes only the features named in its own `features` list — v2 uses
    seven (final_dist and retreat_dist are excluded by the click-buffer
    screen, CIKM section 3.4); v3 uses the same seven plus viewport bands.

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


def extract_viewport_bands(timeline: list[dict], aoi: dict, scr_h: float) -> dict:
    """Per-AOI cumulative viewport-band ms for one AOI, over one timeline.

    Thin wrapper over compute_viewport_bands_py (scripts/test_viewport_bands_parity.py
    — the canonical `edmonds-2026-vpbands-v1` reference, also parity-tested
    against the JS implementation there). This function does not
    reimplement the rule; it packages the single-AOI case build_feature_vector
    needs and renames the output to the model's feature names.

    Input shapes (matching compute_viewport_bands_py exactly):
      timeline: list of {"t": ms, "scrollY": px}, sorted by t, with at least
        two entries — one at the window start and one at the window end (the
        function walks consecutive pairs and treats each interval's `scrollY`
        as constant, i.e. piecewise-constant scroll). Callers should force an
        entry at t=window_start (scrollY=0.0, page starts unscrolled) and
        append one at t=window_end holding the last known scrollY, with one
        entry per scroll event in between — see band_ms() in
        attentional-foraging/scripts/viewport_bands_cursor_only.py for the
        reference construction.
      aoi: {"position": id, "page_top": y0, "page_bot": y1} — one AOI's
        vertical extent, in the SAME coordinate space as timeline's scrollY
        and scr_h (screenshot space for this repo's replay bundles).
      scr_h: viewport height, in that same space.

    Returns {"vt_top": ms, "vt_mid": ms, "vt_bot": ms, "vp_any": ms}. All
    zero if the timeline has fewer than two entries or scr_h is falsy (no
    interval to accumulate over).
    """
    from test_viewport_bands_parity import compute_viewport_bands_py

    bands = compute_viewport_bands_py(timeline, [aoi], scr_h)
    if not bands:
        return {"vt_top": 0.0, "vt_mid": 0.0, "vt_bot": 0.0, "vp_any": 0.0}
    b = bands[0]
    return {
        "vt_top": b["top_ms"],
        "vt_mid": b["mid_ms"],
        "vt_bot": b["bot_ms"],
        "vp_any": b["any_ms"],
    }


def build_feature_vector(cursor_feats: dict, bands: dict | None = None,
                          position: int | None = None) -> dict:
    """Merge cursor features (extract_m5_features) with optional viewport
    bands (extract_viewport_bands) and SERP position into one feature dict
    for M5Classifier.predict_score / predict_label.

    Only the keys the loaded model's `features` list actually names are
    read at predict time — passing extra keys (e.g. bands to a v2-only
    model) is harmless; passing too FEW for what the model needs raises a
    KeyError naming the missing feature.
    """
    feats = dict(cursor_feats)
    if bands is not None:
        feats["vt_top"] = bands["vt_top"]
        feats["vt_mid"] = bands["vt_mid"]
        feats["vt_bot"] = bands["vt_bot"]
    if position is not None:
        feats["position"] = position
    return feats


class M5Classifier:
    def __init__(self, model_path: Path = DEFAULT_MODEL):
        # Kept so consumers can log which coefficients they actually loaded.
        # Replay bundles shipped legacy scores for months because nothing
        # printed the model file at build time (claims inventory §0).
        self.model_path = model_path
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

    def predict_score(self, feats: dict) -> float:
        """Return P(deferred | features) — the primary M5 output.

        Reads only the features this model's JSON names, in that order;
        extra keys in `feats` are ignored. A feature the model needs but
        `feats` lacks raises KeyError naming it, rather than a bare
        dict-lookup KeyError, so a caller can tell "wrong model" from
        "wrong feature dict" immediately.
        """
        z = self.intercept
        for i, name in enumerate(self.features):
            if name not in feats:
                raise KeyError(
                    f"missing feature {name!r} required by {self.model_path.name} "
                    f"(model expects: {self.features}; got: {sorted(feats)})")
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

    # Back-compat alias — every existing caller (build_replay_trial.py,
    # select_testbed.py, prior sessions' notes) spells this predict_proba.
    predict_proba = predict_score

    def predict_label(self, feats: dict, threshold: float | None = None) -> str:
        """Convenience label at ONE operating point (default: this model's
        own `operating_threshold`). This is not the canonical output.

        Per the 2026-09-19 decision (docs/CURATION.md), M5 emits a
        continuous deferred_score; a hard label collapses that score to a
        single threshold's worth of information and hides how weak the
        REJECTED side of the call is. Before trusting this label, check the
        rejected-side precision at the threshold in use: if the model ships
        an `operating_points` block, each row carries `rejected_precision`/
        `rejected_recall` per threshold (read via `operating_points()`);
        otherwise fall back to `model['loso_youden_j']` — on v2 at its own
        Youden threshold (p*=0.477), a DEFERRED call is right 78.1% of the
        time but a REJECTED call is right only 48.5% (derived from TPR
        0.7276 / FPR 0.4425 on 6,800 deferred / 3,132 rejected rows) — worse
        than a coin flip's complement. `threshold=` overrides the model's
        default operating point for exploring the operating_points table.
        """
        thr = threshold if threshold is not None else self.threshold
        return "DEFERRED" if self.predict_score(feats) >= thr else "EVALUATED_REJECTED"

    def operating_points(self) -> list[dict] | None:
        """v3+ block: [{threshold, predicted_deferred_share, deferred_precision,
        deferred_recall, rejected_precision, rejected_recall}, ...] including
        the Youden and prior-matching rows. None on a v2-only model."""
        return self.model.get("operating_points")

    def calibration(self) -> dict | None:
        """v3+ block: {bins, brier, max_abs_gap, verdict}. None on a v2-only
        model."""
        return self.model.get("calibration")


def aoi_y_center(bbox: dict) -> float:
    return bbox["location"]["y"] + bbox["size"]["height"] / 2.0
