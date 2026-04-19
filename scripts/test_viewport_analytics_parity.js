#!/usr/bin/env node
/**
 * Parity test for `computeViewportAnalyticsPure` (JS) vs. the canonical
 * reference in attentional-foraging/scripts/nb30_scroll_trajectory.py.
 *
 * Writes fixtures/viewport_analytics_trajectory.json (the scroll timeline
 * + AOI bboxes) and fixtures/js_viewport_analytics.json (this script's
 * output). The companion Python script reads the trajectory, runs the
 * reference logic, and writes fixtures/py_viewport_analytics.json. The
 * two files must match to 1e-6 on every field.
 *
 * Run:
 *   node scripts/test_viewport_analytics_parity.js
 *   python3 scripts/test_viewport_analytics_parity.py
 */

import { computeViewportAnalyticsPure } from '../src/approach-retreat.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(__dirname, '..', 'fixtures');
mkdirSync(FIXTURES, { recursive: true });

// Trajectory exercising the features we emit:
//   - Variable-velocity scroll (so min_abs_velocity, n_reversals have bite)
//   - Reversal (scroll back up) to exercise n_reversals
//   - Pause (stationary segment) → min_abs_velocity = 0
//   - AOI partially visible → max_overlap_frac < 1
//   - AOI fully visible → max_overlap_frac = 1
//   - AOI crosses viewport center → vt_center_ms > 0
const trajectory = {
  doc_h: 3000,
  scr_h: 900,
  center_tol_px: 100,
  iab_viewable_threshold_ms: 1000,
  scroll_events: [
    { t: 0,    scrollY: 0   },
    { t: 1000, scrollY: 300 },   // down slow, 300 px/s
    { t: 1500, scrollY: 900 },   // down fast, 1200 px/s
    { t: 2000, scrollY: 900 },   // pause (0 px/s)
    { t: 3000, scrollY: 500 },   // REVERSAL — back up, -400 px/s
    { t: 4000, scrollY: 500 },   // pause
    { t: 5000, scrollY: 1400 },  // down again, 900 px/s (second reversal)
  ],
  aois: [
    { position: 0, page_top: 100,  page_bot: 250  }, // top of page; scrolls past
    { position: 1, page_top: 400,  page_bot: 550  }, // mid visibility
    { position: 2, page_top: 1000, page_bot: 1150 }, // appears late
    { position: 3, page_top: 2800, page_bot: 2950 }, // never reached
    { position: 4, page_top: 1200, page_bot: 2400 }, // TALL AOI (> scr_h)
  ],
};

console.log(`synthetic trajectory:`);
console.log(`  doc_h=${trajectory.doc_h}, scr_h=${trajectory.scr_h}, center_tol=±${trajectory.center_tol_px}`);
console.log(`  ${trajectory.scroll_events.length} scroll events, ${trajectory.aois.length} AOIs`);

const jsAnalytics = computeViewportAnalyticsPure(
  trajectory.scroll_events,
  trajectory.aois,
  trajectory.scr_h,
  trajectory.center_tol_px,
  trajectory.iab_viewable_threshold_ms
);

console.log('\n── JS computeViewportAnalyticsPure ──');
console.log(
  `${'pos'.padEnd(4)} ${'any_ms'.padStart(8)} ${'ctr_ms'.padStart(8)} ${'avg_vpy'.padStart(8)} ` +
  `${'max_ovf'.padStart(8)} ${'min|v|'.padStart(9)} ${'rev'.padStart(4)}`
);
for (const r of jsAnalytics) {
  console.log(
    `${String(r.position).padEnd(4)} ${String(r.vt_any_ms).padStart(8)} ` +
    `${String(r.vt_center_ms).padStart(8)} ` +
    `${r.avg_viewport_y_px.toFixed(1).padStart(8)} ` +
    `${r.max_overlap_frac.toFixed(4).padStart(8)} ` +
    `${r.min_abs_velocity_px_per_s.toFixed(2).padStart(9)} ` +
    `${String(r.n_reversals).padStart(4)}`
  );
}

writeFileSync(
  join(FIXTURES, 'viewport_analytics_trajectory.json'),
  JSON.stringify(trajectory, null, 2)
);
writeFileSync(
  join(FIXTURES, 'js_viewport_analytics.json'),
  JSON.stringify(jsAnalytics, null, 2)
);
console.log(`\nwrote ${join(FIXTURES, 'viewport_analytics_trajectory.json')}`);
console.log(`wrote ${join(FIXTURES, 'js_viewport_analytics.json')}`);
console.log('\nNow run: python3 scripts/test_viewport_analytics_parity.py');
