#!/usr/bin/env node
/**
 * Parity smoke test for ResultFeatureTracker (JS) vs. the canonical
 * AdSERP extractor in
 * attentional-foraging/scripts/m4_nb21_hybrid_rerun.py.
 *
 * We construct a synthetic trajectory of (pageY, t) samples, feed it
 * through the JS tracker, and also write it to a JSON fixture that a
 * companion Python script reads and processes via the paper's feature
 * extraction logic (lifted out of m4_nb21_hybrid_rerun.py's
 * compute_hybrid_features inner loop). Both sides must produce the
 * same nine-feature values within 1e-6 tolerance.
 *
 * Run:
 *   node scripts/test_feature_tracker_parity.js
 *   python3 scripts/test_feature_tracker_parity.py
 *   diff fixtures/js_features.json fixtures/py_features.json  # should match
 */

import { ResultFeatureTracker } from '../src/approach-retreat.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(__dirname, '..', 'fixtures');
mkdirSync(FIXTURES, { recursive: true });

// Result center at pageY = 500 px (a typical mid-SERP position)
const CENTER = 500;
const PROX = 100;

// Synthetic trajectory: cursor starts at pageY = 50 (top of page),
// approaches the result center, overshoots slightly, settles, drifts
// away, returns, and finally drifts far away. Timestamps in ms with
// 16.67 ms intervals (60 Hz).
const trajectory = [];
let t = 1000;
const dt = 16.67;

// Approach from top: 50 → 510 in 30 samples (overshoots center by 10)
for (let i = 0; i < 30; i++) {
  const y = 50 + (460 * i) / 29; // 50 → 510
  trajectory.push({ pageY: y, t });
  t += dt;
}
// Settle near center: 510 → 495 → 505 → 498 (4 samples)
[510, 495, 505, 498].forEach((y) => {
  trajectory.push({ pageY: y, t });
  t += dt;
});
// Drift away: 498 → 350 in 10 samples (retreat)
for (let i = 0; i < 10; i++) {
  const y = 498 - (148 * i) / 9;
  trajectory.push({ pageY: y, t });
  t += dt;
}
// Return to near center: 350 → 495 in 10 samples (reapproach)
for (let i = 0; i < 10; i++) {
  const y = 350 + (145 * i) / 9;
  trajectory.push({ pageY: y, t });
  t += dt;
}
// Final drift away: 495 → 700 in 10 samples (end far from result)
for (let i = 0; i < 10; i++) {
  const y = 495 + (205 * i) / 9;
  trajectory.push({ pageY: y, t });
  t += dt;
}

console.log(`synthetic trajectory: ${trajectory.length} samples`);
console.log(`  y range: ${Math.min(...trajectory.map((s) => s.pageY)).toFixed(1)} → ${Math.max(...trajectory.map((s) => s.pageY)).toFixed(1)}`);
console.log(`  t range: ${trajectory[0].t} → ${trajectory[trajectory.length - 1].t} ms`);
console.log(`  result center: pageY = ${CENTER}`);

// Run through JS tracker
const tracker = new ResultFeatureTracker(CENTER, PROX);
for (const { pageY, t: ts } of trajectory) {
  tracker.update(pageY, ts);
}
const jsFeatures = tracker.getFeatures();

console.log('\n── JS ResultFeatureTracker features ──');
for (const [k, v] of Object.entries(jsFeatures)) {
  console.log(`  ${k.padEnd(24)}  ${typeof v === 'number' ? v.toFixed(6) : v}`);
}

// Write fixture for Python counterpart
writeFileSync(
  join(FIXTURES, 'trajectory.json'),
  JSON.stringify(
    {
      center_pageY: CENTER,
      proximity_px: PROX,
      samples: trajectory,
    },
    null,
    2
  )
);
writeFileSync(
  join(FIXTURES, 'js_features.json'),
  JSON.stringify(jsFeatures, null, 2)
);
console.log(`\nwrote ${join(FIXTURES, 'trajectory.json')}`);
console.log(`wrote ${join(FIXTURES, 'js_features.json')}`);
console.log('\nNow run: python3 scripts/test_feature_tracker_parity.py');
