/**
 * Deferred-score: apply a pre-trained M5-style logistic-regression model
 * (standardized features, sigmoid link) to cursor/viewport features and
 * return a continuous score in [0, 1], not a predicted label.
 *
 * Decision (0.4.0): the library emits a *score*, never a threshold-applied
 * label. Cursor-only per-instance deferred-vs-rejected classification is
 * 0.69 LOSO AUC (scripts/models/m5_cursor_only_v2.json), and a REJECTED
 * label at the Youden-J operating point is only as good as that operating
 * point's error rates — thresholding is a consumer choice, not something
 * this library should bake in. See CHANGELOG.md 0.4.0.
 *
 * Pure, no DOM. Model JSON schema (see scripts/models/m5_cursor_only_v2.json
 * and scripts/models/m5_v3_cursor_bands.json):
 *   features:          ordered feature names
 *   scaler_mean:        per-feature mean (same order)
 *   scaler_scale:       per-feature scale (same order)
 *   coefficients_raw:   per-feature logistic-regression coefficient
 *   intercept:          scalar intercept
 *   apply: "score = sigmoid(sum_i(coef_i * (feat_i - scaler_mean_i) / scaler_scale_i) + intercept)"
 *
 * v3 models add three viewport-band feature names — `vt_top`, `vt_mid`,
 * `vt_bot` — and, for the rank variant, `position`. Those names don't match
 * anything the library emits directly (the tracker/band accumulator uses
 * `top_ms` / `mid_ms` / `bot_ms`), so callers pass `featureAliases` to map
 * a model-declared name onto the key actually present in the features
 * object handed to `score()`.
 */

/**
 * Derive a short, stable id for a model JSON, for provenance stamping on
 * emitted events. Prefers an explicit id field, falls back to the
 * provenance block's producer script (basename) or its sha256 prefix, and
 * finally 'unknown' — models are never required to carry any of these.
 */
function deriveModelId(modelJson) {
  if (!modelJson || typeof modelJson !== 'object') return 'unknown';
  if (typeof modelJson.model_id === 'string' && modelJson.model_id) {
    return modelJson.model_id;
  }
  if (typeof modelJson.id === 'string' && modelJson.id) {
    return modelJson.id;
  }
  const prov = modelJson.provenance;
  if (prov && typeof prov === 'object') {
    if (typeof prov.producer === 'string' && prov.producer) {
      const base = prov.producer.split('/').pop();
      if (base) return base;
    }
    if (typeof prov.producer_sha256 === 'string' && prov.producer_sha256) {
      return prov.producer_sha256.slice(0, 12);
    }
  }
  return 'unknown';
}

/**
 * Build a scorer from a parsed M5-style model JSON object. The library
 * never fetches — callers load/parse the model JSON themselves and hand
 * it in.
 *
 * @param {object} modelJson — parsed model JSON (see schema above).
 * @param {object} [options]
 * @param {Object<string,string>} [options.featureAliases] — maps a name in
 *   `modelJson.features` to the key actually present in the object passed
 *   to `score()`, for feature names the caller's data doesn't use verbatim
 *   (e.g. `{ vt_top: 'top_ms' }`). Names absent from this map are looked up
 *   verbatim.
 * @returns {{
 *   score: (features: object) => number|null,
 *   features: string[],
 *   operatingThreshold: number|null,
 *   operatingPoints: object|null,
 *   calibration: object|null,
 *   semantics: object|null,
 *   modelId: string,
 * }}
 */
export function createDeferredScorer(modelJson, options = {}) {
  const { featureAliases = {} } = options;

  const featureNames = Array.isArray(modelJson?.features)
    ? modelJson.features
    : [];
  const scalerMean = modelJson?.scaler_mean;
  const scalerScale = modelJson?.scaler_scale;
  const coefficients = modelJson?.coefficients_raw;
  const intercept = modelJson?.intercept;

  const valid =
    featureNames.length > 0 &&
    Array.isArray(scalerMean) &&
    scalerMean.length === featureNames.length &&
    Array.isArray(scalerScale) &&
    scalerScale.length === featureNames.length &&
    Array.isArray(coefficients) &&
    coefficients.length === featureNames.length &&
    Number.isFinite(intercept);

  /**
   * Score a features object. Returns null (never NaN) when the model is
   * malformed, `features` is nullish, or any named feature is missing or
   * non-finite — never throws.
   */
  function score(features) {
    if (!valid || !features || typeof features !== 'object') return null;

    let z = intercept;
    for (let i = 0; i < featureNames.length; i++) {
      const modelName = featureNames[i];
      const key = featureAliases[modelName] ?? modelName;
      const raw = features[key];
      if (!Number.isFinite(raw)) return null;

      const scale = scalerScale[i];
      const standardized = (raw - scalerMean[i]) / scale;
      z += coefficients[i] * standardized;
    }
    if (!Number.isFinite(z)) return null;

    const s = 1 / (1 + Math.exp(-z));
    return Number.isFinite(s) ? s : null;
  }

  return {
    score,
    features: featureNames,
    operatingThreshold: Number.isFinite(modelJson?.operating_threshold)
      ? modelJson.operating_threshold
      : null,
    operatingPoints: modelJson?.operating_points ?? null,
    calibration: modelJson?.calibration ?? null,
    semantics: modelJson?.score_semantics ?? null,
    modelId: deriveModelId(modelJson),
  };
}
