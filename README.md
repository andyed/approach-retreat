# Approach/Retreat

Drop-in cursor + viewport instrumentation for ranked-list pages — search
result pages, recommendation feeds, comparison tables, product grids. Two
channels:

1. **Approach-retreat episodes** — per-result enter / dwell / exit behaviour
   from cursor telemetry. Classified into a four-class taxonomy (clicked /
   deferred / evaluated-rejected / not-approached). Desktop-only.
2. **Viewport dynamics** — per-AOI session-level measurement of how each
   result sits in, and moves through, the viewport. Cursor-free; works
   wherever scroll events + DOM bounding boxes are available, including
   mobile and feed surfaces.

Sister library to [ClickSense](https://github.com/andyed/clicksense). For
the research backing — task model, four-class taxonomy derivation,
validation against AdSERP and ACD — see
[`docs/research.md`](docs/research.md).

## See it in action

Three AdSERP trials replayed against the original screenshots with
four-class taxonomy labels inferred from cursor episodes alone (no eye
tracker at inference time):

<table>
<tr>
<td align="center" valign="middle"><a href="https://andyed.github.io/approach-retreat/replay/trials/p006-b4-t7.html"><img src="site/assets/hero/p006-b4-t7_tilt.png" alt="Canonical rejected — DEF 9 / REJ 4" width="300"/></a><br/><sub><b>Canonical rejected</b><br/>DEF 9 · REJ 4</sub></td>
<td align="center" valign="middle"><a href="https://andyed.github.io/approach-retreat/replay/trials/p047-b6-t1.html"><img src="site/assets/hero/p047-b6-t1_tilt.png" alt="Multi-AOI drama — CLK 1 / DEF 9 / REJ 1 / NA 4" width="440"/></a><br/><sub><b>Multi-AOI drama</b><br/>CLK 1 · DEF 9 · REJ 1 · NA 4</sub></td>
<td align="center" valign="middle"><a href="https://andyed.github.io/approach-retreat/replay/trials/p019-b1-t8.html"><img src="site/assets/hero/p019-b1-t8_tilt.png" alt="Canonical deferred — DEF 11" width="300"/></a><br/><sub><b>Canonical deferred</b><br/>DEF 11 · REJ 1</sub></td>
</tr>
</table>

Backgrounds are raw AdSERP screenshots — what the participant saw, pixel
for pixel. Boxes are AOIs; labels are this library's output, computed from
the cursor stream alone. Full replay index:
[andyed.github.io/approach-retreat/replay/](https://andyed.github.io/approach-retreat/replay/) —
86 curated trials.

The companion viewer at
[andyed.github.io/attentional-foraging/](https://andyed.github.io/attentional-foraging/)
renders the same trials through a foveated-perception simulator (showing
what the participant could *resolve* at each fixation). Different view of
the same data.

---

## Install

```bash
npm install andyed/approach-retreat
```

Or via script tag:

```html
<script src="dist/approach-retreat.js"></script>
```

## Quick start

```js
import { ApproachRetreat } from 'approach-retreat';

const ar = new ApproachRetreat({
  resultSelector: '[data-result]',
  onEpisode: (episode) => console.log(episode),
  onClick: ({ position, episode }) => {
    console.log(`Clicked position ${position} after ${episode.dwell_ms}ms`);
  },
});
```

Mark your results:

```html
<div data-result data-position="0">
  <h3>Result title</h3>
  <p>Snippet text...</p>
</div>
```

### Tag the surface type with `data-etype` (recommended)

If your SERP mixes ads and organics in the result column, tag each so your
dashboard can slice ad-vs-organic behaviour:

```html
<div data-result data-position="0" data-etype="dd_top">...</div>
<div data-result data-position="1" data-etype="organic">...</div>
<div data-result data-position="2" data-etype="native_ad">...</div>
```

Conventional values: `organic` (first-class result), `dd_top` (top-of-page
ad carousel cell), `native_ad` (inline-text ad). Any `data-*` attribute is
passed through to PostHog as `target_data_<key>`. The library is
etype-agnostic at the machinery level — what you give up by going
untagged is dashboard-level slicing, not capture.

## What the library emits

### Episode (cursor channel)

Every completed visit to a result emits a 23-field episode from
`Episode.toJSON()` (19 cursor fields + 4 banded-viewport fields, the
latter null when `trackViewportBands: false`).

```js
{
  // --- Identity + outcome ---
  position: 2,
  outcome: 'deferred',          // clicked | deferred | evaluated_rejected | not_approached
  visited: true,
  clicked: false,
  retreated: true,
  visit_number: 2,              // 1 = first visit, 2+ = re-approach

  // --- Timing (ms, performance.now() base) ---
  dwell_ms: 847,
  entered_at: 1412.38,
  exited_at: 2259.77,
  clicked_at: null,

  // --- Cursor dynamics ---
  approach_velocity: 0.34,      // px/ms at entry
  approach_angle: 1.21,         // radians, atan2(vy, vx) at entry
  peak_velocity: 0.89,
  min_velocity: 0.02,
  retreat_distance: 186,        // px from AOI center at max retreat
  sample_count: 51,

  // --- Scroll context ---
  direction: 'forward',         // forward | regressive
  entry_scroll: 420,
  hwm_at_entry: 420,
}
```

#### Raw trajectory (opt-in)

Set `includeSamplesInEpisodeJson: true` to add a `samples` array (one
`{x,y,t,vx,vy}` per native mousemove sample, ~60 Hz). Research-grade
material — keep it local unless you're shipping it through the PostHog
adapter.

### Viewport analytics (cursor-free channel)

One record per AOI per session, computed from scroll events plus DOM
bounding boxes alone. Runs anywhere `scroll` is logged.

```js
ar.getViewportAnalytics();
// [{
//   position: 0,
//   // Impression (MRC/IAB)
//   iab_viewable: true,            // ≥ 50% pixels visible for ≥ 1s continuous
//   ms_at_50pct_or_more: 2400,
//   // Residence (continuous)
//   vt_any_ms: 6200,
//   vt_center_ms: 1800,
//   avg_viewport_y_px: 340,
//   max_overlap_frac: 1.0,
//   // Kinematics (scroll trajectory while visible)
//   min_abs_velocity_px_per_s: 0,
//   n_reversals: 2,
// }, ...]
```

| Tier | Field | Meaning |
|---|---|---|
| Impression (MRC/IAB) | `iab_viewable` | True iff ≥ 50% pixel overlap held for ≥ 1 continuous second. Display rule. |
| Impression | `ms_at_50pct_or_more` | Cumulative ms at ≥ 50% overlap, no continuity constraint. |
| Residence | `vt_any_ms` | Cumulative ms with any viewport overlap. "Did the user ever see it?" |
| Residence | `vt_center_ms` | Cumulative ms with AOI center within ±100 px of viewport center. |
| Residence | `avg_viewport_y_px` | Mean AOI-center viewport-y during visibility. |
| Impression / peak | `max_overlap_frac` | Peak fraction visible. 1.0 = fully in view at some point. |
| Kinematics | `min_abs_velocity_px_per_s` | Slowest scroll speed while AOI was visible. Stabilization marker. |
| Kinematics | `n_reversals` | Scroll-direction reversals while AOI was visible. EWM-reload signal. |

**Banded decomposition** (`vp_top_ms` / `vp_mid_ms` / `vp_bot_ms`) is also
available via `ar.getViewportBands()` — retained for dashboard heatmaps;
adds no detectable AUC on top of the continuous six (see research index
for sourcing).

**Config:** `trackViewportAnalytics` (default `true`),
`viewportCenterTolPx` (default 100), `iabViewableThresholdMs` (default
1000 for the MRC display rule; set 2000 for video).

### Library-side classification + signals

```js
ar.classify();
// { clicked: [{position, ...}], deferred: [...],
//   evaluated_rejected: [...], not_approached: [...] }

ar.getSignals();
// [{ position, outcome, total_dwell_ms, mean_retreat_distance, ... }, ...]

ar.getEpisodes();   // full list, one entry per finalized visit
ar.flush();         // finalize in-flight episodes without clearing history
```

### Canonical seven-feature M4-7 vector

`ar.getApproachFeatures()` emits the canonical feature vector consumed by
the click-prediction (M3) and deferred-class (M5) classifiers. One vector
per result position per session. The Edmonds 2026 CIKM paper companion
documents the click-buffer leakage screen that distinguishes the seven
buffer-robust features from `final_dist` and `retreat_dist` — see
[`docs/research.md`](docs/research.md) for the deployment caveat.

```js
ar.getApproachFeatures();
// [
//   { position: 0,
//     min_dist: 2.0,
//     mean_dist: 143.15,
//     dwell_in_proximity_ms: 466,
//     mean_approach_velocity: 238,
//     max_approach_velocity: 966,
//     direction_changes: 11,
//     frac_decreasing: 0.62,
//     // Caveat fields — see research index
//     final_dist: 200.0,
//     retreat_dist: 198.0,
//     sample_count: 64 },
//   { position: 1, ... },
// ]
```

## Sending events to your analytics

### PostHog adapter (bundled)

Three event types, all `ar_`-prefixed:

| Event | Fires on | Key fields |
|---|---|---|
| `ar_episode` | every finalized episode | the 19 cursor fields + optional `ar_trajectory` (10% sample rate by default) |
| `ar_click` | every click on a result | pre-click velocity, angle, direction, retreat distance, dwell |
| `ar_session_summary` | `visibilitychange` / `pagehide` | four-class counts, positions per class, time-to-first-click |

Every event is merged with session context: `ar_session_id`, `ar_layout`,
`ar_query_id`, viewport (`w`, `h`, `dpr`), UA, referrer, page path.

**Kill switch.** Append `?ph=0` to any URL to skip PostHog entirely.

`ar_click` carries the ClickSense v0.2 target vocabulary —
`target_tag` / `target_id` / `target_label` / `target_href` /
`target_text` / `target_aria_label` / `target_title` / `target_name` /
`target_path` / `target_data_<key>` — so you can JOIN
`click_confidence ↔ ar_click` on `target_href` or `target_name` when both
libraries run on the same page.

### Other adapters

- `approach-retreat/adapters/posthog` — PostHog event flattening.
- `approach-retreat/adapters/callback` — buffer + flush (`sendBeacon`,
  custom transport).

## Composing with ClickSense

Both libraries run on the same page without conflict. ClickSense
captures the commitment moment (per-click confidence); approach-retreat
captures the evaluation phase that precedes it.

```js
import { ClickSense } from 'clicksense';
import { ApproachRetreat } from 'approach-retreat';

const cs = new ClickSense({ enableApproachDynamics: true, onCapture: ... });
const ar = new ApproachRetreat({ resultSelector: '[data-result]', onEpisode: ... });
```

## Relevance scoring

```js
const scores = ar.computeRelevance();
// [{ position: 0, score: 0.72, signals: {...} }, ...]
```

Default weights: dwell time (40%), re-approaches (30%), clicks (30%),
small penalty for repeated retreats. The four-class taxonomy maps cleanly
onto the (0/1/2) graded-relevance vocabulary that learning-to-rank
consumes natively (clicked = 2, deferred = 1, evaluated-rejected = 0;
not-approached excluded as no-evidence).

## Live experiment

The [gh-pages site](https://andyed.github.io/approach-retreat/) runs the
library across five layout variants × four Q&A SERPs (20 bookmarkable
combinations). Same library contract, same episode schema across all of
them — the layout is the variable, the instrumentation is the constant.

Telemetry is live. Press `d` on any SERP page for the in-page debug
overlay. Append `?ph=0` to disable capture.

## Privacy

The library captures cursor + scroll events that the page's own
JavaScript already has access to — no new permissions. Raw trajectory
samples are opt-in (`includeSamplesInEpisodeJson: true`); without that
flag, only aggregate-per-episode statistics leave the browser.

For deployment-grade privacy posture (consent, retention, opt-out):
follow your existing PostHog (or other analytics) configuration. The
library does not introduce a new data plane; it adds events to the one
you already operate.

For a published treatment of the same telemetry primitives' privacy
implications, see Leiva, Arapakis & Iordanou. "My Mouse, My Rules"
(CHIIR 2021).

---

## For researchers

The library is the runnable form of the cognitive task model in the
forthcoming CIKM 2026 paper. The full research index — task model
derivation, four-class taxonomy validation, click-buffer leakage screen,
LAB / WILD numbers with provenance, foundation-model rebuttal, and the
Leiva/Arapakis lineage — lives at
**[`docs/research.md`](docs/research.md)**.

Ancillary docs:

- [`docs/theory.md`](docs/theory.md) — concise theoretical writeup.
- [`docs/one-pager.md`](docs/one-pager.md) — task model vs 638-feature bag,
  four-class taxonomy, retreat geometry as deliberation indicator.
- [`docs/positioning.md`](docs/positioning.md) — four-lane map of related
  work.
- [`docs/history.md`](docs/history.md) — Lucidity 2001 → Optimoz 2001 →
  Uzilla 2003 → ClickSense 2026 → approach-retreat 2026 lineage with
  Slashdot front-page screenshot.
- [`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md) —
  public head-to-head against Brückner, Arapakis & Leiva (SIGIR 2021).
  Approach-retreat features beat the scalar mouse-length baseline by
  +12.5 AUC (0.821 vs 0.696) on their own ad-click-prediction benchmark.
- [`docs/validation/m5-calibration.md`](docs/validation/m5-calibration.md) —
  end-to-end calibration methodology for the deferred-class detector.
- [`docs/validation/viewport-bands-calibration.md`](docs/validation/viewport-bands-calibration.md) —
  bootstrap protocol for the retreat + bands AUC.
- [`docs/validation/feature-ablation-cross-stage.md`](docs/validation/feature-ablation-cross-stage.md) —
  full LOFO + group ablation matrix across CIKM paper's four modeling
  stages (click classifier, deferred classifier, three LambdaMART
  rankers). The cross-stage view the paper §4.1/§4.3/§4.6 paragraphs
  imply but couldn't fit in page budget.

> **AllSERP companion paper.** *AllSERP: Exhaustive Per-Element Enrichment
> of the Versatile AdSERP Dataset* — [arXiv:2605.04949](https://arxiv.org/abs/2605.04949)
> (2026). Documents the typed AOI extraction used here for AOI labels in
> the replay viewer. Local PDF: [`allserp-paper.pdf`](./allserp-paper.pdf).

## License

MIT
