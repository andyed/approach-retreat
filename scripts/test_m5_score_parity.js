#!/usr/bin/env node
/**
 * Parity check for createDeferredScorer (JS) vs. the model JSON's own
 * documented `apply` formula, computed independently in Python from stdlib
 * `json` + `math` only — NOT by importing scripts/m5_inference.py, which
 * another agent is actively changing.
 *
 * For five fixed feature vectors (one at the scaler mean, one all-zeros,
 * three arbitrary-but-fixed points spanning the feature ranges), both
 * sides apply:
 *
 *   score = sigmoid(sum_i(coef_i * (feat_i - scaler_mean_i) / scaler_scale_i) + intercept)
 *
 * against scripts/models/m5_cursor_only_v2.json and must agree within 1e-9.
 * Exits non-zero on any mismatch, and also on zero comparisons performed
 * (a parity test that silently compares nothing must fail, not pass).
 *
 * Run: node scripts/test_m5_score_parity.js
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createDeferredScorer } from '../src/deferred-score.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MODEL_PATH = join(__dirname, 'models', 'm5_cursor_only_v2.json');
const TOLERANCE = 1e-9;

const model = JSON.parse(readFileSync(MODEL_PATH, 'utf8'));
const scorer = createDeferredScorer(model);
const featureNames = model.features;

// Five fixed vectors, in feature order. Not random — deterministic and
// reproducible across runs.
const VECTORS = [
  model.scaler_mean.slice(), // at the mean → z reduces to the intercept
  featureNames.map(() => 0), // all-zero raw features
  [50, 800, 3000, -20, 3000, 80, 0.6],
  [10, 200, 100, 100, 500, 5, 0.1],
  [100, 1200, 6000, -100, 5000, 150, 0.9],
];

const PY_SCRIPT = `
import json, math, sys
model = json.load(open(sys.argv[1]))
vec = json.loads(sys.argv[2])
z = model["intercept"]
for c, m, s, x in zip(model["coefficients_raw"], model["scaler_mean"], model["scaler_scale"], vec):
    z += c * (x - m) / s
score = 1.0 / (1.0 + math.exp(-z))
print(repr(score))
`;

function pythonScore(vec) {
  const out = execFileSync(
    'python3',
    ['-c', PY_SCRIPT, MODEL_PATH, JSON.stringify(vec)],
    { encoding: 'utf8' }
  );
  return parseFloat(out.trim());
}

console.log(`model: ${MODEL_PATH}`);
console.log(`features (${featureNames.length}): ${featureNames.join(', ')}`);
console.log(`tolerance: ${TOLERANCE}\n`);

let compared = 0;
let mismatches = 0;

for (let i = 0; i < VECTORS.length; i++) {
  const vec = VECTORS[i];
  const features = {};
  featureNames.forEach((name, idx) => {
    features[name] = vec[idx];
  });

  const jsScore = scorer.score(features);
  const pyScoreValue = pythonScore(vec);

  compared++;
  const diff =
    typeof jsScore === 'number' ? Math.abs(jsScore - pyScoreValue) : Infinity;
  const ok = Number.isFinite(diff) && diff <= TOLERANCE;
  if (!ok) mismatches++;

  console.log(
    `vector ${i} [${vec.join(', ')}]\n` +
      `  js=${jsScore}  py=${pyScoreValue}  diff=${diff.toExponential(3)}  ${
        ok ? 'OK' : 'MISMATCH'
      }`
  );
}

console.log('');
if (compared === 0) {
  console.error('FAIL: zero comparisons performed');
  process.exit(1);
}
if (mismatches > 0) {
  console.error(
    `FAIL: ${mismatches}/${compared} vectors exceeded tolerance ${TOLERANCE}`
  );
  process.exit(1);
}
console.log(`PASS: ${compared}/${compared} vectors matched within ${TOLERANCE}`);
