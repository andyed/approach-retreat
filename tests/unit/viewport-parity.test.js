import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  computeViewportBandsPure,
  computeViewportAnalyticsPure,
} from '../../src/approach-retreat.js';

// Formalizes scripts/test_viewport_bands_parity.{js,py} and
// scripts/test_viewport_analytics_parity.{js,py}. Golden values are the
// Python references (viewport_time_calibration.py / nb30_scroll_trajectory.py);
// JS must match every field within 1e-6.
const HERE = dirname(fileURLToPath(import.meta.url));
const golden = (name) =>
  JSON.parse(readFileSync(join(HERE, '..', 'golden', name), 'utf8'));

/**
 * Compare two arrays of per-AOI records keyed by `position`. Every field that
 * appears in the expected record must be present in the computed record and
 * match — numerics within 1e-6, everything else exactly.
 */
function expectRecordsClose(got, want) {
  expect(got.length).toBe(want.length);
  const byPos = new Map(got.map((r) => [r.position, r]));
  for (const w of want) {
    const g = byPos.get(w.position);
    expect(g, `position ${w.position} present`).toBeTruthy();
    for (const [k, v] of Object.entries(w)) {
      if (typeof v === 'number') {
        expect(g[k], `pos ${w.position} field ${k}`).toBeCloseTo(v, 6);
      } else {
        expect(g[k], `pos ${w.position} field ${k}`).toEqual(v);
      }
    }
  }
}

describe('computeViewportBandsPure — JS↔Python parity', () => {
  it('matches the viewport_ms_for_trial reference on every AOI/band', () => {
    const t = golden('viewport_bands_trajectory.json');
    const got = computeViewportBandsPure(t.scroll_events, t.aois, t.scr_h);
    expectRecordsClose(got, golden('viewport_bands_expected.json'));
  });
});

describe('computeViewportAnalyticsPure — JS↔Python parity', () => {
  it('matches the nb30_scroll_trajectory reference on every AOI', () => {
    const t = golden('viewport_analytics_trajectory.json');
    const got = computeViewportAnalyticsPure(
      t.scroll_events,
      t.aois,
      t.scr_h,
      t.center_tol_px,
      t.iab_viewable_threshold_ms
    );
    expectRecordsClose(got, golden('viewport_analytics_expected.json'));
  });
});
