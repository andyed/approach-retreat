# Approach/Retreat

Cursor approach-retreat dynamics on search result pages. SERP-specific companion to [ClickSense](https://github.com/andyed/clicksense).

## The idea

Before you click a search result, your cursor tells a story. It approaches a result (interest), dwells over it (evaluation), then either commits (click) or retreats. The geometry of that retreat — how curved, how far, how directly — distinguishes results the user is done with from results they may come back to. Curved + close retreats predict re-approach; straight + far retreats predict commitment to rejection.

ClickSense captures the moment of commitment (mousedown to mouseup). Approach/Retreat captures everything before: the evaluation phase where most of the cognitive work happens.

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

## Related work

This library is the instrumentation half of an ongoing research program. The analysis half lives in [attentional-foraging](https://github.com/andyed/attentional-foraging), which reanalyzes the AdSERP dataset (Latifzadeh, Gwizdka & Leiva, SIGIR '25 — 2,776 trials, 47 participants, simultaneous eye + mouse + pupil tracking) to validate the approach-retreat framework against ground-truth gaze data.

Key findings from that work motivate this library:
- **Four-class taxonomy** — clicked / deferred / evaluated-rejected / not-approached — is recoverable from cursor trajectories alone (NB22, click prediction AUC 0.821)
- **Discrimination cost signature** — top ads produce distinctive cursor hesitation compared to organic results (NB20: 2× approach rate, 2.3× dwell, higher pupil dilation)
- **C/W/L framework extension** — Azzopardi, Thomas & Craswell (SIGIR '18) predicted ads evaluate cheaper than organic; the data shows the opposite for top ads (discrimination, not reading difficulty), suggesting a missing variable in the cost model

This library is the deployable form of that research: you get the signal without the eye tracker.

## References

- Huang, White & Buscher (2012). ["User see, user point"](https://jeffhuang.com/papers/GazeCursor_CHI12.pdf) — gaze-cursor alignment on SERPs, 700 ms lag, behavior-dependent (CHI '12)
- Guo & Agichtein (2012). ["Beyond dwell time"](https://dl.acm.org/doi/10.1145/2187836.2187914) — post-click cursor movements for document relevance (WWW '12)
- Arapakis & Leiva (2016). ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) — 638 cursor features, AUC 0.86 for attention prediction (SIGIR '16)
- Leiva & Arapakis (2020). ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) — 2,737 users, cursor + attention labels + SERP HTML (Frontiers)
- Edmonds (2016). ["Learning from Complex Online Behavior"](https://youtu.be/j38fm48gTgg?t=1348) — click hold duration as cognitive signal

## License

MIT
