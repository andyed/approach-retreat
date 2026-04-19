#!/usr/bin/env node
/**
 * Parity test for `computeViewportBandsPure` (JS) vs. the canonical
 * batch computation lifted from `viewport_ms_for_trial` in
 * attentional-foraging/scripts/viewport_time_calibration.py.
 *
 * Writes fixtures/viewport_bands_trajectory.json (the scroll timeline + AOI
 * bands) and fixtures/js_viewport_bands.json (this script's output). The
 * companion Python script reads the trajectory, runs the reference logic,
 * and writes fixtures/py_viewport_bands.json. The two files must match to
 * 1e-6 on every field.
 *
 * Run:
 *   node scripts/test_viewport_bands_parity.js
 *   python3 scripts/test_viewport_bands_parity.py
 *   diff fixtures/js_viewport_bands.json fixtures/py_viewport_bands.json
 */

import { computeViewportBandsPure } from '../src/approach-retreat.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(__dirname, '..', 'fixtures');
mkdirSync(FIXTURES, { recursive: true });

// Synthetic trajectory exercising every edge case called out in the plan:
//   1. AOI fully above viewport throughout (position 5, will never be visible)
//   2. AOI fully below viewport throughout (position 3)
//   3. AOI center crosses all three thirds during scroll (position 1)
//   4. Tall AOI (page_bot - page_top > scr_h) — center sometimes outside
//      viewport while AOI still intersects, counts in any_ms only (position 4)
//   5. Zero-duration interval (t=2500 → t=2500) — must be skipped
//   6. Final stationary interval after last scroll (t=2500 → t=4000)
const trajectory = {
  doc_h: 3000,
  scr_h: 900,
  scroll_events: [
    { t: 0,    scrollY: 0   },
    { t: 1000, scrollY: 300 },
    { t: 2500, scrollY: 900 },
    { t: 2500, scrollY: 900 },  // dt = 0 — must not accumulate
    { t: 4000, scrollY: 900 },  // stationary tail
  ],
  aois: [
    { position: 0, page_top: 200,   page_bot: 350  },  // top of page
    { position: 1, page_top: 400,   page_bot: 550  },  // mid of page
    { position: 2, page_top: 1200,  page_bot: 1350 },  // appears on scroll
    { position: 3, page_top: 2800,  page_bot: 2950 },  // never reached
    { position: 4, page_top: 500,   page_bot: 1700 },  // TALL AOI (> scr_h)
    { position: 5, page_top: -500,  page_bot: -100 },  // always above viewport
  ],
};

console.log(`synthetic trajectory:`);
console.log(`  doc_h=${trajectory.doc_h}, scr_h=${trajectory.scr_h}`);
console.log(`  ${trajectory.scroll_events.length} scroll events, ${trajectory.aois.length} AOIs`);

const jsBands = computeViewportBandsPure(
  trajectory.scroll_events,
  trajectory.aois,
  trajectory.scr_h
);

console.log('\n── JS computeViewportBandsPure ──');
console.log(`${'pos'.padEnd(4)} ${'any_ms'.padStart(8)} ${'top_ms'.padStart(8)} ${'mid_ms'.padStart(8)} ${'bot_ms'.padStart(8)}`);
for (const r of jsBands) {
  console.log(
    `${String(r.position).padEnd(4)} ${String(r.any_ms).padStart(8)} ${String(r.top_ms).padStart(8)} ${String(r.mid_ms).padStart(8)} ${String(r.bot_ms).padStart(8)}`
  );
}

writeFileSync(
  join(FIXTURES, 'viewport_bands_trajectory.json'),
  JSON.stringify(trajectory, null, 2)
);
writeFileSync(
  join(FIXTURES, 'js_viewport_bands.json'),
  JSON.stringify(jsBands, null, 2)
);
console.log(`\nwrote ${join(FIXTURES, 'viewport_bands_trajectory.json')}`);
console.log(`wrote ${join(FIXTURES, 'js_viewport_bands.json')}`);
console.log('\nNow run: python3 scripts/test_viewport_bands_parity.py');
