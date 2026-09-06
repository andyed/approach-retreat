import { describe, it, expect } from 'vitest';
import { ResultFeatureTracker } from '../../src/approach-retreat.js';

// Regression guard for the dt→0 velocity blow-up. At high mousemove sample
// rates Δt can be 1-2 ms; dividing a few px of inward motion by it once
// produced >9000 px/s (mbp.sqlite ar_session_aoi, n=450, max 11,249.99).
// The tracker floors Δt and clamps the per-sample velocity so the emitted
// max/mean_approach_velocity stay physically plausible. See the DIVERGENCE
// note in src/approach-retreat.js: the Python reference does NOT floor small
// positive Δt and so carries the same defect — this bound is JS-only.
const MAX_PLAUSIBLE_VEL = 5000; // must match the library constant

describe('ResultFeatureTracker — velocity physical bound', () => {
  it('keeps max_approach_velocity bounded under 1-2 ms sample spacing', () => {
    // Cursor rushing inward toward a result centered at pageY=400, sampled
    // every ~1-2 ms — the exact condition that produced 11k px/s in the wild.
    const tracker = new ResultFeatureTracker(400, 100);
    let t = 1000;
    let y = 0; // far away, approaching the center
    for (let i = 0; i < 200; i++) {
      tracker.update(y, t);
      y += 12; // 12 px of inward motion per sample
      t += 1.5; // ~1.5 ms spacing → naive vel ≈ 8000 px/s
    }
    const f = tracker.getFeatures();

    expect(f.max_approach_velocity).toBeLessThanOrEqual(MAX_PLAUSIBLE_VEL);
    expect(f.max_approach_velocity).toBeGreaterThan(0); // still saw approach
    // mean is a signed/directed velocity; magnitude must also stay bounded.
    expect(Math.abs(f.mean_approach_velocity)).toBeLessThanOrEqual(
      MAX_PLAUSIBLE_VEL,
    );
  });

  it('also bounds retreat (negative) velocity symmetrically', () => {
    const tracker = new ResultFeatureTracker(0, 100);
    let t = 1000;
    let y = 0; // start at center, retreat rapidly
    for (let i = 0; i < 200; i++) {
      tracker.update(y, t);
      y += 15; // moving away → negative directed velocity
      t += 1; // 1 ms spacing → naive vel ≈ -15000 px/s
    }
    const f = tracker.getFeatures();

    expect(f.mean_approach_velocity).toBeGreaterThanOrEqual(-MAX_PLAUSIBLE_VEL);
    // max should be ≤ 0 here (no inward motion ever occurred) and bounded.
    expect(f.max_approach_velocity).toBeLessThanOrEqual(MAX_PLAUSIBLE_VEL);
  });

  it('leaves normal-rate velocities (≥8 ms spacing) unclamped', () => {
    // A realistic 60 Hz approach: ~6 px every 16.7 ms ≈ 360 px/s, well below
    // the cap — confirms the bound is a guard, not a blanket rescale.
    const tracker = new ResultFeatureTracker(400, 100);
    let t = 1000;
    let y = 0;
    for (let i = 0; i < 50; i++) {
      tracker.update(y, t);
      y += 6;
      t += 16.7;
    }
    const f = tracker.getFeatures();
    expect(f.max_approach_velocity).toBeGreaterThan(300);
    expect(f.max_approach_velocity).toBeLessThan(500);
  });
});
