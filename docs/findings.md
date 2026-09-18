# Findings — approach-retreat

*Narrative summary of the primary results from this repo's three validation suites. Numbers cite stable IDs in [`key-claims.md`](key-claims.md); this document is the reading layer over the canonical table.*

For the theoretical frame (cursor episode decomposition, four-class taxonomy, LAB↔WILD bridge), see [`theory.md`](theory.md). For mechanism details on the forward-vs-regressive split, see [`forward-regressive-split.md`](forward-regressive-split.md). For the 1-pager pitch to non-academic audiences, see [`one-pager.md`](one-pager.md).

> **Reading flavor tags.** Numbers below carry tags of the form
> `[LAB, AdSERP, <flavor>, NB##:K##]`. The flavor token identifies the
> bbox attribution cascade in force when that number was computed —
> e.g. `absolute legacy`, `bbox-organic`, `organic_hybrid`, `typed_gapfill`,
> `cellsplit`. See
> [`bbox-attribution-lineage.md`](bbox-attribution-lineage.md) for the
> full sequence, which is current, and which is still in flight.

---

## 1. Click-prediction signal survives the eye-tracker stripped away

The library's nine cursor approach features were derived against AdSERP's 150 Hz eye-tracker + cursor stream. The natural question is: what survives when you take the eye tracker away?

**Headline (`[AR-V1:K1]`, `[AR-V1:K6]`):** an 11-feature logistic regression on the same feature family reaches AUC 0.821 ± 0.022 for `ad_clicked` on the public Attentive Cursor Dataset (Leiva & Arapakis 2020) — a 954-session native-ad cohort with cursor + click only, no eye tracker, no pupil. That is +0.125 AUC points (+18 % relative) over the standard `total_mouse_length` scalar baseline `[AR-V1:K3]` reported by Brückner et al. (SIGIR '21).

**Cross-dataset transfer `[AR-V1:K8]`.** The pre-cascade AdSERP LAB click-prediction LOSO with the gaze-clean nine-feature M4 extractor was 0.821 `[LAB, AdSERP, absolute legacy, NB21:K3]` — exactly matching the WILD ACD AUC, which produced an evocative "0.821 = 0.821 across two completely different datasets" framing. The 2026-05-01 cascade retired that LAB anchor: M4 LOSO AUC under bbox-organic attribution is now 0.864 `[LAB, AdSERP, organic, NB21:K-bbox-4]` and 0.870 under hybrid attribution. The post-cascade LAB number is +0.043 above WILD; the headline shifts from "same number" to "the cursor-only feature family transfers from LAB to WILD with a modest LAB-favoring gap, consistent with cleaner attribution sharpening the LAB signal." The within-CI agreement is intact (LAB per-fold SD ≈ 0.044; WILD ± 0.022 — overlap is wide); the rhetorical "exact equality" hook does not survive cleaner attribution. WILD AUC `[WILD, attcur]` is rank-type-N/A (single-AOI native ad cohort, no AdSERP-style rank structure). Both LAB anchors above are the fixation-selected stream; the current cursor-only LAB anchor is M4-7 0.935 `[AR-V1:K-cursor-8]` (0.928 under the `organic` flavour), which widens the LAB-favoring gap to +0.114. K-bbox-8 is superseded.

### The dwell-cheat objection is defused

A skeptical reviewer could read `[AR-V1:K1]` and ask whether the signal is just Fitts mechanics: a user about to click *must* stop the cursor over the target, so dwell-in-target trivially predicts click.

The answer is the 3-feature no-dwell ablation `[AR-V1:K2]`: `min_dist + retreat_dist + ever_in_target` reaches AUC 0.798 ± 0.036 with no dwell feature at all. That's still +0.102 AUC over the scalar baseline `[AR-V1:K7]`. Dwell contributes an additional +0.023 AUC in the full model (the difference between K1 and K2), which is consistent with a small non-mechanical pause component on top of the Fitts baseline — but the geometry-only signal stands without it.

### Hover alone carries most of the load — a deployment frontier

On the cursor-only stream `[LAB, AdSERP, typed, cursor-only, press-anchored 500 ms]` (producer `attentional-foraging/scripts/output/m4_cursor_aoi_mousedown/summary.json`, 2026-09-06, single-feature sweep at `feature_ablation.buf500.alone`), a single feature — `dwell_in_proximity_ms` (time the cursor spent within 100 px of the AOI centre) — reaches LOSO **AUC 0.853** on the AdSERP click-prediction task. `min_dist` alone reaches 0.872. The full seven-feature M4-7 is **0.935** (`conditions.buf500.M4-7.pooled_auc`; position-only M1 is 0.792), so one feature carries about 0.08 short of the full vector. The earlier 0.821 / 0.837 hover figures (methods-paper replicate repo, `replicate/click_prediction_v0_1.py`) were computed on the fixation-selected stream and are superseded.

Among the 2,608 clicked AOIs in the cursor-only buf500 cache (`AdSERP/data/cursor-only-typed-features-mousedown.json`, `conditions.buf500`, `was_clicked` rows; recomputed 2026-09-18), **94.2 % receive any cursor proximity-dwell** (`dwell_in_proximity_ms > 0`; 2,457 of 2,608); 76.3 % receive ≥ 500 ms (1,990); median 1.78 s on dwelled clicks. These are lower than the earlier 93.2 % / 82.7 % / 2.5 s figures because the earlier buffer was click-anchored, and with the `click` stamp landing about 1.4 s after the press it removed no pre-press samples (`deferred_drop_decomposition.md`); the current buffer is press-anchored and drops the terminal 500 ms of every approach. The hover signature is direct empirical evidence of motor-cognitive coupling at the per-result-AOI grain — not a derived statistic from a multi-feature combination.

**Deployment implication.** A hover-counter readout per AOI is the cheapest possible runtime feature: point-in-100px-ball per cursor sample, no sqrt per AOI, no velocity tracking. The full M4 vector remains the accuracy reference; the hover subset is the minimum-cost deployment shape.

**Cross-surface generalization.** The per-AOI engagement-episode primitive does not require a cursor channel. On touch surfaces, per-result viewport residence (which AOI is in the user's visible viewport, and for how long) replaces cursor proximity-dwell. The per-AOI partitioning rule (every result is its own observer) applies unchanged; only the proximity sensor changes. Hover, viewport-dwell, and gaze-fixation-dwell are three readouts of the same primitive, and a "mini" hover-listener implementation is a deferred-class-classifier-free deployment path worth scoping for the library.

### Attention/noticeability is harder

On the noticed Likert target, the same LR reaches AUC 0.594 ± 0.007 `[AR-V1:K9]`. Brückner's BiLSTM on the analogous task lands in a wide 0.55–0.65 AUC band `[AR-V1:K11]` — the cohort is only 716 sessions with ~77 positives after the Likert filter, so the Wilson CIs are visibly wide. Our LR sits inside that band `[AR-V1:K12]`, which we read as "the linear classifier and the BiLSTM are indistinguishable within confidence intervals" rather than "the linear classifier matches the BiLSTM." An 11-feature LR achieving the same AUC band as a 2-layer BiLSTM with three orders of magnitude fewer parameters and directly interpretable coefficients is a useful engineering finding on this target.

### What this does not prove

- **Not** the four-class deferred-vs-evaluated-rejected taxonomy. ACD has one AOI per session, so the deferred-class structure is uncomputable there. That finding is `[LAB]`-only — see §2 below.
- Not "cursor narrates commitment, not awareness." Earlier framings post-hoc-rationalized the AUC gap between `ad_clicked` and `noticed` as evidence for a commitment-vs-awareness dissociation. That framing has been retracted; the gap is equally consistent with `ad_clicked` being a cleaner objective label than Likert self-report.
- Not geometric curvature as a cognitive signal at this sampling rate. ACD's median ~1 event/sec sampling makes `arc_ratio` geometrically underdetermined; the feature is retained for pipeline consistency but the curvature interpretation has been pulled.

Full discussion at [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md).

---

## 2. M5 — a calibrated deferred SCORE, not a four-class classifier

The four-class taxonomy (clicked / deferred / evaluated-rejected / not-approached) is `[LAB]`-only by construction: the deferred / evaluated-rejected split requires the gaze-fixation sequence revisiting an earlier result band, which no cursor-only stream provides. **Hard four-class labels are reserved for observed cursor episodes** — re-entered the bbox after leaving it is `DEFERRED`, a single episode with no re-entry is `EVALUATED_REJECTED`. M5 is a calibration methodology, not a labeler: train a logistic regression once against gaze-derived labels, then deploy at inference time on standard `mousemove` + click telemetry without any eye-tracker dependency, and read its output as a continuous score rather than a predicted class.

**Why a score, not a label.** The cursor-only detector's own operating point makes the case: at its Youden-*J* threshold, `EVALUATED_REJECTED` precision is 48.5 % (from TPR 0.7276 / FPR 0.4425 on 6,800 deferred / 3,132 rejected rows) — a hard rejected call from cursor geometry alone is worse than a coin flip. The ranking-side evidence points the same way: training an LGBMRanker on gaze-derived four-grade labels gains **+0.05 NDCG** against the paper's four-grade relevance and +0.012 click MRR (`attentional-foraging/docs/ablations/ltr_gaze_graded_labels.md`) — the graded signal pays off in aggregate ordering, not in getting any one instance's label right.

**v3 — the deployed score model** `[LAB, AdSERP, typed, cursor-only + viewport bands]` (producer `attentional-foraging/scripts/export_m5_v3.py` → `scripts/output/m5_v3/summary.json`; note `attentional-foraging/docs/ablations/m5_v3_export.md`; superseded model kept as `m5_cursor_only_v2.json`). Same 9,932-row pool as v2 below, plus the library's `vt_top` / `vt_mid` / `vt_bot` viewport bands cut at the press minus 500 ms. Gate: reproduces `viewport_bands_cursor_only/summary.json` to 1e-6 for cursor-alone (0.691065519), bands-alone (0.788615666), and combined (0.789133048) before any v3 model is fitted.

- LOSO pooled AUC **0.7894**, within-trial **0.7758**; paired lift over cursor alone **+0.0882** [+0.0722, +0.1046] `[AR-V2:K-cursor-15–17]`. A rank variant adding `position` does not help: paired +0.0009 [−0.0017, +0.0034], *p* = 0.37 `[AR-V2:K-cursor-21]`.
- **Deployed model is refit unweighted** (`class_weight: null`), not balanced. The balanced fit ranks identically (paired delta +0.0004 [−0.0001, +0.0008]) but is not a probability — it scores as though the prior were 0.5 against a true prior of 0.6847, under-predicting in nine of ten equal-count bins (Brier 0.1918, worst bin off by 0.226). The unweighted refit brings Brier to **0.1679** and the worst bin to **0.044** — inside tolerance, so no Platt layer was added `[AR-V2:K-cursor-18, K-cursor-23]`. Each model file carries `training_prior` (0.6847) and a logit prior-shift recipe for a consumer whose own base rate differs.
- **Operating points**, deployed unweighted model, LOSO out-of-fold: Youden-*J* (*t* = 0.660) gives deferred P/R 0.859 / 0.692 and rejected P/R 0.529 / 0.753; prior-matching (*t* = 0.556, predicted-deferred share = the pool's own 0.685) gives deferred P/R 0.814 / 0.814 and rejected P/R 0.596 / 0.596 `[AR-V2:K-cursor-19, K-cursor-20]`. Both beat v2's 0.485 rejected precision; neither point should be read as a fact about any single result.
- **Aggregate use is not established.** Every AdSERP page is seen by exactly one participant — 2,437 distinct page slugs across 2,437 pool trials, `max_participants_per_page = 1` — so whether the per-instance score becomes a clean separation when averaged across sessions viewing the same result cannot be tested on this corpus `[AR-V2:K-cursor-22]`.
- The band term dominates the fit (`vt_top` +1.412 standardized, larger than any cursor term) and is mostly the return: bands-alone AUC falls from 0.771 to 0.553 on the first-visit carve (`AR-V3:K-cursor-10`). The score's discrimination is real; its mechanism is largely retrospective.

**v2 — the previous deployed model, superseded 2026-09-18** `[LAB, AdSERP, typed, cursor-only, press-anchored 500 ms]` (producer `attentional-foraging/scripts/m4_cursor_only_downstream.py` → `output/m4_cursor_only_downstream/summary.json`, 2026-09-06; transcribed 2026-09-18). Same seven-feature M4 vector, same 9,932-row pool, same NB22 gaze-regression target — kept below for the supervision-signal and ladder arguments, which still hold on the cursor-only stream.
- LOSO pooled AUC **0.691** `[AR-V2:K-cursor-1]`; per-fold mean 0.694 ± 0.070 `[AR-V2:K-cursor-2]`
- Youden-*J* threshold *p* = 0.477 `[AR-V2:K-cursor-3]`; on this seven-feature score alone, precision on the predicted-deferred pool 78.1 % `[AR-V2:K-cursor-4]`, recall 72.8 % `[AR-V2:K-cursor-5]`, F1 0.753 `[AR-V2:K-cursor-6]` — for the current classification quality at this threshold, read v3's operating points above instead
- Leave-one-feature-out: `mean_dist` −0.055, `dwell_in_proximity_ms` −0.009, every other feature within ±0.002 `[AR-V2:K-cursor-9]`. The minimal four (`mean_dist`, `dwell_in_proximity_ms`, `min_dist`, `direction_changes`) reproduce the full model at 0.691, paired Δ +0.001 `[AR-V2:K-cursor-10]`.
- Matched-row ceiling: sampling the cursor at fixation onsets on the same 9,911 rows gives 0.715 against 0.692 native, paired +0.007 [−0.005, +0.020] `[AR-V2:K-cursor-8]`. Gaze-timed sampling does not buy a measurable amount on this stream.

### Why the earlier rows were higher: the ladder

The historical M5 rows (0.769 nine-feature, 0.752 seven-feature, 0.709 pre-cascade) were computed on features from `compute_cursor_approach_features.py`, which selects rows by fixation, samples the cursor at fixation times, measures fixation-to-cursor distance, and weights proximity dwell by fixation duration. `deferred_drop_decomposition.py` (2026-09-17) changes one thing per rung on identical rows and labels `[AR-V2:K-ladder-1–12]`: L (LAB typed features, shared rows) **0.771** → G0 (tracker features, cursor at fixation onsets, buf0) 0.665 → N0 (native sampling) 0.663 → N5 (press-anchored 500 ms buffer) 0.659 → C (full cursor pool, 9,932 rows) **0.691**. The paired steps are −0.068 [−0.116, −0.017] for the feature definition, −0.002 for sampling, −0.005 for the buffer, and +0.012 (CI spanning zero, per-participant sd halving from 0.156 to 0.070) for the population. The label is whether the fixation sequence returns to the result; a feature built from fixation positions and durations carried part of that label. The ~0.75–0.77 figures were cursor geometry plus a gaze term; 0.691 is cursor geometry.

### The supervision-signal finding

The training-target choice (gaze-regression label (NB22 ground truth) vs click label (the LOSO M4-7 click classifier thresholded at Youden-*J* as a non-click splitter)) produces a 1.30 × label-disagreement reduction `[AR-V2:K-cursor-13]` against NB22 ground truth on the same seven features, same LOSO protocol, same model family. M5 disagrees with NB22 at 32.6 % `[AR-V2:K-cursor-12]`; the click-thresholded partition disagrees at 42.5 % `[AR-V2:K-cursor-11]` and puts only 48.7 % of the pool in the deferred class against the gaze split's 68.5 % `[AR-V2:K-cursor-14]`.

**Reading.** The improvement isn't the classifier — it's the supervision target. A click-trained classifier thresholded post-hoc as a non-click splitter is trained on the wrong target for the deferred-class question. M5 swaps the target without changing the features. The ratio came down from 1.49 × on the fixation-selected stream because the gaze term in those features helped M5 more than it helped the click baseline.

### LAB diagnostic upper bound — not deployable

The historical gaze-gated ceiling (AUC 0.794, F1 0.867, precision 90.2 % / recall 83.4 %, supervision ratio 2.18 × `[AR-V2:K9–K14]`, `absolute legacy`, 2026-04-14) was computed on the fixation-selected stream and is superseded as a comparator. The current ceiling is `[AR-V2:K-cursor-8]` above: 0.715 gaze-gated vs 0.692 native on the same rows, a paired +0.007 whose interval includes zero. A production deployment gives up about 0.02 pooled AUC, and possibly nothing, by not having fixation timing.

### Class prior caveat

AdSERP's deferred / evaluated-rejected split in the cursor-only approached-non-click population is 68.5 % / 31.5 % (6,800 / 3,132 of 9,932) `[AR-V2:K-cursor-7]`. The fixation-selected pools were 81 / 19 (pre-cascade, `[AR-V2:K15]`, superseded) and 85 / 15 (typed LAB rung, `[AR-V2:K-ladder-11]`): rows the eyes never selected are disproportionately evaluated-rejected, so the prior moves with the row-selection rule. This is not a universal base rate — it's a property of forced-choice 10-result SERP with motivated crowdworker participants. Production traffic with banner-blindness and query abandonment will almost certainly skew differently. Recalibrate the operating threshold against your own class prior.

> Legacy rows `[AR-V2:K-bbox-1–10, K1–K8, K15]` (0.769 / 0.752 / 0.709; 1.49 ×; 81 / 19) are the fixation-selected feature lineage, superseded 2026-09-18; the rows stay in [`key-claims.md`](key-claims.md) with their notes.

Full methodology at [`docs/validation/m5-calibration.md`](validation/m5-calibration.md).

---

## 3. Viewport bands carry more deferred-class signal than cursor retreat, and most of it is the return

*Re-derived 2026-09-18 on the cursor-only pool `[AR-V3:K-cursor-1..12]`; the numbers this section carried before were the fixation-selected pool with the nine-feature LAB vector and are kept as superseded rows in `key-claims.md`.*

The library's per-AOI viewport-band features (`vp_top_ms` / `vp_mid_ms` / `vp_bot_ms`) measure how long an AOI's centre sat in each third of the viewport, cut at the press. On the same 9,932 approached non-click rows the deferred detector uses:

- Bands alone: pooled AUC **0.789**, within-trial **0.773** `[AR-V3:K-cursor-3]`
- Cursor M4-7 alone: 0.691 / 0.718 `[AR-V3:K-cursor-1]`; paired bands − cursor +0.082 [+0.064, +0.100] `[K-cursor-6]`
- Combined: 0.789 / 0.776, +0.006 over bands alone `[K-cursor-4, K-cursor-7]`

Unlike the NB36 viewport kinematics vector, whose pooled edge over the cursor vanished within trial, the band advantage holds inside the page. Coefficient ordering is unchanged from the historical rows: `vt_top` +1.45, `vt_mid` +0.83, `vt_bot` +0.28 `[K-cursor-8]`; top-of-viewport residence is what predicts a return. `vt_top` is positive at every rank P0–P5 with no interval touching zero `[K-cursor-9]`; the earlier P5 significance transition was a property of 122 rows, not of the feature.

**The carve.** Cut the window at the end of the first gaze visit and bands fall from 0.771 to **0.553**, `vp_any` to 0.464, paired −0.195 [−0.213, −0.176] `[K-cursor-10, 11]`; the cursor on the same 9,141 rows is 0.679 `[K-cursor-12]`. A deferred result has spent longer in the top third *because* the eyes came back to it, and the viewport records that return as residence. This is the viewport form of the gaze-dwell circularity (`attentional-foraging/docs/methodology/deferred-dwell-carve.md`), and it is why the TODO's visit-number carve applies to viewport episodes on touch as much as to cursor episodes.

**Practical implication for consumers.** Bands are the stronger deferred-class feature on desktop and the only one on touch, but only their pre-return portion is a predictor; whole-session per-AOI viewport analytics are the circular ones. Weight `vt_top` by rank if you like, but the rank dependence is a gentle decline now, not a cutoff at P5.

Full derivation: `attentional-foraging/docs/ablations/viewport_bands_cursor_only.md`; historical calibration at [`docs/validation/viewport-bands-calibration.md`](validation/viewport-bands-calibration.md).

---

## 4. What survives, what doesn't — LAB ↔ WILD summary

The repo's central organizational axis (per `CLAUDE.md`) is which findings transfer from the LAB instrumentation stack (pupil → gaze → cursor → scroll → click on AdSERP) to the WILD instrumentation stack (cursor → click on ACD).

| Finding | LAB regime | WILD regime | Status |
|---|---|---|---|
| Click prediction with M4 features | LOSO AUC 0.935 (cursor-only M4-7, `[AR-V1:K-cursor-8]`) | AUC 0.821 ± 0.022 `[AR-V1:K1]` | **`[BOTH]`** |
| Hover-only click prediction (1 feat) | LOSO AUC 0.853 (cursor-only, `m4_cursor_aoi_mousedown` single-feature sweep) | (not yet run on ACD) | `[LAB]` headline; mobile generalization open |
| `min_dist` alone (1 feat) | LOSO AUC 0.872 (same sweep) | (not run alone on ACD; K4 is the WILD univariate at 0.564) | `[LAB]` headline |
| 3-feature no-dwell click prediction | (not run as primary on AdSERP) | AUC 0.798 ± 0.036 `[AR-V1:K2]` | `[WILD]` headline |
| Retreat + viewport bands combined | AUC 0.842 `[AR-V3:K5]` | (TODO: port to ACD) | `[LAB]` for now |
| M5 deferred-class detection | AUC 0.691 `[AR-V2:K-cursor-1]` | structurally uncomputable (single AOI / session) | `[LAB]` only |
| Four-class taxonomy discrimination | possible (gaze-grounded) | structurally uncomputable | `[LAB]` only |
| `vt_top` coefficient rank-dependence | +2.02 → +0.21 across P0–P5 `[AR-V3:K9–K14]` | (no AOI rank structure on ACD) | `[LAB]` only |

**Reading.** The cursor feature family transfers; the gaze-derived class structure does not, and won't until a multi-AOI in-the-wild dataset becomes available. M5 is the current bridge — train against LAB labels, deploy on WILD telemetry.

---

## 5. The AdSERP corpus spans diverse, modern SERP layouts

The rank-position absorption result — M4 drops explicit rank position and loses no predictive power (M3 ≈ M4) — is a *layout-resilience* claim only if the corpus it holds across is itself layout-diverse. It is.

Across all 2,764 AdSERP trials (12 alignment-excluded; re-derived 2026-08-30 on the collision-fixed typed maps), the typed-gapfill AOI maps show **every SERP (100 %) carries at least one non-organic element** — not one trial is a plain ten-blue-links list. A typical page runs **≈16 AOIs spanning a median of 7 distinct element types** (range 2–11), only about half of them organic results.

| Element type | Present in |
|---|---|
| organic results | 100 % of trials |
| native ad | 95.3 % |
| `dd_top` — top ad block, typically a product carousel | 57.0 % |
| image pack | 56.8 % |
| `dd_right` — right-rail ads | 31.0 % |
| people-also-ask | 27.7 % |
| knowledge panel | 27.7 % |

(Plus page furniture present on most trials: pagination 97 %, related-searches 65 %, chrome 48 %.)

These are exactly the elements that break classical position-bias click models — multi-column carousels, image packs, and knowledge panels all disrupt the single-column top-to-bottom scan the position-bias assumption rests on. That M3 ≈ M4 holds across a corpus where *every* page mixes these verticals is the empirical substrate for the layout-resilience claim: the absorption is not an artifact of a uniform ranked list.

Producer: `attentional-foraging/scripts/serp_layout_diversity.py` → `output/serp_layout_diversity/summary.json`.

---

## How citations work

In paper drafts and external prose: cite `[AR-V1:K1]` (etc.). The reader follows the link to [`key-claims.md`](key-claims.md), reads the row, and from there can trace back to the producing script and output. If the prose value disagrees with the K-ID row, the prose is wrong.

This document is the reading layer; [`key-claims.md`](key-claims.md) is the canonical layer; the per-suite docs under [`validation/`](validation/) are the methods layer; the scripts under [`analysis/`](../analysis/) and [`scripts/`](../scripts/) are the execution layer. Numbers flow upward, not downward.
