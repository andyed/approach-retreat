# Liu, Wang, Zhou, Nie, Zhang & Ma — *From Skimming to Reading: A Two-stage Examination Model for Web Search* (CIKM '14)

[`liu2014skimming`](references.bib) · [DOI 10.1145/2661829.2661907](https://doi.org/10.1145/2661829.2661907)

The closest **per-result-AOI precedent** to approach-retreat. THUIR / Yiqun Liu group, four years before PSCM. Two-phase SERP evaluation — *skimming* then *reading* — both phases predictable from mouse signal at the per-result granularity.

## Method

Two stages of examination:
1. **Skimming** — fast, ballistic scan over results.
2. **Reading** — slower, focused engagement on a subset of results.

Per-result summary statistics drive the inference: dwell, hover, presence — whether the cursor entered the result region, how long it spent, whether it lingered above the threshold the model fits. Logistic models on those features predict click probability.

## What this paper does that the cursor-feature classifier tradition does not

Liu *et al.* commit to **the per-result AOI as the unit of feature aggregation** — the same commitment approach-retreat builds on. Brückner-style cursor classifiers (per-session bag-of-statistics) and sequence models (per-trajectory-token) both step away from per-result attribution. Liu sits closer to approach-retreat in the layout below than to either of those:

```
per-rank  →  per-result AOI summary  →  per-result AOI episode geometry  →  per-trajectory token
(click models) (Liu 2014)             (approach-retreat)                  (sequence models)
```

## What approach-retreat adds

- **Internal episode geometry**, not just summary statistics. Approach-retreat measures `min_dist`, `retreat_dist`, `retreat_arc_ratio`, `direction_changes`, `frac_decreasing` *within* each AOI encounter. Liu's vector is per-result-summary (dwell, hover, presence) — coarser.
- **The four-class taxonomy of non-click behavior**. Liu's two-stage model splits *whole-trial* behavior into skim/read; approach-retreat splits *per-result* behavior into clicked / deferred / evaluated-rejected / not-approached. The latter is the LTR-relevant graded-relevance shape.
- **Click-buffer leakage controls.** Liu's per-result vector includes terminal-window samples; approach-retreat's seven canonical features are screened against terminal cursor lock-on (CIKM §3.4 / §4.4).

## Notes for the CIKM paper

§2 cites this as **"the closest per-result-AOI precedent"** — the gap between Liu's per-result summary and approach-retreat's per-result *episode geometry* is what the paper's contribution sits in. Cite as `\cite{liu2014skimming}`.

The OSEC Survey → Evaluate decomposition (CIKM §3.3, deliberation phase) is a distant cousin of Liu's skimming → reading split — both are two-phase task models for SERP evaluation. The tasks are different (Liu's outcome is click prediction across a session; approach-retreat's outcome is per-AOI engagement classification), but the two-phase decomposition itself is shared.
