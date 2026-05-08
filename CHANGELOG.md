# Changelog

## v0.3.0 — 2026-05-08 — getSignals not_approached fixes + adapter idempotence

Three-commit data-correctness patch on top of v0.2.1, motivated by the
movies.mindbendingpixels.com calibration substrate. No public API
change; per-session AOI rollups now reflect what the user actually
saw, and adapters can no longer double-count the session-end summary.
This release also begins committing `dist/` so downstream consumers
can pin against tags rather than rebuild locally.

### Why

The v0.2.1 patch closed the missing-summary loss rate. With
`ar_session_summary` reliably landing, the next layer of artefacts
surfaced:

1. **Per-session `C+D+R+N` summed to 4-7 of 10 expected**, not 10.
   AOIs the user scrolled past then out of view fell out of the
   not_approached rollup entirely — the rollup consulted the
   *currently*-intersecting set, not the *ever*-intersecting set.
2. **Even after fixing (1)**, the threshold-0.3 IntersectionObserver
   missed cards that flickered through the viewport faster than the
   browser polling cadence caught them at ≥30% intersection. Same
   end result: AOIs invisible to the rollup.
3. **Consumers calling `adapter.captureSummary(ar)` explicitly**
   before a same-origin navigation could still produce a duplicate
   summary — the visibilitychange/pagehide listener wired by `bind()`
   had its own `fired` guard, but it didn't see the explicit call.
   The `movies-mindbendingpixels` consumer worked around this with a
   wrapping shim; the workaround is no longer needed.

### What changed

- **`449b77a` getSignals: not_approached uses ever-visible, not
  currently-visible.** Add-only `_everVisibleResults` mirror of
  `_visibleResults`. The not_approached enumeration now consults the
  add-only set so AOIs the user scrolled past stay in the rollup.
  Below-fold AOIs that never intersected stay correctly absent.
- **`283af59` posthog-adapter: captureSummary self-idempotent across
  both call paths.** `summaryFired` lifted out of `bind()` and into
  the adapter's outer scope. Explicit-call and visibilitychange
  paths share the guard; first call wins, subsequent calls are
  no-ops. `bind()` simplified.
- **`8ae9d33` getSignals: dedicated threshold-0 observer for
  everVisible enrollment.** `_everVisibleResults` now has its own
  `IntersectionObserver` at `threshold: 0`. The original 30%-threshold
  observer is unchanged (preserves band/dwell semantics). Below-fold
  AOIs still correctly absent because they never intersect at all.

### Verification

Verified on `movies.mindbendingpixels.com` post-deploy
(2026-05-08 03:39 UTC):

- **everVisible:** deliberate-scroll dogfood pass produced
  `C+D+R+N = 8` of 10 on the affected mission (vs 4-5 pre-fix). The
  remaining 2-of-10 gap reflects browser IntersectionObserver
  poll-rate limits — a card flickering through between polls during
  very fast scroll. Out-of-scope for this release; would need a
  mutation-observer fallback or a static "denominator from result
  count" override at the consumer level.
- **idempotency:** zero millisecond-class within-page-lifecycle
  duplicates. Multi-row `(session_id, ar_query_id)` pairs do exist
  (max 4 for one mission) but minimum inter-row gap is 14.1 seconds
  — those are redo-button revisits, each spawning a fresh adapter,
  which is the intended behavior.

### Distribution policy change

Starting with v0.3.0, `dist/` is committed to the repo and tagged.
Downstream consumers can pin against the tag (e.g. `v0.3.0`) and
verify a shipped sha256 rather than rebuild locally and trust their
build environment. The `build` script still exists; CI/dev workflows
just no longer required to ship.

### Migration notes

Consumers wrapping `adapter.captureSummary` to dedupe (e.g. the
shim previously in `movies-mindbendingpixels`'s `js/ar-init.js`) can
drop the wrap. Adapter is self-idempotent now.

No public API change. No migration on stored data.

## v0.2.1 — 2026-05-07 — Reliable session-summary capture on mission flow

Telemetry-reliability patch on the data-collection site. No library API change.

### Why

At the 2026-05-06 movies.mindbendingpixels.com conference demo (n=5 engaged users), 103 `ar_episode` events and 45 `ar_click` events landed cleanly — but only **1** `ar_session_summary` was captured across all 5 sessions. The 80 % loss rate meant the per-session M4 nine-feature rollups, classification counts, and viewport-band aggregates (the inputs the CIKM paper consumes) were missing for most attendees.

### Root cause

The PostHog adapter's `bind()` listener captures the summary on `visibilitychange:hidden` / `pagehide`. With the missions flow's 50 ms post-click `setTimeout` redirect to `done.html`, PostHog's batch buffer didn't have time to flush before the page detached, and bfcache could swallow `pagehide` entirely.

### What changed

- `site/serps/rich-thumbnail.html`: `handleRunClick` now calls `adapter.captureSummary(ar)` synchronously before scheduling the redirect. Redirect delay grows to 250 ms so the batch buffer can flush.
- `site/js/ar-init.js`: `captureSummary` is wrapped with a `summaryFired` guard inside `initApproachRetreat` so the explicit click-time call and the implicit `bind()` pagehide call cooperate — whichever fires first wins; the other becomes a no-op. `bind()` remains as the safety net for sessions that close without clicking.
- Drops `includeSamplesInEpisodeJson: true` — `samples` was duplicated by the flattened `ar_trajectory` (stride 10) field, ~halving per-event payload and reducing PostHog per-property-size drop risk.

### Verification

Re-run the mbp-dash check after the next data-collection session:

```sql
SELECT event_name, COUNT(*) AS n, COUNT(DISTINCT session_id) AS sessions
FROM events
WHERE host = 'movies.mindbendingpixels.com'
  AND ts >= '2026-05-07'
GROUP BY event_name;
```

Expect `ar_session_summary` count ≈ session count for sessions that include at least one click.

## 2026-05-05 — Y-pixel coverage fix in upstream `attentional-foraging` (branch `bbox-y-coverage-fix`)

Companion to the AF cascade (see `attentional-foraging/CHANGELOG.md` 2026-05-05). Tracks the AR-side work needed to consume the new `typed_gapfill` flavor.

### Why

Upstream AF audited click attribution under `typed` AOI extraction and found 22.7 % silent contamination of `approached & clicked` records via Y-band-only attribution rolling right-rail (dd_right) and page-chrome clicks into adjacent organics. The mitigation is a new `typed_gapfill` flavor (midpoint-split organic bboxes + X+Y bbox-aware click attribution + `is_main_axis_click()` trial filter).

The replay viewer at `site/replay/` and any model JSON / cursor-approach episode export that referenced upstream typed bboxes need to consume the gapfill outputs and reflect the change visually before AR's K-claims can be updated.

### What landed (this branch)

(In progress.) Initial branching done; awaiting upstream verification on the 6 confirmed-issue trials before rebuilding the replay set.

### What's pending

- Replay-set rebuild to consume `attentional-foraging/data/aoi-typed-gapfill/{tid}.json` instead of `data/aoi-typed/{tid}.json`. Visual verification on:
  - `p008-b3-t7` (right-rail click rolled into organic 3 under legacy)
  - `p009-b5-t2` (page-chrome click rolled into dd_top 0)
  - `p041-b5-t2` (right-rail no-shipped-rect click rolled into organic 2)
  - `p038-b4-t3` (off-target click 92 px right of column rolled into organic 7)
  - `p005-b2-t2`, `p006-b2-t7` (in-column-edge clicks recovered by midpoint-split)
- Re-derivation of cursor-approach episode JSONs from `cursor-approach-features-typed-gapfill.json`.
- Review of `site/replay/data/aoi_corrections.json` for stale entries that demoted positions because the original bbox was over-tight; may become unnecessary under gapfill.

### Pointers

- [`attentional-foraging/docs/null-findings/2026-05-05-bbox-y-coverage.md`](../attentional-foraging/docs/null-findings/2026-05-05-bbox-y-coverage.md)
- [`attentional-foraging/docs/methodology/attribution-cascade-synthesis.md §1.06`](../attentional-foraging/docs/methodology/attribution-cascade-synthesis.md)

---

## 2026-05-01 — AOI rebuild on bbox attribution (branch `feat/aoi-rebuild-2026-05-01`)

### Why

Upstream `attentional-foraging` shipped pixel-accurate organic-result bboxes (branch `feat/aoi-pipeline-v2`, replacing band-estimation-from-h3-count with CV row-projection on screenshots). The replay-bundle producer (`scripts/build_replay_trial.py`) reads `AdSERP/data/organic-boundary-data/{tid}.json` and feeds those bboxes into the M5 four-class classifier. Re-running it under the new bboxes shifts class labels per AOI on most trials.

### What was rebuilt

All 80 curated trials in `site/replay/data/curation.json` had their replay bundles regenerated under the new bbox AOIs. Pre-rebuild bundles snapshotted to `scripts/output/aoi-rebuild-baseline/trials-pre-aoi-v2/` for diff.

### Magnitude of label shifts

**64 of 80 curated trials (80.0%) have shifted four-class label distributions.** Sample:

| Trial | OLD (band attribution) | NEW (bbox attribution) |
|---|---|---|
| p011-b6-t2 | DEF=5, NA=5, EVAL=3 | DEF=8, **CLK=1**, NA=5, EVAL=3 (click reattributed) |
| p019-b6-t2 | DEF=1, NA=4 | **CLK=1**, DEF=8, NA=5 (huge shift) |
| p035-b6-t10 | NA=7 (all unapproached) | DEF=6, CLK=1, NA=6 (was previously a "drive-through" example) |
| p036-b1-t6 | DEF=4, NA=6, EVAL=2 | CLK=1, DEF=8, NA=4, EVAL=2 |

### Stale curation captions (8 total)

Captions that cite class counts which no longer match:

```
[B-DEF] p019-b1-t8:    "5 DEFERRED"  → new has 11
[B-DEF] p015-b3-t10:   "5 DEFERRED"  → new has  7
[B-DEF] p015-b5-t2:    "4 DEFERRED"  → new has  9
[B-DEF] p005-b2-t2:    "4 DEFERRED"  → new has 10
[B-DEF] p009-b1-t1:    "3 DEFERRED"  → new has  8
[B-REJ] p006-b4-t7:    "5 EVAL-REJ"  → new has  4
[B-REJ] p020-b1-t7:    "3 EVAL-REJ"  → new has  0   (reclassified entirely)
[B-REJ] p045-b2-t5:    "2 EVAL-REJ"  → new has  1
```

The remaining 72 captions either don't cite explicit counts (general descriptions) or still match exactly under bbox attribution.

### Status / next moves

- **Replay bundles are committed.** Demos at `andyed.github.io/approach-retreat/replay/` will reflect the new labels on next deploy.
- **Stale captions need editing** before re-publishing — either rephrase to match new counts or pick different trials that still illustrate the original intent.
- **M5 classifier was NOT retrained.** It was originally trained against NB22 gaze-based regression labels under band attribution. Inference happens against new bboxes (cursor + AOI features change), but the LR coefficients are unchanged. A future iteration should retrain M5 against organic-attribution NB22 labels for full consistency.
- **Heavier work deferred**: regenerating cursor-approach-features under organic and retraining M5 against fresh NB22 labels.

### Upstream pointer

Full upstream context, K-ID delta tables, and pipeline rationale at `attentional-foraging` branch `feat/aoi-pipeline-v2`, top entry of `CHANGELOG.md`.

---

All notable changes to `approach-retreat` are documented here. Versioning
follows SemVer; breaking changes bump MAJOR, additive changes bump MINOR.

## [0.2.0] — 2026-04-19

### Added

- **Per-AOI viewport-band dwell tracking.** Every observed AOI now
  accumulates four cumulative-ms totals: `vp_any_ms` (any part of the AOI
  intersected the viewport), plus `vp_top_ms` / `vp_mid_ms` / `vp_bot_ms`
  using the AOI center's viewport-y bucketed into thirds of the current
  viewport height. Piecewise-constant accumulation fires on scroll (rAF-
  throttled), resize, reflow (ResizeObserver), and IntersectionObserver
  transitions.
- **`ApproachRetreat.getViewportBands()`** — returns per-position band
  totals `[{ position, vp_any_ms, vp_top_ms, vp_mid_ms, vp_bot_ms }]`.
- **`ApproachRetreat.getViewportBandContext()`** — returns
  `{ viewport_h, schema: 'edmonds-2026-vpbands-v1' }` for session-summary
  basis disclosure.
- **Exported pure helpers** — `computeViewportBandsPure(timeline, aois,
  scrH)` and `classifyAoiInViewport(pageTop, pageBot, scrollY, scrH)`.
  Stateless, parity-tested against the Python reference
  `viewport_ms_for_trial` in
  `attentional-foraging/scripts/viewport_time_calibration.py`
  (`scripts/test_viewport_bands_parity.{js,py}`, Δ = 0 on every field).
- **Episode-scoped band times on `ar_episode`** — `ar_vp_{any,top,mid,bot}_ms`
  restricted to `entered_at → exited_at`.
- **Session-scoped band times on `ar_session_summary`** — merged into each
  `ar_approach_features` row on `position`. Augmentative: the nine-feature
  schema `edmonds-2026-m4-v1` is unchanged; band fields are nullable on
  rows without a band record. Summary also carries
  `ar_viewport_band_schema: 'edmonds-2026-vpbands-v1'` and
  `ar_viewport_band_basis_px` (current viewport height at capture).
- **Config flags** — `trackViewportBands` (default `true`) and
  `trackViewportReflow` (default `true`). Setting `trackViewportBands:
  false` fully degrades to pre-0.2.0 behavior.

### Fixed

- `_resultPageYCenter` cache is now invalidated on layout reflow via
  ResizeObserver. Prior behavior cached on first observation and never
  re-measured — on reflow-heavy pages, `getApproachFeatures()` could drift
  silently from the live AOI geometry. Incidental improvement to M4
  feature accuracy.

### Calibration source

LAB (AdSERP), n = 2,351 approached-not-clicked AOIs, 47 LOSO participants,
post 2026-04-12 coordinate-space audit. Outcome = NB22 gaze-regression
label (deferred vs evaluated-rejected). 95 % CIs from 1,000-seed
participant-cluster bootstrap:

- retreat features alone (9 M4 features): **AUC 0.796 [0.759, 0.830]**
- viewport bands alone (target AOI, 3 features): **AUC 0.800 [0.774, 0.828]**
- retreat + bands combined: **AUC 0.842 [0.818, 0.864]** (+0.04 over retreat alone)
- Fully-contextual viewport (all 10 AOIs × 3 bands + rank dummies, 40
  features): AUC 0.748 — worse than local-only under LOSO. The signal is
  **local per-AOI**, not contextual. This library emits local bands only.

Pooled standardized coefficients (+ predicts DEFERRED):
`vt_top +1.83, vt_mid +0.83, vt_bot +0.21`. Top-of-viewport dwell is ~9×
more discriminative than bottom-of-viewport.

`vt_top` is **rank-dependent**: +2.02 [+1.47, +2.69] at P0 → +0.49 [+0.13,
+1.05] at P4 → +0.21 [−0.17, +0.69] at P5 (CI crosses 0 — the significance
transition). **Rank dependence is reported for P0–P5 only.** Positions past
P5 are too sparse (n ≤ 91 per slice), class-balance-inverted (P8 is 25 %
deferred vs P0's 90 %), and participant-concentrated (top 4 of 33
contributors supply 44 % of the deep-rank pool; removing them attenuates
the bucket's vt_top from +0.72 to +0.34 with CI touching 0) for a robust
headline claim. Diagnostic deep-rank values live in
`attentional-foraging/scripts/output/viewport_time_calibration/bootstrap_results.json`
(`deep_rank_bucket`, `per_position_ci[6..8]`) and should not be cited as
calibration without a larger-corpus replication. Consumers should apply
per-rank interaction weights downstream; the library emits raw band ms only.

Source: `attentional-foraging/scripts/viewport_time_calibration.py`,
`scripts/output/viewport_time_calibration/results.json`.

### Notes

- `ResizeObserver` is feature-detected; on older browsers the library
  falls back to `scroll` + `window.resize` coverage (safe for non-
  reflowing pages).
- Mid-session viewport resize shifts the basis for subsequent intervals.
  The summary carries `ar_viewport_band_basis_px` (current at capture);
  sessions needing basis-stable bands should filter on equality with the
  initial `ar_viewport_h` in `buildSessionContext`.
- Synthetic parity test covers edge cases: fully-above, fully-below, all-
  thirds crossing, tall AOI with center off-viewport, zero-duration
  intervals, stationary tails. An end-to-end real-trial replay test
  against the AdSERP dataset is recommended as a follow-up (not load-
  bearing for the 0.2.0 release; the synthetic parity is exact).

## [0.1.0] — 2026-04-15

First tagged release. Ships the cursor episode decomposition library, the
four-class outcome taxonomy, the PostHog adapter, the gh-pages Quora-SERP
demo, and the canonical M4 nine-feature extractor used by the Edmonds 2026
CIKM paper.

### Added

- **`ResultFeatureTracker`** — per-result running aggregates of the nine M4
  approach features from the Edmonds 2026 CIKM paper. Computed against each
  result's page-space Y center (scroll-invariant) with O(1) memory per
  tracked result regardless of sample count.
- **`ApproachRetreat.getApproachFeatures()`** — returns the nine features
  per result position, ranked by position. Fully parity-tested against the
  AdSERP canonical extractor in
  `attentional-foraging/scripts/m4_nb21_hybrid_rerun.py` (all nine features
  match within 1e-6).
- **Parity test suite** — `scripts/test_feature_tracker_parity.{js,py}` run
  a synthetic trajectory through both the JS library and the Python paper
  extractor and diff the outputs.
- **PostHog adapter extension** — `ar_session_summary` now ships
  `ar_approach_features` alongside the existing four-class taxonomy fields,
  so downstream pipelines can train M4 click predictors or M5 deferred-class
  detectors directly on captured data.
- **`docs/validation/m5-calibration.md`** — methodology doc for deploying a
  cursor-only deferred-class detector calibrated from behavioral labels.
- **Four-class outcome taxonomy** — `clicked` / `deferred` /
  `evaluated_rejected` / `not_approached`. Library heuristic (cursor
  re-entry within `reapproachWindowMs`) is a lower-fidelity approximation
  of NB22 gaze-regression labels; deployments needing gaze-grounded labels
  should follow the M5 calibration methodology above.
- **`approachFeatureProximityPx`** config option (default 100 px) matching
  the canonical AdSERP extractor's `dwell_in_proximity_ms` threshold.

### Validated

- Cross-dataset replication on the Attentive Cursor Dataset
  [Leiva & Arapakis 2020]: 11-feature LR reaches AUC 0.821 on `ad_clicked`
  vs. scalar mouse-length baseline 0.696, no eye tracker. See
  `analysis/attcur-validation/`.
- AdSERP validation lives in the companion `attentional-foraging` repo
  (NB20–NB22, and the gaze-clean Option D hybrid extractor rerun at
  `scripts/m4_nb21_hybrid_rerun.py`).

### Notes

- Not yet on npm. Install from the GitHub repo URL or clone and
  `node build.js` yourself. The `dist/` bundle is gitignored; rebuild
  before every tagged release.
- Coordinate convention: cursor Y is page-space throughout, matching
  `attentional-foraging`.
