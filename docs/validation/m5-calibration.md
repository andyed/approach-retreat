# M5 Calibration: Training a Cursor-Only Deferred-Class Detector from Behavioral Labels

> **Historical calibration record (2026-09-04).** The 0.794 gaze-gated,
> 0.709 legacy gaze-clean, 0.769 nine-feature organic, and 0.752 seven-feature
> organic results describe distinct runs. They have not all been recalibrated
> after the August measurement corrections. Keep the recipe, feature set,
> population, and training artifact together; use
> [Current evidence](../current-evidence.md) for the current status.

## Current calibration (2026-09-18)

`[LAB, AdSERP, typed, cursor-only, press-anchored 500 ms]`. Producer: `attentional-foraging/scripts/m4_cursor_only_downstream.py` → `scripts/output/m4_cursor_only_downstream/summary.json` (2026-09-06), `section_4_3.deployable_M4_7` and `section_4_2`; transcribed 2026-09-18 as `[AR-V2:K-cursor-1–14]` in [`key-claims.md`](../key-claims.md). The features are the seven-feature M4 vector as this library's `ResultFeatureTracker` computes it (one-dimensional cursor-to-AOI-centre distance on native `mousemove` events, samples within 500 ms of the `mousedown` anchor excluded; no `final_dist`, no `retreat_dist`). Rows are every approached (`min_dist` < 100 px) non-click AOI in an included trial; the target is the NB22 gaze-regression label; LOSO by participant, 47 folds, `StandardScaler` → balanced `LogisticRegression(C=1)`.

| Metric | Value | Sidecar key |
|---|---:|---|
| LOSO pooled AUC | **0.691** | `deployable_M4_7.pooled_auc` |
| Per-fold AUC, mean ± sd | 0.694 ± 0.070 | `deployable_M4_7.fold_auc_mean` / `fold_auc_sd` |
| Youden-*J* operating threshold | *p* = 0.477 | `deployable_M4_7.youden_j.threshold` |
| Precision on predicted-deferred pool | **78.1 %** | `…youden_j.precision` |
| Recall on predicted-deferred pool | **72.8 %** | `…youden_j.recall` |
| F1 on deferred class | **0.753** | `…youden_j.f1` |
| Pool, deferred / evaluated-rejected | 9,932; 6,800 / 3,132 = 68.5 % / 31.5 % | `population.approached_nonclick_pool`, `population.four_class` |
| Click-thresholded partition disagreement vs NB22 | 42.5 % | `section_4_2.disagreement_pct` |
| M5 disagreement vs NB22 | 32.6 % | `section_4_2.deployable_disagreement_pct` |
| Supervision-signal ratio | 1.30 × | 42.5 / 32.6 |
| Matched-row ceiling (cursor sampled at fixation onsets, same 9,911 rows) | 0.715 vs 0.692 native; paired +0.007 [−0.005, +0.020] | `section_4_3.matched_row_ceiling` |

**Class prior.** 68.5 / 31.5 deferred / evaluated-rejected on the cursor-only pool. The 81 / 19 quoted in the historical sections below is the pre-cascade fixation-selected pool, and the typed fixation-selected pool is 85 / 15 (`deferred_drop_decomposition/summary.json`, `rungs.L_full_lab_pool`); rows the eyes never selected are disproportionately evaluated-rejected, so the prior moves with the row-selection rule. Recalibrate the threshold on your own prior either way.

**The historical rows are not cursor-only calibrations.** Every number in the sections below (0.794 gaze-gated, 0.709 legacy, 0.769 nine-feature organic, 0.752 seven-feature organic) was trained on features from `compute_cursor_approach_features.py`, which selects rows by fixation, samples the cursor at fixation times, measures the distance from the *fixation position* to the cursor, and weights proximity dwell by fixation duration. The label is whether the fixation sequence returns to the result, so those features carried part of the label. `deferred_drop_decomposition.py` (2026-09-17; `attentional-foraging/docs/ablations/deferred_drop_decomposition.md`) measures the cost on identical rows and labels: replacing the fixation-selected features with the tracker's costs **−0.068 [−0.116, −0.017]** paired (0.771 → 0.665 pooled on the 3,706 shared rows), while native sampling (−0.002), the 500 ms press buffer (−0.005) and the move to the full cursor pool (+0.012) each stay inside their intervals. The advice below, "do not sample the cursor at fixation timestamps", is correct and incomplete: the distances were fixation-to-cursor too. The historical rows describe the ceiling a gaze-informed feature set reaches, not what this library's extractor produces.

**Deployed model.** `scripts/models/m5_final_model.json` (nine features including `final_dist` and `retreat_dist`, 2,070 fixation-selected episodes, `loso_auc` 0.769, threshold 0.489) was trained on that historical stream, so its scaler statistics and coefficients apply to a feature distribution the runtime tracker does not produce. It is being replaced by `m5_cursor_only_v2.json`: seven features, trained on `cursor-only-typed-features-mousedown.json` (buf500) against the NB22 typed labels, full-data refit after the LOSO gate reproduces 0.691 (another session is producing it; see the 2026-09-18 claims inventory §0). The old file is kept as `m5_final_model.legacy-2026-05-02.json`. Expect the reported AUC to move 0.769 → 0.691 on the swap; the ladder above is the reason, not a regression.

---

**Status:** methodology doc for deployers. Reference numbers are from AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR 2025); production deployments should calibrate against their own data.

---

## What this is

The `approach-retreat` library ships a nine-feature cursor approach extractor (§3.6 of the methods paper; `src/features.ts` in this repo). The features support two downstream tasks:

1. **Click prediction** via a supervised classifier trained on click labels. This is what the M1–M4 models in the paper do. On AdSERP, nine gaze-clean approach features reach LOSO AUC **0.821** (matching a 10-feature position-and-approach baseline at 0.820 within fold SD). On the Attentive Cursor Dataset, an 11-feature version of the same feature family — different task (`ad_clicked`), different population, different feature count — reaches AUC **0.821** against a scalar mouse-length baseline at 0.696. Same feature family, two datasets, gaze-free in both, AUC 0.821 on both.
2. **Deferred-class detection** — identifying episodes in which the user approached a result, examined it, re-examined it, and still chose to decline. This is the hard-negative class the paper describes and is not directly observable from click logs alone.

This document is about task (2). M5 is a **calibration methodology** for training a cursor-only deferred-class detector from a one-time supervised step against behavioral ground truth (eye-tracker fixation data, human relevance annotations, or a webcam-gaze subsample). Once calibrated, M5 runs at inference time on standard `mousemove` + click telemetry with no eye tracker or gaze data in the deployment loop.

**M5 is not a pre-trained classifier you can pip-install.** It is a training recipe and a set of reference numbers. Your deployment calibrates its own M5 instance against its own supervision source.

---

## Why you would want to use it

If you are mining hard negatives for dense-retrieval training from user behavior, the dominant sources (BM25 top-*k*, ANCE model-mined candidates, RocketQA cross-encoder-denoised candidates) all face a contamination failure mode: candidates that look like hard negatives to the retriever are sometimes latent positives the training set mislabels as irrelevant, and training on these pushes the embedding in the wrong direction. Skip-above rules from click logs [Joachims et al. CIKM '05] produce behavioral negatives without model contamination but cannot distinguish "the user carefully considered this result and declined" from "the user never attended to this result at all."

The M5 calibration methodology produces a cursor-only classifier whose predicted-deferred pool contains episodes in which **the user approached a candidate, their gaze-return behavior indicated a second examination, and they still chose to decline**. These are candidates for behavioral supervision. A gaze return is not a human relevance judgment, and the predicted pool has not been validated as an equivalent replacement for annotation or at production scale.

**On AdSERP, the calibration reference point** is `[LAB, AdSERP, organic]` (post-2026-05-01 cascade; M5 retrained against bbox-derived NB22 labels):

| Metric | Value (post-cascade `[organic]`) | Pre-cascade `[absolute legacy]` |
|---|---:|---:|
| LOSO AUC (cursor-only, gaze-clean features) | **0.769** | 0.709 |
| Youden-*J* operating threshold | *p* = 0.489 | *p* = 0.500 |
| Precision on predicted-deferred pool | **87.8 %** | 88.9 % |
| Recall on predicted-deferred pool | **71.6 %** | 73.0 % |
| F1 on deferred class | **0.789** | 0.802 |
| Supervision-signal advantage over click-trained baseline | 1.49 × (legacy; bbox re-derivation pending — the supervision-target argument survives structurally even if the per-class numbers shift) | 1.49 × |

These are **reference numbers for AdSERP's class prior and task design**. Production deployments will see different numbers depending on their own prior; the calibration methodology itself is what transfers.

**Feature-set provenance (2026-08-30 audit).** The post-cascade column above is the 2026-05-02 retrain on the **legacy nine-feature set, including `final_dist` and `retreat_dist`** — the two distance terms since screened as structurally leakage-prone under the click-buffer protocol. A canonical **seven-feature leakage-screened** re-run (2026-05-09, n = 2,067) gives LOSO AUC **0.752**, threshold *p* = 0.449, precision 86.7 %, recall 77.1 %, F1 0.816 `[AR-V2:K-bbox-6–10]`; that run is the current on-disk `attentional-foraging/scripts/output/m5_cursor_only_taxonomy_organic/summary.json` (the 0.769 producer output survives in AF git at `06542d62`, and its model file is the one deployed in this repo). Use the canonical numbers wherever the leakage caveat must not apply; the −0.017 AUC gap is the measured contribution of the two screened features.

---

## Feature requirements

M5 operates on the nine M4 cursor approach features from the `approach-retreat` library. At inference time the library computes these as running aggregates over the `mousemove` event stream with O(1) memory per episode; no trajectory buffer is needed.

The features are:

| Feature | Measures |
|---|---|
| `min_dist` | Closest cursor approach to the result bounding box (px) |
| `mean_dist` | Mean cursor-to-result distance over the trial |
| `final_dist` | Cursor distance at episode end |
| `retreat_dist` | Post-closest-approach drift (`distances[-1] − distances[min_dist_idx]`) |
| `dwell_in_proximity_ms` | Time cursor spent within 100 px of the result |
| `mean_approach_velocity` | Mean rate of change of cursor-to-target distance |
| `max_approach_velocity` | Peak approach velocity |
| `direction_changes` | Number of velocity-sign reversals |
| `frac_decreasing` | Fraction of samples with decreasing distance |

**The feature extractor must be gaze-clean.** In particular, do NOT sample the cursor at fixation timestamps — that inflates training-time signal that production inference cannot reproduce. The paper's Appendix A documents the measurement: a LAB gaze-gated feature extractor reaches M5 precision 90.2 % / recall 83.4 % (F1 0.867), but 10.4 percentage points of the recall advantage cannot be recovered without fixation-timing input at inference time (eye tracker, webcam gaze estimator, or equivalent). The gaze-clean numbers above are the deployable reference point.

**Two feature-extractor options** for a deployment:

1. **Production (recommended):** use the `approach-retreat` library directly. The library binds a standard DOM `mousemove` listener, computes the nine features as running aggregates, and emits a per-episode record via `onEpisode`. It uses CSS-class-based DOM containment for result identification (`data-result` attribute or configurable selector), which is equivalent to the **xpath-grounded arm** of the paper's hybrid extractor (~31 % of AdSERP records, where observed mouse events on a result provide the bounding-box anchor). The paper's remaining ~69 % of records use a linear-fallback bounding box derived from page-height estimation, which is an offline-reconstruction artifact the library does not need: in production, `getBoundingClientRect()` at library initialization gives exact containment for every result by construction, so a library deployment has 100 % xpath-equivalent coverage without any fallback arm.
2. **Offline replay:** if you have archived mouse-event logs and want to train M5 on a historical dataset, use `scripts/m4_nb21_hybrid_rerun.py` from the `attentional-foraging` repo as a template. The script implements the gaze-clean hybrid xpath + linear-fallback extractor used for the paper's §4.3 reference numbers, runs LOSO on a target set of (trial, result) records, and reports precision / recall / F1 for M5 on your data.

---

## Training protocol

M5 is a logistic regression with class-weight-balanced training, LOSO cross-validation by participant (or by session if no participant identifier is available), and a `StandardScaler → LogisticRegression` pipeline to prevent leakage. The training target is a binary `gaze_regression_label` — `True` for episodes where the user's gaze returned to the result for a second examination, `False` otherwise.

```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("lr", LogisticRegression(
        max_iter=5000, class_weight="balanced", C=1.0,
    )),
])
gkf = GroupKFold(n_splits=n_participants)
y_proba = cross_val_predict(
    pipe, X, y, groups=groups, cv=gkf,
    method="predict_proba", n_jobs=1,
)[:, 1]
```

**Where does the supervision label come from?** This is the only step that requires either LAB instrumentation or a behavioral proxy, and it is done once at calibration time — not at deployment time. Four possible routes, with different validation requirements:

1. **Eye-tracker ground truth (highest fidelity, lowest scalability).** Collect a single-session dataset with gaze tracking on your production SERP surface. Compute a gaze-regression label per episode by detecting whether the user's fixation sequence revisits the result band (scroll-high-water-mark rule on page-space fixation Y coordinates). This is what AdSERP's NB22 labels are; see `attentional-foraging/notebooks-v2/22_four_class_taxonomy.ipynb` for the detector.
2. **Human relevance annotations (highest scalability, cheapest, speculative — not yet validated).** Every production search ranker-training pipeline already produces graded relevance judgments on (query, result) pairs. In principle, one could transfer-label M5's training target by aligning the predicted-deferred pool with the "relevant-but-not-ideal" middle of the relevance scale. **We have no empirical evidence that graded relevance labels transfer to the gaze-regression behavioral target**; the two measure different things (annotator's assessment of document quality vs. user's in-session decision to re-examine). This is a research lead, not a tested calibration recipe, and a deployment that chooses this path should validate the transfer against at least one of the other three options before committing to it.
3. **Downstream-task A/B calibration.** Mine hard negatives from M5's output at several candidate thresholds, train the downstream retriever on each, pick the threshold that wins on held-out retrieval metrics. Held-out retrieval performance is the downstream criterion; M5 itself is never explicitly evaluated. This is how ANCE and RocketQA calibrate their hard-negative miners in practice.
4. **Webcam-based gaze estimation.** Consumer webcam gaze estimators (WebGazer.js and similar) are a possible source of coarse revisit labels, but their adequacy must be measured on the target layout and devices. Recruit a small sample (50–200 sessions), label via webcam gaze, train M5. Fidelity is lower than a dedicated eye tracker but higher than transfer labeling, and the hardware cost is zero beyond user consent.

**Class imbalance.** In AdSERP's approached non-click population, 81 % of episodes are deferred and 19 % are evaluated-rejected. Your prior will differ — production traffic with banner-blindness and query abandonment is likely to include a higher evaluated-rejected fraction than forced-choice crowdworker tasks, though this has not been directly measured. Use `class_weight="balanced"` during training, and recalibrate the Youden-*J* operating threshold on your own class prior at deployment time.

---

## Calibrating the operating threshold

M5 outputs `p(deferred)` for each episode at inference time. The operating threshold is a scalar knob you choose based on the precision / recall trade-off your downstream task requires. The AdSERP Youden-*J* threshold post-cascade (`p* = 0.489` under `[organic]`; `p* = 0.500` under `[absolute legacy]`) is a reasonable default, but **you should recalibrate against your own data before deploying**.

Three practical calibration paths for the threshold itself (distinct from the supervision-source options above):

1. **Use the AdSERP default (`p* = 0.500`) as a starting point.** Acceptable for the first deployment; accept the precision / recall that fall out.
2. **Downstream-task A/B.** Set the threshold so that mining hard negatives from M5's output produces the best downstream retrieval metric on a held-out set.
3. **Per-deployment eye-tracked calibration sample.** Collect 50–200 eye-tracked sessions on your SERP surface, compute NB22-style gaze-regression labels, measure M5's precision / recall on that sample, and pick the threshold that matches your target operating point.

---

## What to expect

### On AdSERP (reference calibration)

Gaze-clean hybrid feature extractor (99.8 % population coverage, mousemove-only, no gaze data):

| Setting | Value |
|---|---:|
| LOSO AUC | 0.709 |
| Youden-*J* threshold | *p* = 0.500 |
| Precision (deferred) | 88.9 % |
| Recall (deferred) | 73.0 % |
| F1 (deferred) | 0.802 |
| NB21 baseline disagreement vs. NB22 | 43.8 % |
| M5 disagreement vs. NB22 | 29.4 % |
| Supervision-signal ratio (NB21 / M5) | 1.49 × |

### LAB diagnostic upper bound (not deployable)

For comparison, a LAB gaze-gated feature extractor (fixation-timed cursor sampling, **not production-deployable**) reaches:

| Setting | Value |
|---|---:|
| LOSO AUC | 0.794 |
| Precision (deferred) | 90.2 % |
| Recall (deferred) | 83.4 % |
| F1 (deferred) | 0.867 |
| Supervision-signal ratio | 2.18 × |

**The LAB numbers are an upper bound, not a target.** The fidelity cost of removing fixation gating is 0.040 AUC, 10.4 pt recall, 0.065 F1, and 0.69× supervision-signal ratio. A production deployment cannot reproduce the LAB numbers without deploying an eye tracker, and the LAB figures are reported here only so a deployer knows what the ceiling is.

### On the Attentive Cursor Dataset (Leiva & Arapakis 2020, ACD)

ACD has no eye-tracker data and single-AOI sessions, so the deferred-class taxonomy is structurally uncomputable. The ACD result is therefore about the underlying cursor-feature family, not about M5 specifically: an 11-feature LR on the approach feature family reaches AUC 0.821 on `ad_clicked` vs. 0.696 for a scalar mouse-length baseline. This matches the AdSERP gaze-clean M4 click-prediction AUC of 0.821 exactly and establishes the feature family transfers across datasets and subject populations without gaze data.

---

## What NOT to do

1. **Do not use M5 as a symmetric two-way partitioner.** M5 is a deferred-class detector. Its predicted *evaluated-rejected* pool has substantially lower precision than its predicted-deferred pool — more than half of its eval-rejected predictions are true deferreds M5 missed at the Youden-*J* operating point. If your downstream task needs the evaluated-rejected class, either use NB22 direct labeling (eye-tracker required) or fall back to the NB21 classifier-threshold cut on the same features.
2. **Do not expect the LAB reference numbers in production.** The 2.18 × supervision-signal ratio and the 90.2 %/83.4 % precision/recall are measured on a LAB gaze-gated feature extractor that production deployments cannot reproduce. The gaze-clean reference point (1.49 ×, 88.9 % / 73.0 %) is the deployable ceiling, and even that is AdSERP-calibrated; your deployment will see different numbers.
3. **Do not train M5 at inference time.** Training uses the behavioral supervision source and is a one-time cost; inference applies the frozen trained classifier to incoming cursor telemetry with no labels of any kind in the loop. A production deployment recalibrates M5 periodically (weekly / monthly) as the class prior drifts, but it does not re-derive the supervision labels on every request.
4. **Do not use M5's output as a hard-negative label without a subsequent quality check.** The predicted-deferred pool has 88.9 % precision at the AdSERP reference point, meaning ~11 % of predictions are actually evaluated-rejected episodes that got misclassified. These are still non-click episodes, but they are softer hard negatives than true deferreds. A cross-encoder denoising step (RocketQA-style) on top of M5's output closes this gap further if your downstream retrieval task is sensitive to it.
5. **Do not treat AdSERP's 81 / 19 deferred / evaluated-rejected class ratio as a universal base rate.** It is a property of the forced-choice 10-result SERP with motivated crowdworker participants. Your production traffic's ratio will differ, possibly substantially.

---

## Reproducing the AdSERP reference numbers

The calibration was run on AdSERP in the companion `attentional-foraging` repo. To reproduce the reference numbers in this document:

```bash
cd attentional-foraging
uv run python scripts/m4_nb21_hybrid_rerun.py
```

The script:

1. Loads the 13,419 AdSERP per-(trial, result) records from `AdSERP/data/cursor-approach-features.json` for ground-truth click labels and trial metadata.
2. Loads NB22 gaze-regression labels from `scripts/output/approach_threshold_sensitivity/regression_labels_cache.json`.
3. Computes gaze-clean hybrid features per trial using xpath-grounded DOM containment when mouse events indicate on-result hover, and linear band-top fallback otherwise. 99.8 % coverage.
4. Runs LOSO M1 / M2 / M3 / M4 click prediction (the task-model thesis result).
5. Runs the NB21 classifier-threshold taxonomy on M4 output for the baseline comparison.
6. Runs M5 (LOSO LR on the same features with `gaze_regression_label` as target) for the calibration reference.
7. Writes `scripts/output/m4_nb21_hybrid_rerun/summary.json` with all numbers.

Runtime: ~30 seconds on a modern laptop (features are cached after the first run).

---

## References

- The methods paper (submitted; full citation on acceptance).
- Latifzadeh, K., Gwizdka, J. & Leiva, L. A. (2025). *The AdSERP Dataset.* SIGIR '25.
- Leiva, L. A. & Arapakis, I. (2020). *The Attentive Cursor Dataset.* *Front. Hum. Neurosci.* 14:565664.
- Joachims, T., Granka, L., Pan, B., Hembrooke, H. & Gay, G. (2005). *Accurately interpreting clickthrough data as implicit feedback.* SIGIR '05.
- Xiong, L., Xiong, C., Li, Y. et al. (2021). *Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval.* ICLR '21.
- Qu, Y., Ding, Y., Liu, J. et al. (2021). *RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering.* NAACL '21.
