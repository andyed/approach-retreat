# Approach/Retreat

Cursor approach-retreat dynamics on **ranked list layouts** (search result pages, recommendation feeds, comparison tables). Sister library to [ClickSense](https://github.com/andyed/clicksense).

## The idea

Before you click a search result, your cursor tells a story. It approaches a result (interest), dwells over it (evaluation), then either commits (click) or retreats. The geometry of that retreat — how curved, how far, how directly — distinguishes results the user is done with from results they may come back to. Curved + close retreats predict re-approach; straight + far retreats predict commitment to rejection.

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

Each completed cursor visit to a result produces:

```js
{
  position: 0,
  dwell_ms: 847,
  visited: true,
  clicked: false,
  retreated: true,
  visit_number: 1,          // 2+ = re-approach
  approach_velocity: 0.34,  // px/ms entering the AOI
  approach_angle: 1.21,     // radians
  peak_velocity: 0.89,      // max speed while over result
  min_velocity: 0.02,       // min speed (near-pause = reading)
  sample_count: 51,
}
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

> **Status: work-in-progress.** Data collection is not yet wired up. The library runs in the browser and builds episode data, but nothing is being persisted or transmitted. Treat the current site as an instrumentation demo — your cursor behavior is visible in the on-page debug overlay (press `d`) but is not recorded anywhere.

The [gh-pages site](https://andyed.github.io/approach-retreat/) presents real questions displayed as search results with synthetic answers that represent the discourse arc over time. An injected ad tests discrimination cost (the approach-retreat signature when users identify sponsored content).

Starting with: **"Will AI be an existential threat to humanity?"** — synthetic answers representing ~15 years of shifting consensus, from early dismissal through the Bostrom inflection to post-GPT recalibration.

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

- **Click prediction (NB21, NB22):** Episode-level features (dwell, retreat distance, arc ratio, visit count) → AUC 0.821 for click prediction. With element-type interactions → 0.838. Competitive with Arapakis & Leiva 2016 (0.86 AUC, 638 features) using ~6 features because the task model tells you which features matter.
- **Retreat arc geometry (NB24):** Top ads show 2.36× arc ratio (curved retreats) vs 1.08 for organic (near-straight). Re-approached retreats have both higher arc ratio (2.09 vs 1.18) and lower Fitts ID (2.21 vs 2.31 bits) — the DEFERRED signature is curved + close.
- **Discrimination cost (NB20):** Top ads produce 2× the approach rate of organic results, 2.3× the dwell, 17× the lateral drift during retreat, and the highest pupil dilation (+0.41%). This is the C/W/L violation: top ads evaluate *more* expensively than organic, not less.
- **Public head-to-head against Brückner et al. 2021:** See [`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md). Approach-retreat features beat the Brückner scalar mouse-movement-length baseline by +12.5 AUC (0.821 vs 0.696) on their own ad-click-prediction benchmark, using an 11-feature logistic regression — no neural network, no embeddings. The task model is the whole reason for the gap.

### Framework extensions

- **C/W/L (Azzopardi, Thomas & Craswell, SIGIR '18)** predicts user evaluation cost decreases with position — ads should be cheaper than organic because they demand less reading. The AdSERP data shows the opposite for top ads: discrimination ("is this ad or result?") is a cost C/W/L doesn't model. Adding a retreat × is_top_ad interaction lifts click-prediction AUC from 0.884 to 0.914. A CIKM 2026 paper draft formalizes this as a missing variable in the framework.
- **Information Foraging Theory (Pirolli & Card, 1999)** provides the patch-leaving vocabulary, but operates at the session level. OSEC applies the same foraging lens at the per-result evaluation level — each result is a mini-patch with its own cost and reward. Retreat geometry is the motor trace of the patch-leaving decision.

### Datasets used for validation

- [AdSERP](https://github.com/kayhan-latifzadeh/AdSERP) — primary, via attentional-foraging
- [The Attentive Cursor Dataset](https://gitlab.com/iarapakis/the-attentive-cursor-dataset) — public (no permission required), 2,737 users, self-reported attention labels, for scale replication. Cloning and taxonomy validation pending.
- [Brückner et al. 2021 artifacts](https://dl.acm.org/doi/10.1145/3404835.3463011) — head-to-head beat documented in [`docs/validation/attcur-bruckner.md`](docs/validation/attcur-bruckner.md).

## References

- Huang, White & Buscher (2012). ["User see, user point"](https://jeffhuang.com/papers/GazeCursor_CHI12.pdf) — gaze-cursor alignment on SERPs, 700 ms lag, behavior-dependent (CHI '12)
- Guo & Agichtein (2012). ["Beyond dwell time"](https://dl.acm.org/doi/10.1145/2187836.2187914) — post-click cursor movements for document relevance (WWW '12)
- Arapakis & Leiva (2016). ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) — 638 cursor features, AUC 0.86 for attention prediction (SIGIR '16)
- Leiva & Arapakis (2020). ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) — 2,737 users, cursor + attention labels + SERP HTML (Frontiers)
- Edmonds (2016). ["Learning from Complex Online Behavior"](https://youtu.be/j38fm48gTgg?t=1348) — click hold duration as cognitive signal

## License

MIT
