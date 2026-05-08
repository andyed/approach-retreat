# Findings — approach-retreat

*Narrative summary of the primary results from this repo's three validation suites. Numbers cite stable IDs in [`key-claims.md`](key-claims.md); this document is the reading layer over the canonical table.*

For the theoretical frame (cursor episode decomposition, four-class taxonomy, LAB↔WILD bridge), see [`theory.md`](theory.md). For mechanism details on the forward-vs-regressive split, see [`forward-regressive-split.md`](forward-regressive-split.md). For the 1-pager pitch to non-academic audiences, see [`one-pager.md`](one-pager.md).

---

## 1. Click-prediction signal survives the eye-tracker stripped away

The library's nine cursor approach features were derived against AdSERP's 150 Hz eye-tracker + cursor stream. The natural question is: what survives when you take the eye tracker away?

**Headline (`[AR-V1:K1]`, `[AR-V1:K6]`):** an 11-feature logistic regression on the same feature family reaches AUC 0.821 ± 0.022 for `ad_clicked` on the public Attentive Cursor Dataset (Leiva & Arapakis 2020) — a 954-session native-ad cohort with cursor + click only, no eye tracker, no pupil. That is +0.125 AUC points (+18 % relative) over the standard `total_mouse_length` scalar baseline `[AR-V1:K3]` reported by Brückner et al. (SIGIR '21).

**Cross-dataset transfer `[AR-V1:K8]`.** The pre-cascade AdSERP LAB click-prediction LOSO with the gaze-clean nine-feature M4 extractor was 0.821 `[LAB, AdSERP, absolute legacy, NB21:K3]` — exactly matching the WILD ACD AUC, which produced an evocative "0.821 = 0.821 across two completely different datasets" framing. The 2026-05-01 cascade retired that LAB anchor: M4 LOSO AUC under bbox-organic attribution is now 0.864 `[LAB, AdSERP, organic, NB21:K-bbox-4]` and 0.870 under hybrid attribution. The post-cascade LAB number is +0.043 above WILD; the headline shifts from "same number" to "the cursor-only feature family transfers from LAB to WILD with a modest LAB-favoring gap, consistent with cleaner attribution sharpening the LAB signal." The within-CI agreement is intact (LAB per-fold SD ≈ 0.044; WILD ± 0.022 — overlap is wide); the rhetorical "exact equality" hook does not survive cleaner attribution. WILD AUC `[WILD, attcur]` is rank-type-N/A (single-AOI native ad cohort, no AdSERP-style rank structure).

### The dwell-cheat objection is defused

A skeptical reviewer could read `[AR-V1:K1]` and ask whether the signal is just Fitts mechanics: a user about to click *must* stop the cursor over the target, so dwell-in-target trivially predicts click.

The answer is the 3-feature no-dwell ablation `[AR-V1:K2]`: `min_dist + retreat_dist + ever_in_target` reaches AUC 0.798 ± 0.036 with no dwell feature at all. That's still +0.102 AUC over the scalar baseline `[AR-V1:K7]`. Dwell contributes an additional +0.023 AUC in the full model (the difference between K1 and K2), which is consistent with a small non-mechanical pause component on top of the Fitts baseline — but the geometry-only signal stands without it.

### Attention/noticeability is harder

On the noticed Likert target, the same LR reaches AUC 0.594 ± 0.007 `[AR-V1:K9]`. Brückner's BiLSTM on the analogous task lands in a wide 0.55–0.65 AUC band `[AR-V1:K11]` — the cohort is only 716 sessions with ~77 positives after the Likert filter, so the Wilson CIs are visibly wide. Our LR sits inside that band `[AR-V1:K12]`, which we read as "the linear classifier and the BiLSTM are indistinguishable within confidence intervals" rather than "the linear classifier matches the BiLSTM." An 11-feature LR achieving the same AUC band as a 2-layer BiLSTM with three orders of magnitude fewer parameters and directly interpretable coefficients is a useful engineering finding on this target.

### What this does not prove

- **Not** the four-class deferred-vs-evaluated-rejected taxonomy. ACD has one AOI per session, so the deferred-class structure is uncomputable there. That finding is `[LAB]`-only — see §2 below.
- Not "cursor narrates commitment, not awareness." Earlier framings post-hoc-rationalized the AUC gap between `ad_clicked` and `noticed` as evidence for a commitment-vs-awareness dissociation. That framing has been retracted; the gap is equally consistent with `ad_clicked` being a cleaner objective label than Likert self-report.
- Not geometric curvature as a cognitive signal at this sampling rate. ACD's median ~1 event/sec sampling makes `arc_ratio` geometrically underdetermined; the feature is retained for pipeline consistency but the curvature interpretation has been pulled.

Full discussion at [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md).

---

## 2. M5 — calibrated cursor-only deferred-class detector

The four-class taxonomy (clicked / deferred / evaluated-rejected / not-approached) is `[LAB]`-only by construction: the deferred / evaluated-rejected split requires the gaze-fixation sequence revisiting an earlier result band, which no cursor-only stream provides. M5 closes that gap as a calibration methodology, not as a pre-trained artifact: train a logistic regression once against gaze-derived labels, then deploy at inference time on standard `mousemove` + click telemetry without any eye-tracker dependency.

**On AdSERP — the gaze-clean reference point** `[LAB, AdSERP, organic]` (post-2026-05-01 cascade; trained against bbox-organic NB22 labels via `compute_regression_labels.py --attribution organic`):
- LOSO AUC 0.769 `[AR-V2:K-bbox-1]` at the Youden-*J* threshold *p* = 0.489 `[AR-V2:K-bbox-2]`
- Precision on predicted-deferred pool 87.8 % `[AR-V2:K-bbox-3]`, recall 71.6 % `[AR-V2:K-bbox-4]`, F1 0.789 `[AR-V2:K-bbox-5]`

> Pre-cascade reference (legacy absolute attribution, retired 2026-05-01): LOSO AUC 0.709 / threshold 0.500 / precision 88.9 % / recall 73.0 % / F1 0.802 — preserved as `[AR-V2:K1–K5, absolute legacy]`. The cascade retrained the M5 model on `cursor-approach-features-organic.json` with bbox-derived AOIs; the +0.060 AUC gain reflects cleaner training data, not a different model architecture.

### The supervision-signal finding

The training-target choice (gaze-regression label (NB22 ground truth) vs click label (NB21 thresholded as a non-click splitter)) produces a 1.49 × label-disagreement reduction `[AR-V2:K8]` against NB22 ground truth on the same nine features, same LOSO protocol, same model family. M5 disagrees with NB22 at 29.4 % `[AR-V2:K7]`; the click-trained NB21 baseline disagrees at 43.8 % `[AR-V2:K6]`.

**Reading.** The improvement isn't the classifier — it's the supervision target. A click-trained classifier thresholded post-hoc as a non-click splitter is trained on the wrong target for the deferred-class question. M5 swaps the target without changing the features. This is the key piece of M5.

### LAB diagnostic upper bound — not deployable

A LAB gaze-gated feature extractor (sampling cursor at fixation timestamps) reaches AUC 0.794, F1 0.867, precision 90.2 % / recall 83.4 % `[AR-V2:K9–K12]`, supervision-signal ratio 2.18 × `[AR-V2:K13]`. These are an upper bound, not a target. The fidelity cost of going gaze-clean is −0.040 AUC, −10.4 pt recall, −0.065 F1, ×0.69 supervision-signal ratio `[AR-V2:K14]`. A production deployment cannot reproduce these without an eye tracker; the gaze-clean numbers are the deployable ceiling.

### Class prior caveat

AdSERP's deferred / evaluated-rejected split in the approached-non-click population is 81 % / 19 % `[AR-V2:K15]`. This is not a universal base rate — it's a property of forced-choice 10-result SERP with motivated crowdworker participants. Production traffic with banner-blindness and query abandonment will almost certainly skew differently. Recalibrate the operating threshold against your own class prior.

Full methodology at [`docs/validation/m5-calibration.md`](validation/m5-calibration.md).

---

## 3. Viewport bands carry as much signal as cursor retreat — and combine separably

The library's per-AOI viewport-band features (`vp_any_ms`, `vp_top_ms`, `vp_mid_ms`, `vp_bot_ms`) measure how long an AOI lived in each third of the viewport during a session. The calibration question: do these add anything to the cursor retreat features, or are they redundant?

**Headline `[AR-V3:K1, K3, K5]`:**
- Retreat alone (9 features): bootstrap median AUC 0.796 [0.759, 0.830]
- Viewport bands alone, target AOI (3 features): 0.800 [0.774, 0.828]
- Retreat + bands combined (12 features): AUC 0.842 [0.818, 0.864]

The combined model is separable from retreat-alone at the upper CI (0.842 > 0.830). Bands carry as much signal as the nine-feature cursor retreat set on their own, and the lift from combining is measurable. Fully-contextual viewport (10 AOIs × bands + rank, 40 features) is *worse* than local at AUC 0.748 `[AR-V3:K4]` — the signal is per-AOI, not session-level. The library accordingly emits raw per-AOI band ms only and leaves rank-weighting to consumers.

### Coefficient signs reveal the mechanism

Pooled standardized coefficients on the deferred outcome `[AR-V3:K6–K8]`:
- `vt_top` = +1.83 (top-of-viewport dwell predicts deferred)
- `vt_mid` = +0.83
- `vt_bot` = +0.21

Top-of-viewport dwell is ~9 × more discriminative than bottom-of-viewport dwell. Mechanistically consistent: top-of-viewport is where reading happens; bottom-of-viewport is where scrolling-past happens.

### The rank-dependence finding (P0–P5 only)

`vt_top`'s coefficient is rank-dependent and weakens monotonically with rank `[AR-V3:K9–K14]`:

- P0 (+2.02, strong) → P1 (+1.67, strong) → P2 (+1.48, strong) → P3 (+1.10, strong) → P4 (+0.49, marginal) → P5 (+0.21, CI includes 0 — significance transition)

Past P5 the per-position estimates are too sparse (n ≤ 91 per slice), participant-concentrated (top 4 contributors supply 44 % of the deep-rank bucket), and confounded by deep-rank approach behavior (bottom-of-page ad presence). Deep-rank values are retained in `bootstrap_results.json` for diagnostic use but must not be cited as calibration without a larger-corpus replication.

**Practical implication for consumers.** Weight `vt_top` by rank with a piecewise function or smooth decay over P0–P5. A single pooled weight under-fits P0–P3 and over-fits the P4–P5 transition. If a single band feature is desired, `vt_mid` is the more rank-robust default (+0.5 to +1.2 across P1–P5).

### JS↔Python parity verified

`computeViewportBandsPure` (JS) and `viewport_ms_for_trial` (Python) produce identical output on a six-AOI synthetic fixture covering edge cases (AOI fully above / below viewport, center crossing all thirds during scroll, tall AOI with center off-viewport, zero-duration intervals). All 24 fields match exactly (Δ = 0) `[AR-V3:K15]`. The library tag for this feature is `edmonds-2026-vpbands-v1` `[AR-V3:K16]`.

Full calibration at [`docs/validation/viewport-bands-calibration.md`](validation/viewport-bands-calibration.md).

---

## 4. What survives, what doesn't — LAB ↔ WILD summary

The repo's central organizational axis (per `CLAUDE.md`) is which findings transfer from the LAB instrumentation stack (pupil → gaze → cursor → scroll → click on AdSERP) to the WILD instrumentation stack (cursor → click on ACD).

| Finding | LAB regime | WILD regime | Status |
|---|---|---|---|
| Click prediction with M4 features | LOSO AUC 0.821 (gaze-clean, AF NB21:K3) | AUC 0.821 ± 0.022 `[AR-V1:K1]` | **`[BOTH]`** |
| 3-feature no-dwell click prediction | (not run as primary on AdSERP) | AUC 0.798 ± 0.036 `[AR-V1:K2]` | `[WILD]` headline |
| Retreat + viewport bands combined | AUC 0.842 `[AR-V3:K5]` | (TODO: port to ACD) | `[LAB]` for now |
| M5 deferred-class detection | AUC 0.709 `[AR-V2:K1]` | structurally uncomputable (single AOI / session) | `[LAB]` only |
| Four-class taxonomy discrimination | possible (gaze-grounded) | structurally uncomputable | `[LAB]` only |
| `vt_top` coefficient rank-dependence | +2.02 → +0.21 across P0–P5 `[AR-V3:K9–K14]` | (no AOI rank structure on ACD) | `[LAB]` only |

**Reading.** The cursor feature family transfers; the gaze-derived class structure does not, and won't until a multi-AOI in-the-wild dataset becomes available. M5 is the current bridge — train against LAB labels, deploy on WILD telemetry.

---

## How citations work

In paper drafts and external prose: cite `[AR-V1:K1]` (etc.). The reader follows the link to [`key-claims.md`](key-claims.md), reads the row, and from there can trace back to the producing script and output. If the prose value disagrees with the K-ID row, the prose is wrong.

This document is the reading layer; [`key-claims.md`](key-claims.md) is the canonical layer; the per-suite docs under [`validation/`](validation/) are the methods layer; the scripts under [`analysis/`](../analysis/) and [`scripts/`](../scripts/) are the execution layer. Numbers flow upward, not downward.
