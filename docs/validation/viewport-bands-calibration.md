# Viewport-band calibration

**What this library emits:** per-AOI cumulative ms in each of four bands —
`vp_any_ms`, `vp_top_ms`, `vp_mid_ms`, `vp_bot_ms`. Bands are defined by
the AOI center's viewport-y position, bucketed into thirds of the current
viewport height (`scr_h`). `any` is binary viewport intersection
(accumulates whenever any part of the AOI overlaps the viewport, including
the tall-AOI case where the center is off-viewport).

**What this library does not do:** score, weight, or interact bands with
rank. Raw band ms only. Consumers apply per-rank interaction weights
downstream — the coefficient structure is rank-dependent (see below).

## Empirical calibration (2026-04-19)

Source: `attentional-foraging/scripts/viewport_time_calibration.py`.
Corpus: AdSERP LAB (47 participants), post 2026-04-12 coordinate-space
audit. Target population: approached-not-clicked AOIs (n = 2,351).
Outcome: NB22 gaze-regression label (1 = deferred, 0 = evaluated-
rejected). LOSO LR by participant.

### Pooled performance

Bootstrap 95 % CIs from 1,000 participant-cluster-resampling seeds over the
pooled subset; point estimates from the LOSO run.

| Model | features | Bootstrap median | 95 % CI |
|---|---|---|---|
| retreat alone (M4) | 9 | 0.796 | [0.759, 0.830] |
| viewport bands_any alone | 1 | 0.734 | [0.701, 0.766] |
| viewport bands alone (target AOI) | 3 | **0.800** | **[0.774, 0.828]** |
| fully-contextual viewport (all 10 AOIs × bands + rank) | 40 | 0.748 | — (point only) |
| **retreat + bands (target AOI)** | 12 | **0.842** | **[0.818, 0.864]** |

**Takeaway.** Viewport bands carry as much signal as the 9-feature
cursor retreat set (overlapping CIs); the combined model is separable
at the upper CI (0.842 > 0.830). Fully-contextual viewport is *worse*
than local — the signal is **local per-AOI**, so this library emits
local bands only. See `attentional-foraging/notebooks-v2/28_viewport_bands.ipynb`
for the full per-position and per-participant breakdown.

### Coefficient signs (pooled, standardized, + = predicts DEFERRED)

| feature | coef |
|---|---|
| vt_top | **+1.83** |
| vt_mid | +0.83 |
| vt_bot | +0.21 |

Top-of-viewport dwell is ~9× more discriminative than bottom-of-viewport
dwell, pooled. Mechanistically consistent: top-of-viewport is where
reading happens; bottom-of-viewport is scrolling past.

### Rank dependence of `vt_top`

Per-position estimates are reported for **P0–P5 only** (n ≥ 122 per slice,
200-seed per-position cluster bootstrap).

| pos | n | vt_top median | 95 % CI | verdict |
|---|---|---|---|---|
| P0 (rank 1) | 645 | **+2.02** | [+1.47, +2.69] | strong |
| P1 (rank 2) | 545 | **+1.67** | [+1.22, +2.38] | strong |
| P2 (rank 3) | 396 | **+1.48** | [+1.03, +2.17] | strong |
| P3 (rank 4) | 262 | **+1.10** | [+0.56, +2.05] | strong |
| P4 (rank 5) | 180 | +0.49 | [+0.13, +1.05] | marginal |
| P5 (rank 6) | 122 | +0.21 | [−0.17, +0.69] | **CI includes 0 — transition** |

**Deep ranks (P6–P8) not reported as calibration.** An initial pooled
P6+ bucket (n = 201) gave `vt_top = +0.75 [+0.21, +1.60]`, but a
participant-sensitivity audit (2026-04-19) found the estimate fragile:
- Top 4 of 33 contributors supply 44 % of the bucket (p044 alone = 14 %).
- Dropping those 4 participants attenuates `vt_top` to +0.34 with the
  CI touching 0 ([−0.03, +1.40]).
- Top-4-only subsample shows `vt_top = +1.13 [+0.89, +1.71]` — a tight
  internal pattern, but not representative.
- Bottom-of-page ads and deep-rank approach behavior may interact
  (users reaching rank 7–10 are disproportionately those willing to scroll
  past ad slots); this confound has not been controlled for.

Deep-rank values are retained in
`attentional-foraging/scripts/output/viewport_time_calibration/bootstrap_results.json`
(`deep_rank_bucket` + `per_position_ci[6..8]`) for diagnostic use. They
should not be cited as calibration without a larger-corpus replication
that (a) balances deep-rank contribution across participants and
(b) stratifies by bottom-ad presence.

**Practical implication for consumers.** Weight `vt_top` by rank over
P0–P5 with a piecewise function or a smooth decay. A single pooled
weight under-fits P0–P3 and over-fits the P4–P5 transition. If a
single band feature is desired, `vt_mid` is the more rank-robust
default (+0.5 to +1.2 across P1–P5). Do not apply a learned deep-rank
weight until the confounds above are resolved.

## Parity test

`scripts/test_viewport_bands_parity.{js,py}` exercise the pure JS helper
`computeViewportBandsPure` against the canonical Python
`viewport_ms_for_trial` logic (lifted verbatim from the calibration
script). The synthetic fixture covers:

1. AOI fully above viewport throughout → all zeros.
2. AOI fully below viewport throughout → all zeros.
3. AOI center crosses all three thirds during scroll.
4. Tall AOI with center outside `[0, scr_h]` while intersecting →
   `any_ms` only, no third.
5. Zero-duration interval (two events at same `t`) → skipped.
6. Final stationary interval after last scroll.

All 24 fields (6 AOIs × 4 bands) match exactly (Δ = 0).

## Basis caveat

Band definitions depend on `window.innerHeight` at snapshot time. The
library uses the live value; bands accumulated before a mid-session
resize are under the old basis, after under the new. The session
summary carries `ar_viewport_band_basis_px` (current at capture) and
`ar_viewport_h` (from `buildSessionContext` at page load). Downstream
analyses needing basis-stable bands should filter on sessions where
these match.
