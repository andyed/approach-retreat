#!/usr/bin/env node
/**
 * Sanity check for the `maxSampleHz` fixed-rate throttle in
 * `ApproachRetreat._onMouseMove` (uniform time-decimation).
 *
 * Drives synthetic mousemove streams at known rates through a tracker
 * with a minimal DOM stub and confirms:
 *   - a high-rate stream is decimated to ~maxSampleHz with every
 *     inter-sample gap >= the configured interval (1000/maxSampleHz ms);
 *   - a stream already below maxSampleHz passes through unchanged;
 *   - maxSampleHz of 0 or Infinity disables the throttle entirely.
 *
 * No accuracy claim is made here — the §5.1 ablation already proved
 * uniform time-decimation is AUC-flat to 1 Hz. This only verifies the
 * live throttle keeps samples at the intended rate.
 *
 * Run:  node scripts/test_throttle_sanity.js
 */

import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// --- Minimal DOM stub: just the surface ApproachRetreat touches at
// construction and on each mousemove with all viewport tracking off. ---
const resultEl = {
  getAttribute: () => '0',
  getBoundingClientRect: () => ({
    left: 0, right: 800, top: 100, bottom: 200, width: 800, height: 100,
  }),
  closest: () => null,
};
global.IntersectionObserver = undefined;
global.ResizeObserver = undefined;
global.cancelAnimationFrame = () => {};
global.requestAnimationFrame = () => 0;
global.window = {
  scrollY: 0, innerHeight: 900,
  addEventListener: () => {}, removeEventListener: () => {},
};
global.document = {
  addEventListener: () => {}, removeEventListener: () => {},
  documentElement: null,
  querySelectorAll: () => [resultEl],
};

// Controllable clock so the synthetic stream has exact timestamps.
let CLOCK = 0;
global.performance = { now: () => CLOCK };

const { ApproachRetreat } = await import(
  join(__dirname, '..', 'src', 'approach-retreat.js')
);

let failures = 0;

function run(label, { hz, eventRateHz, durationMs }, check) {
  CLOCK = 0;
  const kept = [];
  const ar = new ApproachRetreat({
    maxSampleHz: hz,
    trackViewportBands: false,
    trackViewportAnalytics: false,
    trackVisibility: false,
    trackScroll: false,
    onEpisode: () => {},
  });
  // `_updateApproachFeatures` runs exactly once per KEPT mousemove, so
  // wrapping it records the kept-sample timeline.
  const orig = ar._updateApproachFeatures.bind(ar);
  ar._updateApproachFeatures = (pageY, t) => { kept.push(t); orig(pageY, t); };

  const eventDt = 1000 / eventRateHz;
  let rawEvents = 0;
  let y = 0;
  for (CLOCK = 0; CLOCK <= durationMs; CLOCK += eventDt) {
    y = (y + 7) % 600;
    ar._onMouseMove({ clientX: 400, clientY: y });
    rawEvents += 1;
  }
  const n = kept.length;
  const span = n > 1 ? kept[n - 1] - kept[0] : 0;
  const effHz = span > 0 ? ((n - 1) / span) * 1000 : 0;
  const gaps = [];
  for (let i = 1; i < n; i++) gaps.push(kept[i] - kept[i - 1]);
  const minGap = gaps.length ? Math.min(...gaps) : 0;
  const maxGap = gaps.length ? Math.max(...gaps) : 0;
  ar.destroy();

  console.log(label);
  console.log(`  input: ${eventRateHz} Hz over ${durationMs} ms (${rawEvents} raw events)`);
  console.log(`  maxSampleHz=${hz} -> kept ${n}/${rawEvents}, effective ${effHz.toFixed(2)} Hz`);
  console.log(`  inter-sample gap: min=${minGap.toFixed(2)} ms max=${maxGap.toFixed(2)} ms`);

  const result = check({ n, rawEvents, effHz, minGap, maxGap });
  if (result.ok) {
    console.log(`  PASS — ${result.msg}\n`);
  } else {
    console.log(`  FAIL — ${result.msg}\n`);
    failures += 1;
  }
}

// A) High-rate stream decimated to the cap. Every kept gap must be
//    >= the throttle interval (66.67 ms at 15 Hz) and effective rate
//    must land at ~15 Hz.
run('A) 60 Hz input, 15 Hz cap (default)',
  { hz: 15, eventRateHz: 60, durationMs: 2000 },
  ({ effHz, minGap }) => {
    const interval = 1000 / 15;
    const okGap = minGap >= interval - 1e-6;
    const okHz = effHz >= 13 && effHz <= 16;
    return {
      ok: okGap && okHz,
      msg: `min gap ${minGap.toFixed(2)} ms >= ${interval.toFixed(2)} ms and rate in [13,16] Hz`,
    };
  });

// B) High-refresh display: same cap holds.
run('B) 144 Hz input, 15 Hz cap (high-refresh display)',
  { hz: 15, eventRateHz: 144, durationMs: 2000 },
  ({ effHz, minGap }) => {
    const interval = 1000 / 15;
    return {
      ok: minGap >= interval - 1e-6 && effHz >= 13 && effHz <= 16,
      msg: `min gap ${minGap.toFixed(2)} ms >= ${interval.toFixed(2)} ms and rate in [13,16] Hz`,
    };
  });

// C) Stream already slower than the cap passes through untouched —
//    every raw event is kept.
run('C) 10 Hz input, 15 Hz cap (already below cap)',
  { hz: 15, eventRateHz: 10, durationMs: 2000 },
  ({ n, rawEvents }) => ({
    ok: n === rawEvents,
    msg: `all ${rawEvents} raw events kept (no decimation below cap)`,
  }));

// D) Throttle disabled with hz=0 — every raw event processed.
run('D) 60 Hz input, throttle disabled (maxSampleHz=0)',
  { hz: 0, eventRateHz: 60, durationMs: 2000 },
  ({ n, rawEvents }) => ({
    ok: n === rawEvents,
    msg: `all ${rawEvents} raw events kept (throttle off)`,
  }));

// E) Throttle disabled with Infinity — same.
run('E) 60 Hz input, throttle disabled (maxSampleHz=Infinity)',
  { hz: Infinity, eventRateHz: 60, durationMs: 2000 },
  ({ n, rawEvents }) => ({
    ok: n === rawEvents,
    msg: `all ${rawEvents} raw events kept (throttle off)`,
  }));

if (failures > 0) {
  console.error(`${failures} check(s) FAILED`);
  process.exit(1);
}
console.log('All throttle sanity checks passed.');
