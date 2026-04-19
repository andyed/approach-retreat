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

Per-position estimates are reported for P0–P5 (n ≥ 122 per slice, 200-seed
per-position bootstrap). Positions past P5 are pooled into a single **P6+
bucket** because per-position estimates at P6/P7/P8 are noise: class balance
inverts (P8 is 25 % deferred vs P0's 90 %), sample sizes collapse
(n = 91/56/40), and CIs widen across zero. The P6+ bucket is the honest
deep-rank estimator.

| pos | n | vt_top median | 95 % CI | verdict |
|---|---|---|---|---|
| P0 (rank 1) | 645 | **+2.02** | [+1.47, +2.69] | strong |
| P1 (rank 2) | 545 | **+1.67** | [+1.22, +2.38] | strong |
| P2 (rank 3) | 396 | **+1.48** | [+1.03, +2.17] | strong |
| P3 (rank 4) | 262 | **+1.10** | [+0.56, +2.05] | strong |
| P4 (rank 5) | 180 | +0.49 | [+0.13, +1.05] | marginal |
| P5 (rank 6) | 122 | +0.21 | [−0.17, +0.69] | **CI includes 0 — transition** |
| **P6+ bucket** | **201** | **+0.75** | **[+0.21, +1.60]** | weak but CI-clean |

At the P6+ bucket, the bands-alone coefficient structure flattens: `vt_top`
+0.72, `vt_mid` +0.30, `vt_bot` +0.36. At depth, *any* viewport residence
is a consideration signal, not specifically top-of-viewport. Combined
retreat + bands AUC at P6+ is 0.742 [0.640, 0.839].

**Practical implication for consumers.** Weight `vt_top` by rank with a
piecewise function or a smooth decay; a single pooled weight under-fits
P0–P3 and over-fits deep ranks. If a single band feature is desired,
`vt_mid` is the more rank-robust default (+0.5 to +1.2 across P1–P7).
For scoring beyond P5, treat the P6+ bucket as one position.

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
