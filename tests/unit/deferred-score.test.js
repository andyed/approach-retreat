import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createDeferredScorer } from '../../src/deferred-score.js';

// Formalizes scripts/test_m5_score_parity.js's premise at the unit level:
// the scorer must reproduce the model JSON's documented `apply` formula
// exactly, must never throw or return NaN on malformed/missing input, and
// must support the v3 band-feature schema via featureAliases.
const HERE = dirname(fileURLToPath(import.meta.url));
const MODEL_V2 = JSON.parse(
  readFileSync(
    join(HERE, '..', '..', 'scripts', 'models', 'm5_cursor_only_v2.json'),
    'utf8'
  )
);

function sigmoid(z) {
  return 1 / (1 + Math.exp(-z));
}

/** Hand-computed reference: score = sigmoid(sum(coef_i * (x_i - mean_i) / scale_i) + intercept). */
function handComputeV2(featureVector) {
  const { scaler_mean, scaler_scale, coefficients_raw, intercept, features } =
    MODEL_V2;
  let z = intercept;
  for (let i = 0; i < features.length; i++) {
    const x = featureVector[features[i]];
    z += coefficients_raw[i] * ((x - scaler_mean[i]) / scaler_scale[i]);
  }
  return sigmoid(z);
}

describe('createDeferredScorer — v2 (cursor-only, seven features)', () => {
  const scorer = createDeferredScorer(MODEL_V2);

  it('exposes the model metadata read-only', () => {
    expect(scorer.features).toEqual(MODEL_V2.features);
    expect(scorer.operatingThreshold).toBeCloseTo(
      MODEL_V2.operating_threshold,
      12
    );
    expect(scorer.operatingPoints).toBe(null); // not present on v2
    expect(scorer.calibration).toBe(null); // not present on v2
    expect(scorer.modelId).toBe('export_m5_cursor_only.py');
  });

  it('reproduces a hand-computed sigmoid on a fixed feature vector', () => {
    const fixed = {
      min_dist: 12.5,
      mean_dist: 340.2,
      dwell_in_proximity_ms: 900,
      mean_approach_velocity: -30.4,
      max_approach_velocity: 1800,
      direction_changes: 6,
      frac_decreasing: 0.55,
    };
    const expected = handComputeV2(fixed);
    expect(scorer.score(fixed)).toBeCloseTo(expected, 12);
    // Sanity: it's a real probability, and not the intercept-only trivial case.
    expect(scorer.score(fixed)).toBeGreaterThan(0);
    expect(scorer.score(fixed)).toBeLessThan(1);
  });

  it('reproduces the sigmoid at exactly the scaler mean (z = intercept)', () => {
    const atMean = {};
    MODEL_V2.features.forEach((name, i) => {
      atMean[name] = MODEL_V2.scaler_mean[i];
    });
    expect(scorer.score(atMean)).toBeCloseTo(sigmoid(MODEL_V2.intercept), 12);
  });

  it('returns null (never NaN/throws) when a named feature is missing', () => {
    const missing = {
      min_dist: 12.5,
      mean_dist: 340.2,
      // dwell_in_proximity_ms omitted
      mean_approach_velocity: -30.4,
      max_approach_velocity: 1800,
      direction_changes: 6,
      frac_decreasing: 0.55,
    };
    expect(scorer.score(missing)).toBe(null);
  });

  it('returns null on a non-finite feature value (NaN, Infinity)', () => {
    const base = {
      min_dist: 12.5,
      mean_dist: 340.2,
      dwell_in_proximity_ms: 900,
      mean_approach_velocity: -30.4,
      max_approach_velocity: 1800,
      direction_changes: 6,
      frac_decreasing: 0.55,
    };
    expect(scorer.score({ ...base, min_dist: NaN })).toBe(null);
    expect(scorer.score({ ...base, mean_dist: Infinity })).toBe(null);
  });

  it('returns null on nullish or non-object input, without throwing', () => {
    expect(() => scorer.score(null)).not.toThrow();
    expect(scorer.score(null)).toBe(null);
    expect(scorer.score(undefined)).toBe(null);
  });

  it('returns null for a malformed model (mismatched array lengths)', () => {
    const broken = createDeferredScorer({
      ...MODEL_V2,
      scaler_mean: MODEL_V2.scaler_mean.slice(0, 3), // truncated — length mismatch
    });
    expect(
      broken.score({
        min_dist: 1,
        mean_dist: 1,
        dwell_in_proximity_ms: 1,
        mean_approach_velocity: 1,
        max_approach_velocity: 1,
        direction_changes: 1,
        frac_decreasing: 1,
      })
    ).toBe(null);
  });
});

describe('createDeferredScorer — v3 schema stub (band features + rank)', () => {
  // Inline stub model exercising the v3 schema: the seven base features plus
  // vt_top/vt_mid/vt_bot (viewport-band ms) and position (0-based rank).
  // Coefficients/scaler values are arbitrary but fixed — this test checks
  // the scorer's feature-aliasing and formula, not any real calibration.
  const STUB_V3 = {
    features: [
      'min_dist',
      'mean_dist',
      'dwell_in_proximity_ms',
      'mean_approach_velocity',
      'max_approach_velocity',
      'direction_changes',
      'frac_decreasing',
      'vt_top',
      'vt_mid',
      'vt_bot',
      'position',
    ],
    scaler_mean: [25, 560, 1500, 15, 2200, 50, 0.42, 1000, 800, 400, 2],
    scaler_scale: [28, 375, 1900, 130, 1500, 48, 0.15, 900, 700, 500, 2],
    coefficients_raw: [
      -0.09, -0.56, 0.33, -0.0004, -0.1, 0.14, -0.05, 0.4, 0.1, -0.2, -0.3,
    ],
    intercept: 0.1,
    operating_threshold: 0.5,
    operating_points: { youden: { threshold: 0.5 } },
    calibration: { method: 'platt' },
    score_semantics: { higher: 'more likely deferred' },
    apply:
      'score = sigmoid(sum_i(coef_i * (feat_i - scaler_mean_i) / scaler_scale_i) + intercept)',
  };

  const scorer = createDeferredScorer(STUB_V3, {
    featureAliases: { vt_top: 'top_ms', vt_mid: 'mid_ms', vt_bot: 'bot_ms' },
  });

  it('exposes operating_points, calibration, and semantics read-only', () => {
    expect(scorer.operatingPoints).toEqual(STUB_V3.operating_points);
    expect(scorer.calibration).toEqual(STUB_V3.calibration);
    expect(scorer.semantics).toEqual(STUB_V3.score_semantics);
  });

  it('maps vt_top/vt_mid/vt_bot onto top_ms/mid_ms/bot_ms via featureAliases, and reads position verbatim', () => {
    const features = {
      min_dist: 20,
      mean_dist: 500,
      dwell_in_proximity_ms: 1200,
      mean_approach_velocity: -10,
      max_approach_velocity: 900,
      direction_changes: 4,
      frac_decreasing: 0.4,
      top_ms: 1500,
      mid_ms: 700,
      bot_ms: 200,
      position: 1,
    };

    let z = STUB_V3.intercept;
    const rawByModelName = {
      min_dist: features.min_dist,
      mean_dist: features.mean_dist,
      dwell_in_proximity_ms: features.dwell_in_proximity_ms,
      mean_approach_velocity: features.mean_approach_velocity,
      max_approach_velocity: features.max_approach_velocity,
      direction_changes: features.direction_changes,
      frac_decreasing: features.frac_decreasing,
      vt_top: features.top_ms,
      vt_mid: features.mid_ms,
      vt_bot: features.bot_ms,
      position: features.position,
    };
    STUB_V3.features.forEach((name, i) => {
      z +=
        STUB_V3.coefficients_raw[i] *
        ((rawByModelName[name] - STUB_V3.scaler_mean[i]) /
          STUB_V3.scaler_scale[i]);
    });
    const expected = sigmoid(z);

    expect(scorer.score(features)).toBeCloseTo(expected, 12);
  });

  it('returns null when a band feature is absent (bands not tracked)', () => {
    const noBands = {
      min_dist: 20,
      mean_dist: 500,
      dwell_in_proximity_ms: 1200,
      mean_approach_velocity: -10,
      max_approach_velocity: 900,
      direction_changes: 4,
      frac_decreasing: 0.4,
      position: 1,
      // top_ms / mid_ms / bot_ms omitted entirely
    };
    expect(scorer.score(noBands)).toBe(null);
  });
});
