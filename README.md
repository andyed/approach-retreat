# Approach/Retreat

Cursor approach-retreat dynamics on search result pages. SERP-specific companion to [ClickSense](https://github.com/andyed/clicksense).

## The idea

Before you click a search result, your cursor tells a story. It approaches a result (interest), dwells over it (evaluation), then either commits (click) or retreats (rejection). The retreat distance encodes confidence: moving far away raises the motor cost of returning — a self-imposed penalty that externalizes uncertainty into physical space.

ClickSense captures the moment of commitment (mousedown to mouseup). Approach/Retreat captures everything before: the evaluation phase where most of the cognitive work happens.

### Signals

| Signal | What it means |
|--------|---------------|
| **Approach velocity** | Fast = scanning. Slow = evaluating. |
| **Dwell time** | Time cursor spends over a result's bounding box |
| **Retreat** | Cursor leaves without clicking — rejection or deferral |
| **Retreat distance** | How far the cursor moves away — encodes rejection confidence |
| **Re-approach** | Cursor returns to a previously visited result — reconsideration |
| **Commitment depth** | How far down the SERP before first click |

### Adaptive reranking

Collected approach-retreat signals drive relevance scoring. Over time, results rerank themselves based on how visitors actually evaluate them — not just what they click.

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

The [gh-pages site](https://andyed.github.io/approach-retreat/) presents real questions displayed as search results with synthetic answers that represent the discourse arc over time. An injected ad tests discrimination cost (the approach-retreat signature when users identify sponsored content). Your cursor behavior is captured anonymously to study how people evaluate ranked information.

Starting with: **"Will AI be an existential threat to humanity?"** — synthetic answers representing ~15 years of shifting consensus, from early dismissal through the Bostrom inflection to post-GPT recalibration.

## Adapters

- `approach-retreat/adapters/posthog` — PostHog event flattening
- `approach-retreat/adapters/callback` — Buffer + flush (sendBeacon, etc.)

## References

- Huang, White & Buscher (2012). ["User see, user point"](https://jeffhuang.com/papers/GazeCursor_CHI12.pdf) — gaze-cursor alignment on SERPs, 700 ms lag, behavior-dependent (CHI '12)
- Guo & Agichtein (2012). ["Beyond dwell time"](https://dl.acm.org/doi/10.1145/2187836.2187914) — post-click cursor movements for document relevance (WWW '12)
- Arapakis & Leiva (2016). ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) — 638 cursor features, AUC 0.86 for attention prediction (SIGIR '16)
- Leiva & Arapakis (2020). ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) — 2,737 users, cursor + attention labels + SERP HTML (Frontiers)
- Kirsh & Maglio (1994). "On distinguishing epistemic from pragmatic action" — retreat as epistemic action framework
- Edmonds (2016). ["Learning from Complex Online Behavior"](https://youtu.be/j38fm48gTgg?t=1348) — click hold duration as cognitive signal

## License

MIT
