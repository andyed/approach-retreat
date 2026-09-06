import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { ResultFeatureTracker } from '../../src/approach-retreat.js';

// Formalizes scripts/test_feature_tracker_parity.{js,py} as an assertion.
// Golden values are the Python reference output (the canonical AdSERP
// extractor in attentional-foraging/scripts/m4_nb21_hybrid_rerun.py); the JS
// ResultFeatureTracker must reproduce all nine M4 features within 1e-6.
const HERE = dirname(fileURLToPath(import.meta.url));
const golden = (name) =>
  JSON.parse(readFileSync(join(HERE, '..', 'golden', name), 'utf8'));

describe('ResultFeatureTracker — JS↔Python parity (M4 nine-feature)', () => {
  const traj = golden('feature_trajectory.json');
  const expected = golden('feature_expected.json');

  const tracker = new ResultFeatureTracker(traj.center_pageY, traj.proximity_px);
  for (const { pageY, t } of traj.samples) tracker.update(pageY, t);
  const features = tracker.getFeatures();

  it('produces exactly the expected feature set', () => {
    expect(Object.keys(features).sort()).toEqual(Object.keys(expected).sort());
  });

  for (const [key, want] of Object.entries(expected)) {
    it(`${key} matches the Python reference within 1e-6`, () => {
      expect(features[key]).toBeCloseTo(want, 6);
    });
  }
});
