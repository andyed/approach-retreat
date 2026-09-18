// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { ApproachRetreat } from '../../src/approach-retreat.js';
import { createPostHogAdapter } from '../../src/adapters/posthog.js';

// Wiring test for the `deferredScoreModel` constructor option: with it set,
// approached-result summaries (getApproachFeatures() rows and each
// finalized episode) gain deferred_score/deferred_score_model; without it,
// the keys are absent entirely (not present-as-null). Also exercises the
// PostHog adapter's ar_deferred_score_mean / ar_deferred_score_by_position
// aggregates and the per-episode ar_deferred_score field.
//
// Reuses the happy-dom fake-observer setup from
// tests/integration/demo-emission.test.js (kept local/minimal rather than
// shared, to stay independent of that suite's fixtures).

const HERE = dirname(fileURLToPath(import.meta.url));
const MODEL_V2 = JSON.parse(
  readFileSync(
    join(HERE, '..', '..', 'scripts', 'models', 'm5_cursor_only_v2.json'),
    'utf8'
  )
);

let clock;

function installFakes() {
  clock = 1000;
  vi.stubGlobal('performance', { now: () => clock });

  class FakeIntersectionObserver {
    constructor(cb) {
      this._cb = cb;
    }
    observe(el) {
      this._cb([{ target: el, isIntersecting: true, intersectionRatio: 1 }]);
    }
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  }
  vi.stubGlobal('IntersectionObserver', FakeIntersectionObserver);

  class FakeResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal('ResizeObserver', FakeResizeObserver);

  vi.stubGlobal('requestAnimationFrame', () => 0);
  vi.stubGlobal('cancelAnimationFrame', () => {});
}

function tick(ms) {
  clock += ms;
}

function renderResultRows(n) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const rows = [];
  for (let i = 0; i < n; i++) {
    const row = document.createElement('div');
    row.dataset.result = '';
    row.dataset.position = String(i);
    container.appendChild(row);

    const top = 100 + i * 120;
    const rect = {
      left: 0,
      right: 800,
      top,
      bottom: top + 100,
      width: 800,
      height: 100,
      x: 0,
      y: top,
    };
    row.getBoundingClientRect = () => rect;
    rows.push(row);
  }
  return rows;
}

function moveTo(x, y) {
  document.dispatchEvent(
    new window.MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true })
  );
}

// Drive the cursor through and past result 0 so its tracker accumulates
// enough samples for min_dist/mean_dist/etc. to be well-defined, then leave
// so the episode finalizes.
function driveResult0() {
  moveTo(400, 130); // approach
  tick(60);
  moveTo(400, 150); // enter/dwell near center (rows[0] spans 100..200)
  tick(60);
  moveTo(400, 170);
  tick(60);
  moveTo(400, 5000); // leave -> exits, retreat window will graduate on flush
}

beforeEach(() => {
  installFakes();
  document.body.innerHTML = '';
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('deferredScoreModel — ApproachRetreat wiring', () => {
  it('omits deferred_score entirely when the option is not set', () => {
    renderResultRows(2);
    const ar = new ApproachRetreat({ resultSelector: '[data-result]' });
    ar.refresh();

    driveResult0();
    ar.flush();

    const features = ar.getApproachFeatures();
    const row0 = features.find((f) => f.position === 0);
    expect(row0).toBeTruthy();
    expect('deferred_score' in row0).toBe(false);
    expect('deferred_score_model' in row0).toBe(false);

    const episodes = ar.getEpisodes();
    expect(episodes.length).toBeGreaterThan(0);
    expect('deferred_score' in episodes[0]).toBe(false);
    expect('deferred_score_model' in episodes[0]).toBe(false);
  });

  it('attaches a numeric-or-null deferred_score when the option is set', () => {
    renderResultRows(2);
    const ar = new ApproachRetreat({
      resultSelector: '[data-result]',
      deferredScoreModel: MODEL_V2,
    });
    ar.refresh();

    driveResult0();
    ar.flush();

    const features = ar.getApproachFeatures();
    const row0 = features.find((f) => f.position === 0);
    expect(row0).toBeTruthy();
    expect('deferred_score' in row0).toBe(true);
    expect(row0.deferred_score === null || typeof row0.deferred_score === 'number').toBe(true);
    if (typeof row0.deferred_score === 'number') {
      expect(row0.deferred_score).toBeGreaterThanOrEqual(0);
      expect(row0.deferred_score).toBeLessThanOrEqual(1);
    }
    expect(row0.deferred_score_model).toBe('export_m5_cursor_only.py');

    const episodes = ar.getEpisodes();
    expect(episodes.length).toBeGreaterThan(0);
    const ep0 = episodes.find((e) => e.position === 0);
    expect('deferred_score' in ep0).toBe(true);
    expect(ep0.deferred_score_model).toBe('export_m5_cursor_only.py');
  });

  it('does not touch the observed Outcome / four-class classification', () => {
    renderResultRows(2);
    const withoutModel = new ApproachRetreat({ resultSelector: '[data-result]' });
    withoutModel.refresh();
    driveResult0();
    withoutModel.flush();
    const classesWithout = withoutModel.classify();

    document.body.innerHTML = '';
    renderResultRows(2);
    clock = 1000;
    const withModel = new ApproachRetreat({
      resultSelector: '[data-result]',
      deferredScoreModel: MODEL_V2,
    });
    withModel.refresh();
    driveResult0();
    withModel.flush();
    const classesWith = withModel.classify();

    const outcomeCounts = (classes) =>
      Object.fromEntries(
        Object.entries(classes).map(([k, v]) => [k, v.length])
      );
    expect(outcomeCounts(classesWith)).toEqual(outcomeCounts(classesWithout));
  });
});

describe('deferredScoreModel — PostHog adapter aggregates', () => {
  it('emits ar_deferred_score on ar_episode and ar_deferred_score_mean / ar_deferred_score_by_position on ar_session_summary', () => {
    renderResultRows(2);
    const capture = vi.fn();
    const adapter = createPostHogAdapter({ capture }, {});
    const ar = new ApproachRetreat({
      resultSelector: '[data-result]',
      deferredScoreModel: MODEL_V2,
      onEpisode: adapter.onEpisode,
      onClick: adapter.onClick,
    });
    ar.refresh();

    driveResult0();
    adapter.captureSummary(ar);

    const episodeCall = capture.mock.calls.find((c) => c[0] === 'ar_episode');
    expect(episodeCall).toBeTruthy();
    expect('ar_deferred_score' in episodeCall[1]).toBe(true);

    const summaryCall = capture.mock.calls.find(
      (c) => c[0] === 'ar_session_summary'
    );
    expect(summaryCall).toBeTruthy();
    const summary = summaryCall[1];
    expect(
      summary.ar_deferred_score_mean === null ||
        typeof summary.ar_deferred_score_mean === 'number'
    ).toBe(true);
    expect(typeof summary.ar_deferred_score_by_position).toBe('object');
  });

  it('guards the aggregates against empty input (no approached results)', () => {
    renderResultRows(2); // rendered but never approached by the cursor
    const capture = vi.fn();
    const adapter = createPostHogAdapter({ capture }, {});
    const ar = new ApproachRetreat({
      resultSelector: '[data-result]',
      deferredScoreModel: MODEL_V2,
      onEpisode: adapter.onEpisode,
      onClick: adapter.onClick,
    });
    ar.refresh();

    adapter.captureSummary(ar); // no cursor movement at all

    const summary = capture.mock.calls.find(
      (c) => c[0] === 'ar_session_summary'
    )[1];
    expect(summary.ar_deferred_score_mean).toBe(null);
    expect(summary.ar_deferred_score_by_position).toEqual({});
  });
});
