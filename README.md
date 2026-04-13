# Approach/Retreat

Cursor approach-retreat dynamics on **ranked list layouts** (search result pages, recommendation feeds, comparison tables). Sister library to [ClickSense](https://github.com/andyed/clicksense).

*Current iteration of a cursor-instrumentation line that began with the Optimoz Firefox gesture extension (2001) and Uzilla (2003) — see [Precedents](#precedents-2001-2003) below and [`docs/history.md`](docs/history.md) for the full lineage.*

## The idea

Before you click a search result, your cursor tells a story. It approaches a result (interest), dwells over it (evaluation), then either commits (click) or retreats. After the retreat, two distinct cursor signatures distinguish results the user is done with from results they may come back to: **deferred** users park the cursor while their eyes wander to alternatives (high post-closest-approach drift, long gaze and proximity dwells), then eventually scroll back; **evaluated-rejected** users move the cursor on with their eyes (low post-closest drift, short dwells) and never return. The motor-signature dissociation is sharp — *p* = 1.76 × 10⁻³⁸ on post-closest drift, *p* = 9.76 × 10⁻⁷⁰ on gaze dwell — see [`docs/theory.md`](docs/theory.md) for the full table and the corrected geometric interpretation.

### How this differs from ClickSense

**ClickSense** instruments approach + click dynamics on arbitrary clickable elements (buttons, cards, links) — vendor-agnostic motor confidence across any layout. The signal is per-click: approach velocity, hold duration, trajectory shape.

**Approach/Retreat** is SERP-specific. It models the evaluation phase across a *list* of ranked candidates, tracking enter/dwell/exit episodes at each position and classifying them into a four-class taxonomy (clicked / deferred / evaluated-rejected / not-approached). The signal is per-SERP: which results were considered, which were skipped, and which were kept in reserve.

Both libraries compose — a page can run both. ClickSense sees each click as a moment; approach-retreat sees the whole page of decisions leading up to it.

### Signals

| Signal | What it means |
|--------|---------------|
| **Approach velocity** | Fast = scanning. Slow = evaluating. |
| **Dwell time** | Time cursor spends over a result's bounding box |
| **Retreat** | Cursor leaves without clicking — rejection or deferral |
| **Retreat distance** | How far the cursor moves away — far retreats predict commitment to rejection (no return), close retreats predict re-approach |
| **Arc ratio** | Path length / direct distance — curved retreats (arc ratio > 1.5) predict re-approach |
| **Re-approach** | Cursor returns to a previously visited result — reconsideration |
| **Commitment depth** | How far down the SERP before first click |

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

Mark your SERP results:

```html
<div data-result data-position="0">
  <h3>Result title</h3>
  <p>Snippet text...</p>
</div>
<div data-result data-position="1">
  <h3>Another result</h3>
  <p>More snippet text...</p>
</div>
```

## Episode data

Every completed cursor visit to a result produces a 19-field episode from `Episode.toJSON()`. Grouped by purpose:

```js
{
  // --- Identity + outcome ---
  position: 2,                    // rank in the SERP (from data-position)
  outcome: 'deferred',            // four-class: clicked | deferred | evaluated_rejected | not_approached
  visited: true,                  // always true for emitted episodes
  clicked: false,
  retreated: true,
  visit_number: 2,                // 1 = first visit, 2+ = re-approach

  // --- Timing (all ms, performance.now() base) ---
  dwell_ms: 847,                  // total time cursor was over the AOI
  entered_at: 1412.38,            // when cursor crossed into the AOI
  exited_at: 2259.77,             // when cursor left the AOI
  clicked_at: null,               // populated only when the visit ended in a click

  // --- Cursor dynamics ---
  approach_velocity: 0.34,        // px/ms at the moment of entry
  approach_angle: 1.21,           // radians, atan2(vy, vx) at entry
  peak_velocity: 0.89,             // max speed while over the result
  min_velocity: 0.02,              // min speed while over — near-pause = reading
  retreat_distance: 186,           // px from AOI center at max retreat (0 if clicked)
  sample_count: 51,                // number of raw mousemove samples captured

  // --- Scroll context (forward/regressive split) ---
  direction: 'forward',            // 'forward' = at/near scroll HWM, 'regressive' = scrolled back up
  entry_scroll: 420,               // window.scrollY at entry
  hwm_at_entry: 420,               // running max of scrollY at entry
}
```

### Raw trajectory (opt-in)

Set `includeSamplesInEpisodeJson: true` on the library to add a `samples` array to each episode. Every sample is `{ x, y, t, vx, vy }` at the native mousemove rate (typically 60Hz). This is research-grade material — keep it local unless you're shipping it to an instrumented adapter like PostHog (see below).

```js
const ar = new ApproachRetreat({
  resultSelector: '[data-result]',
  includeSamplesInEpisodeJson: true,
  onEpisode: (ep) => saveForAnalysis(ep),
});
```

### PostHog capture shape

The bundled PostHog adapter (`adapters/posthog.js`) ships three event types, all prefixed `ar_`:

| Event | Fires on | Key fields |
|---|---|---|
| `ar_episode` | every finalized episode | all 19 fields above + optional `ar_trajectory` (flat `[x,y,t_rel_ms,vx,vy,...]` array, 10% sample rate by default) |
| `ar_click` | every click on a result | pre-click velocity, angle, direction, retreat distance, dwell before click |
| `ar_session_summary` | `visibilitychange` / `pagehide` | four-class taxonomy counts, positions per class, forward/regressive counts, time-to-first-click, max position approached |

Every event is merged with a session context: `ar_session_id`, `ar_layout`, `ar_query_id`, viewport (`w`, `h`, `dpr`), UA, referrer, page path, load time.

Dev kill-switch: append `?ph=0` to any URL to skip PostHog entirely.

### Library-side classification

```js
ar.classify();
// { clicked: [{position, ...}], deferred: [...],
//   evaluated_rejected: [...], not_approached: [...] }

ar.getSignals();
// [{ position, outcome, total_dwell_ms, mean_retreat_distance,
//    visit_count, retreat_count, reapproach_count, ... }, ...]

ar.getEpisodes();  // full list, one entry per finalized visit
ar.flush();        // finalize in-flight episodes without clearing history
```

## Relevance scoring

```js
const scores = ar.computeRelevance();
// [{ position: 0, score: 0.72, signals: {...} }, ...]
```

Weights: dwell time (40%), re-approaches (30%), clicks (30%), with a small penalty for repeated retreats.

## Using with ClickSense

Both libraries work on the same page. ApproachRetreat captures the evaluation phase; ClickSense captures the commitment moment.

```js
import { ClickSense } from 'clicksense';
import { ApproachRetreat } from 'approach-retreat';

const cs = new ClickSense({ enableApproachDynamics: true, onCapture: ... });
const ar = new ApproachRetreat({ resultSelector: '[data-result]', onEpisode: ... });
```

## Live experiment

The [gh-pages site](https://andyed.github.io/approach-retreat/) runs the library across **five layout variants** (narrow vertical, wide two-pane, card grid, dense titles-only, rich thumbnail) crossed with **four Q&A SERPs**, producing 20 bookmarkable combinations. Every variant uses the same library contract and emits the same episode schema — the layout is the variable, the instrumentation is the constant.

Each Q&A SERP presents a question with synthetic answers representing a discourse arc over time, plus an injected ad to test discrimination cost (the approach-retreat signature when users identify sponsored content):

| Question | Year range | Flavor |
|---|---|---|
| Will AI be an existential threat to humanity? | 2011–2025 | Technical / philosophical, consensus shift |
| Is The A-Team the dumbest great show ever made? | 1984–2024 | Nostalgic / critical, multi-decade reappraisal |
| Are cats intelligent? | 2011–2025 | Scientific / anecdotal, research drift |
| What was your favorite sunset? | 2013–2024 | Personal / experiential, no consensus to shift |

**Telemetry is live.** Every cursor episode, click, and session summary ships to PostHog via the bundled adapter (same project as the attentional-foraging scanpath viewer). Episodes include the optional 10%-downsampled trajectory as research-grade material. Press `d` on any SERP page to toggle the in-page debug overlay showing episodes, retreats, and the four-class classification. Append `?ph=0` to any URL to disable capture.

## Adapters

- `approach-retreat/adapters/posthog` — PostHog event flattening
- `approach-retreat/adapters/callback` — Buffer + flush (sendBeacon, etc.)

## Background reading

- **[`docs/theory.md`](docs/theory.md)** — Concise theoretical writeup. What the library measures, what the signals mean, the lineage of cursor-on-SERP work, and what we initially proposed but rejected after the data didn't support it.
- **[`docs/one-pager.md`](docs/one-pager.md)** — Why a task model beats a 638-feature bag for SERP cursor analysis. The four-class taxonomy, discrimination cost, retreat geometry as deliberation indicator. Citations to prior work.
- **[`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md)** — Public head-to-head validation against Brückner, Arapakis & Leiva (SIGIR '21) on their own benchmark. Approach-retreat features beat a scalar mouse-length baseline by +12.5 AUC on ad click prediction (0.821 vs 0.696) with a non-learned 11-feature logistic regression. Reproduction pipeline at [`analysis/attcur-validation/`](analysis/attcur-validation/).
- **[`docs/history.md`](docs/history.md)** — How we got here. A personal history of cursor instrumentation from 2001 (Lucidity + the Optimoz gesture extension's real-time cursor-vector compression, Slashdotted and installed by millions) through Uzilla 2003 ("mouse miles" path length + the DOM-path signature) to ClickSense and approach-retreat. Complements the Leiva/Arapakis lineage table below with the other side of the story.

## Related work

This library is the instrumentation half of a two-part research program:

- **Analysis:** [attentional-foraging](https://github.com/andyed/attentional-foraging) — a reanalysis of the AdSERP dataset (Latifzadeh, Gwizdka & Leiva, SIGIR '25; 2,776 trials, 47 participants, simultaneous eye + mouse + scroll + pupil tracking) that produces the OSEC task model and the four-class taxonomy.
- **Deployment:** this library — the task model in runnable form. You get the signal without the eye tracker.

### Precedents (2001–2003)

The modern IR cursor literature did not start in 2012 with Huang et al. Two of its foundational primitives were already codified in the early 2000s, in browser instrumentation work that predates the SIGIR cursor-on-SERP thread by roughly a decade. Approach-retreat is directly descended from both.

| Year | Release | Primitive | Modern re-derivation |
|---|---|---|---|
| **2001** | [Optimoz](http://optimoz.mozdev.org/) — Firefox gesture extension, [Slashdotted](https://www.flickr.com/photos/andyed/125275288/), installed by millions | **Real-time cursor-vector compression** via the gesture-recognition algorithm. Turned cursor-trajectory summarization from a batch lab exercise into something running live in every gesture-enabled Firefox. | **Villaizán-Vallelado et al.** (SIGIR '25) — Seq2Seq Transformer over raw cursor-trajectory embeddings, 24 years later. Same primitive, different decoder. |
| **2003** | **Edmonds.** [*Uzilla: A new tool for Web usability testing*](https://link.springer.com/article/10.3758/BF03202549) (Behavior Research Methods, Instruments, & Computers 35(2):194–201) | **"Mouse miles"** — integrated cursor path length (and its horizontal/vertical decomposition) as a summative usability measure, reported alongside time-on-task and success rate. Used in a 2002 Clemson case study comparing left- vs right-hand navigation on a SERP-like test site. | **Brückner, Arapakis & Leiva** (SIGIR '21) — "When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search." Same primitive, same framing, 18 years later. |

Uzilla also introduced the **DOM-path click signature** — identifying click targets by their full DOM-tree path rather than pixel position. That one is arguably the most widely adopted idea from the paper, silently embedded in most modern web analytics, session-recording, A/B testing, and accessibility tools.

See [`docs/history.md`](docs/history.md) for the full lineage (Lucidity 2001 → Optimoz 2001 → Uzilla 2003 → ClickSense 2026 → approach-retreat 2026) and the Slashdot front-page screenshot. Approach-retreat adds a **task model** on top of these primitives — the four-class taxonomy (clicked / deferred / evaluated_rejected / not_approached) reframes the same cursor primitives as labels rather than features.

### The Leiva/Arapakis research program

The cursor-on-SERP lineage this work builds on runs through a single sustained collaboration — Luis Leiva and Ioannis Arapakis have been producing the foundational datasets, features, and baselines for more than a decade. Approach/retreat is best understood as a task-model layer on top of their instrument.

| Year | Paper | What it contributed |
|---|---|---|
| 2016 | Arapakis & Leiva. ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) (SIGIR) | 638 cursor features → 0.86 AUC attention prediction on Yahoo Knowledge Modules. Established that cursor telemetry alone is strong signal. |
| 2020 | Arapakis, Penta, Joho & Leiva. "A Price-per-attention Auction Scheme Using Mouse Cursor Information" (ACM TOIS) | Cursor-derived attention as an auction-scheme currency — the economic framing that motivates the rest of the program. |
| 2020 | Arapakis & Leiva. "Learning Efficient Representations of Mouse Movements to Predict User Attention" (SIGIR) | Neural-embedding precursor to AdSight — learned representations of cursor trajectories. |
| 2020 | Leiva & Arapakis. ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) (Frontiers) | 2,737 users, cursor + self-reported attention labels + SERP HTML. Largest public cursor-on-SERP dataset. |
| 2021 | Leiva, Arapakis & Iordanou. "My Mouse, My Rules" (CHIIR) | Privacy analysis of the same telemetry primitives — important context for any deployment. |
| 2021 | **Brückner, Arapakis & Leiva.** ["When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search"](https://dl.acm.org/doi/10.1145/3404835.3463011) (SIGIR) | Scalar "mouse movement length" as a relevance signal. **This is the closest published work to approach/retreat — a single-feature version of what the four-class taxonomy decomposes.** |
| 2025 | Latifzadeh, Gwizdka & Leiva. "A Versatile Dataset of Mouse and Eye Movements on Search Engine Results Pages" (SIGIR) | AdSERP: eye + mouse + pupil + ad boundaries on 2,776 trials. The dataset this work is built on. |
| 2025 | Arapakis et al. "AdSight" (SIGIR) | Transformer-based click prediction from cursor + layout. The modern black-box counterpart to the task-model approach here. |

### What approach/retreat adds

Each of the papers above treats cursor behavior as a *signal to decode*. None of them adopt a **task model** for the evaluation phase. The contribution here is specifically the OSEC → four-class decomposition, which turns a 638-feature brute-force problem into a ~6-feature parsimonious one and recovers an interpretable taxonomy (clicked / deferred / evaluated-rejected / not-approached) instead of a scalar score.

### Validation against AdSERP (attentional-foraging)

The four-class taxonomy and retreat geometry claims are validated in the attentional-foraging notebooks:

- **Click prediction (NB21, NB22):** Episode-level features (dwell, retreat distance, arc ratio, visit count) → **AUC 0.859** for click prediction (LOSO M3, post coordinate-space audit 2026-04-12). With element-type interactions (NB22 M3ei): organic **0.859**, top ads **0.919** (+0.010 over M3), native ads **0.817**. Competitive with Arapakis & Leiva 2016 (0.86 AUC, 638 features) using ~6 features because the task model tells you which features matter.
- **Retreat arc geometry (NB24 v2, rebuilt 2026-04-08):** Top ads show 1.50 median arc ratio vs 1.31 for organic (pooled p = 0.027, but ns under participant clustering p = 0.26 — the element-type effect is Fitts ID, not arc curvature). The arc-ratio metric measures path-length / direct-distance at the moment of max retreat — a *different* geometric quantity from the K5 post-closest-drift signal cited in `docs/theory.md`. NB24's participant-clustered direction has not been re-verified post 2026-04-12 fixation audit; treat NB24 numbers as pre-2nd-fix until refreshed. The canonical motor-signature anchor for the four-class dissociation is `[NB22:K5–K7]` (post-closest drift + gaze dwell + proximity dwell), not arc geometry.
- **Discrimination cost (NB20):** Top ads produce 2× the approach rate of organic results (42.9% vs 21.0%), 2.3× the dwell (4,586 vs 2,023 ms), 1.7× the direction changes during retreat (2.7 vs 1.6), and the highest pupil dilation (+0.41%). This is the C/W/L violation: top ads evaluate *more* expensively than organic, not less.
- **Public head-to-head against Brückner et al. 2021:** See [`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md). Approach-retreat features beat the Brückner scalar mouse-movement-length baseline by +12.5 AUC (0.821 vs 0.696) on their own ad-click-prediction benchmark, using an 11-feature logistic regression — no neural network, no embeddings. The task model is the whole reason for the gap.

### Framework extensions

- **C/W/L (Azzopardi, Thomas & Craswell, SIGIR '18)** predicts user evaluation cost decreases with position — ads should be cheaper than organic because they demand less reading. The AdSERP data shows the opposite for top ads: discrimination ("is this ad or result?") is a cost C/W/L doesn't model. Adding element-type interaction features lifts top-ad click-prediction AUC from **0.909** to **0.919** (+0.010; NB22:K9, post coordinate-space audit 2026-04-12). A CIKM 2026 paper draft formalizes this as a missing variable in the framework.
- **Information Foraging Theory (Pirolli & Card, 1999)** provides the patch-leaving vocabulary, but operates at the session level. OSEC applies the same foraging lens at the per-result evaluation level — each result is a mini-patch with its own cost and reward. Retreat geometry is the motor trace of the patch-leaving decision.

### Datasets used for validation

- [AdSERP](https://github.com/kayhan-latifzadeh/AdSERP) — primary, via attentional-foraging
- [The Attentive Cursor Dataset](https://gitlab.com/iarapakis/the-attentive-cursor-dataset) — public (no permission required), 2,737 users, self-reported attention labels, for scale replication. Cloning and taxonomy validation pending.
- [Brückner et al. 2021 artifacts](https://dl.acm.org/doi/10.1145/3404835.3463011) — head-to-head beat documented in [`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md).

## References

- Edmonds (2003). ["Uzilla: A new tool for Web usability testing"](https://link.springer.com/article/10.3758/BF03202549) — instrumented Mozilla browser, "mouse miles" (integrated cursor path length), DOM-path click signature, cursor-vector compression via Optimoz's gesture recognition algorithm. Behavior Research Methods, Instruments, & Computers 35(2):194–201.
- Huang, White & Buscher (2012). ["User see, user point"](https://jeffhuang.com/papers/GazeCursor_CHI12.pdf) — gaze-cursor alignment on SERPs, 700 ms lag, behavior-dependent (CHI '12)
- Guo & Agichtein (2012). ["Beyond dwell time"](https://dl.acm.org/doi/10.1145/2187836.2187914) — post-click cursor movements for document relevance (WWW '12)
- Arapakis & Leiva (2016). ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) — 638 cursor features, AUC 0.86 for attention prediction (SIGIR '16)
- Leiva & Arapakis (2020). ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) — 2,737 users, cursor + attention labels + SERP HTML (Frontiers)
- Edmonds (2016). ["Learning from Complex Online Behavior"](https://youtu.be/j38fm48gTgg?t=1348) — click hold duration as cognitive signal

## License

MIT
