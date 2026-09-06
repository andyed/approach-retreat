// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { ApproachRetreat } from '../../src/approach-retreat.js';
import {
  createPostHogAdapter,
  buildSessionContext,
  isPostHogDisabled,
} from '../../src/adapters/posthog.js';

// End-to-end emission test for the AR demo telemetry path. This is the guard
// the production "ar_* events went silent" episode motivates: it drives a
// synthetic cursor over a rendered SERP and asserts ar_episode / ar_click /
// ar_session_summary actually reach posthog.capture — and that the known
// silent-failure modes (no window.posthog, broken [data-result] contract)
// behave as expected rather than throwing or pretending to work.
//
// Runs in happy-dom. Two headless gaps are bridged: getBoundingClientRect
// returns zeros (we stub per-element rects) and there is no Intersection
// /ResizeObserver (we fake them). performance.now() is a controllable clock so
// dwell and the 15 Hz sample throttle are deterministic.

const HERE = dirname(fileURLToPath(import.meta.url));

let clock;

function installFakes() {
  clock = 1000;
  vi.stubGlobal('performance', { now: () => clock });

  // The library gates AOI hit-testing on _visibleResults, populated by an
  // IntersectionObserver. Mark every observed element visible synchronously so
  // a headless cursor can enter results.
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

  // Viewport-band snapshots schedule via rAF; we don't assert bands here, and a
  // no-op avoids re-entrant snapshotting under the controllable clock.
  vi.stubGlobal('requestAnimationFrame', () => 0);
  vi.stubGlobal('cancelAnimationFrame', () => {});
}

function tick(ms) {
  clock += ms;
}

/**
 * Build the SERP DOM contract the library depends on: [data-result] +
 * [data-position], each with a fixed headless rect (rows 100px tall, stacked
 * from y=100 with 20px gaps). Returns the row elements.
 */
function renderResultRows(n) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const rows = [];
  for (let i = 0; i < n; i++) {
    const row = document.createElement('div');
    row.dataset.result = '';
    row.dataset.position = String(i);
    const link = document.createElement('a');
    link.setAttribute('data-clicksense', `result-${i}`);
    link.href = `https://example.com/r/${i}`;
    link.textContent = `Result ${i}`;
    row.appendChild(link);
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
    link.getBoundingClientRect = () => rect;
    rows.push(row);
  }
  return rows;
}

function moveTo(x, y) {
  document.dispatchEvent(
    new window.MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true })
  );
}

function clickOn(el, x, y) {
  el.dispatchEvent(
    new window.MouseEvent('click', { clientX: x, clientY: y, bubbles: true })
  );
}

/**
 * Mirror of site/js/ar-init.js#initApproachRetreat, wired against src/ so the
 * test exercises the real emission semantics without depending on a dist
 * build. Keep in sync with the demo wiring.
 */
function wireDemo(posthog, layoutName = 'narrow-vertical') {
  const adapter = createPostHogAdapter(posthog, {
    context: buildSessionContext({ ar_layout: layoutName, ar_query_id: 'test-q' }),
    disabled: isPostHogDisabled() || !posthog,
  });
  const ar = new ApproachRetreat({
    resultSelector: '[data-result]',
    onEpisode: adapter.onEpisode,
    onClick: adapter.onClick,
  });
  adapter.bind(ar);
  ar.refresh();
  return { ar, adapter };
}

beforeEach(() => {
  installFakes();
  document.body.innerHTML = '';
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('AR demo — telemetry emission (the silent-listener guard)', () => {
  it('fires ar_episode, ar_click, and ar_session_summary from a driven cursor', () => {
    const capture = vi.fn();
    const rows = renderResultRows(3);
    const { ar, adapter } = wireDemo({ capture });

    // Enter result 0 (y in 100..200), dwell past minDwellMs (100), click, leave.
    moveTo(400, 150); // t=1000 — enter result 0
    tick(120);
    moveTo(400, 150); // t=1120 — sample; dwell ~120ms
    tick(40);
    clickOn(rows[0].querySelector('a'), 400, 150); // t=1160 — click while active
    tick(140);
    moveTo(400, 5000); // t=1300 — leave all AOIs → clicked episode finalizes

    adapter.captureSummary(ar); // flush + summary

    const names = capture.mock.calls.map((c) => c[0]);
    expect(names).toContain('ar_episode');
    expect(names).toContain('ar_click');
    expect(names).toContain('ar_session_summary');
  });

  it('emits faithful payloads with version stamp and session context merged', () => {
    const capture = vi.fn();
    const rows = renderResultRows(3);
    const { ar, adapter } = wireDemo({ capture }, 'wide-two-pane');

    moveTo(400, 150);
    tick(120);
    moveTo(400, 150);
    tick(40);
    clickOn(rows[0].querySelector('a'), 400, 150);
    tick(140);
    moveTo(400, 5000);
    adapter.captureSummary(ar);

    const byName = (n) => capture.mock.calls.find((c) => c[0] === n)?.[1];

    const ep = byName('ar_episode');
    expect(ep.ar_position).toBe(0);
    expect(ep.ar_outcome).toBe('clicked');
    expect(ep.ar_clicked).toBe(true);
    expect(ep.ar_dwell_ms).toBeGreaterThanOrEqual(100);
    expect(ep.approach_retreat_version).toBeTruthy(); // version stamp on every event
    expect(ep.ar_layout).toBe('wide-two-pane'); // session context merged
    expect(ep.ar_session_id).toBeTruthy();

    const ck = byName('ar_click');
    expect(ck.ar_position).toBe(0);
    expect(ck.target_href).toBe('https://example.com/r/0'); // clicksense-aligned target field
    expect(ck.ar_layout).toBe('wide-two-pane');

    const sum = byName('ar_session_summary');
    expect(sum.ar_total_episodes).toBeGreaterThanOrEqual(1);
    expect(sum.ar_total_clicked).toBe(1);
    expect(Array.isArray(sum.ar_approach_features)).toBe(true);
  });

  it('captureSummary is idempotent (explicit call + bind both wired)', () => {
    const capture = vi.fn();
    renderResultRows(2);
    const { ar, adapter } = wireDemo({ capture });

    moveTo(400, 150);
    tick(150);
    moveTo(400, 5000);

    adapter.captureSummary(ar);
    adapter.captureSummary(ar); // second call must be a no-op

    const summaries = capture.mock.calls.filter((c) => c[0] === 'ar_session_summary');
    expect(summaries.length).toBe(1);
  });

  it('is a silent no-op when window.posthog is absent (the Jun-10 silence signature)', () => {
    renderResultRows(3);
    // Adblock / blocked CDN / CSP → window.posthog never defined. The demo
    // wiring disables the adapter (disabled: ... || !posthog), so nothing is
    // captured and nothing throws. Documenting this is the point: a missing
    // analytics global fails silent, which is exactly how the listener can go
    // dark without an error in the console.
    const { ar, adapter } = wireDemo(undefined);
    expect(adapter._disabled).toBe(true);

    expect(() => {
      moveTo(400, 150);
      tick(150);
      moveTo(400, 5000);
      adapter.captureSummary(ar);
    }).not.toThrow();
  });

  it('emits no ar_episode when results lack the [data-result] contract', () => {
    const capture = vi.fn();
    // Render rows WITHOUT data-result (e.g. a renderAnswers regression that
    // drops the attribute). The library finds zero AOIs → zero episodes, yet
    // the session summary still fires: episodes silently vanish while the
    // pipeline looks alive. This is the other silent-listener signature.
    const container = document.createElement('div');
    document.body.appendChild(container);
    for (let i = 0; i < 3; i++) {
      const d = document.createElement('div');
      d.dataset.position = String(i); // position but NO data-result
      const top = 100 + i * 120;
      d.getBoundingClientRect = () => ({
        left: 0,
        right: 800,
        top,
        bottom: top + 100,
        width: 800,
        height: 100,
        x: 0,
        y: top,
      });
      container.appendChild(d);
    }
    const { ar, adapter } = wireDemo({ capture });

    moveTo(400, 150);
    tick(150);
    moveTo(400, 5000);
    adapter.captureSummary(ar);

    const names = capture.mock.calls.map((c) => c[0]);
    expect(names).not.toContain('ar_episode');
    expect(names).toContain('ar_session_summary');
    const sum = capture.mock.calls.find((c) => c[0] === 'ar_session_summary')[1];
    expect(sum.ar_total_episodes).toBe(0);
  });
});

// Opportunistic smoke test against the REAL demo module (site/js/ar-init.js),
// which imports the bundled site/dist/. That mirror is gitignored and only
// exists after `npm run build`, so this block skips cleanly when it is absent.
const distReady = existsSync(
  join(HERE, '..', '..', 'site', 'dist', 'approach-retreat.esm.js')
);

describe.skipIf(!distReady)(
  'AR demo — real site/js/ar-init.js module (requires `npm run build`)',
  () => {
    it('renderAnswers emits the [data-result] / [data-position] contract', async () => {
      const { renderAnswers } = await import('../../site/js/ar-init.js');
      const container = document.createElement('div');
      document.body.appendChild(container);
      renderAnswers(container, [
        {
          position: 0,
          type: 'answer',
          title: 'A',
          author: 'x',
          author_bio: 'b',
          snippet: 's',
          full_text: 'f',
          year: 2020,
          upvotes: 1,
        },
        { position: 1, type: 'ad', title: 'Ad', author_bio: 'sp', snippet: 's' },
      ]);
      const resultRows = container.querySelectorAll('[data-result]');
      expect(resultRows.length).toBe(2);
      resultRows.forEach((r) =>
        expect(r.getAttribute('data-position')).not.toBeNull()
      );
    });

    it('initApproachRetreat returns a live (non-disabled) adapter when posthog is present', async () => {
      const { renderAnswers, initApproachRetreat } = await import(
        '../../site/js/ar-init.js'
      );
      window.posthog = { capture: vi.fn() };
      const container = document.createElement('div');
      document.body.appendChild(container);
      renderAnswers(container, [
        { position: 0, type: 'answer', title: 'A', snippet: 's', full_text: 'f' },
      ]);

      const { ar, adapter } = initApproachRetreat({
        layoutName: 'narrow-vertical',
        queryMeta: { id: 'q' },
      });
      expect(adapter._disabled).not.toBe(true);
      expect(typeof ar.getEpisodes).toBe('function');

      delete window.posthog;
    });
  }
);
