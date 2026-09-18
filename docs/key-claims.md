# Key Claims — approach-retreat

> **Measurement-version notice (2026-09-18).** These stable IDs preserve the
> validation runs and model configurations that produced them; superseded
> rows keep their IDs and carry a dated note. The 2026-09-18 claims
> inventory ([validation/2026-09-18-claims-inventory.md](validation/2026-09-18-claims-inventory.md))
> checked every row against the producer now standing behind it: the LAB
> M5 / V2 / V3 rows dated before September were computed on a
> fixation-selected feature stream (rows chosen by fixation, cursor sampled
> at fixation times, fixation-to-cursor distance), not on the tracker's
> cursor-only features. The current cursor-only rows are the `K-cursor-*`
> and `K-ladder-*` blocks below; [Current evidence](current-evidence.md)
> carries the checked outputs. V3 has not been re-derived on the cursor-only
> pool. WILD remains a separate binary-click validation, not four-class
> validation.

*Aggregated load-bearing numbers from this repo's validation suites, with stable IDs for citation.*

## What this document is for

Every quantitative claim that ships from this repo to a paper, a README, a slide deck, or another lab gets a stable K-ID here. Prose elsewhere cites the K-ID; this document transcribes the value for that run. A superseding producer output takes precedence until its row is updated.

### The contract

- **If prose in a paper draft cites a value that disagrees with a row below, the prose is wrong** — not the validation script. The validation script is canonical; this aggregate is a transcription of the script outputs.
- **K-IDs are never renumbered.** Adding a new row gets a new K-ID. Retired claims get marked `(retired YYYY-MM-DD: reason)` but keep the ID.
- **Cite as `[AR-V#:K##]`** in prose — `V1` indexes the validation suite (V1 = Brückner ACD, V2 = M5 calibration, V3 = viewport bands), `K##` indexes the row within that suite.
- **Every row points at the script and output that produced it** so any reader can re-derive the value from raw data.

### Validation suites covered

- [V1: Brückner-ACD click-prediction replication](#v1-brückner-acd-click-prediction-replication) — `analysis/attcur-validation/`
- [V2: M5 calibration (deferred-class detector)](#v2-m5-calibration-deferred-class-detector) — `docs/validation/m5-calibration.md`
- [V3: Viewport-band calibration](#v3-viewport-band-calibration) — `docs/validation/viewport-bands-calibration.md`

### LAB / WILD regime tags + rank-type axis

Every row carries **two tags**: a regime tag (LAB/WILD) and a rank-type tag (post-2026-05-01 cascade). The rank-type tag identifies which AdSERP AOI-attribution flavor produced the upstream data; see [`attentional-foraging/docs/methodology/aoi-coverage-contribution.md` §4](https://github.com/andyed/attentional-foraging/blob/main/docs/methodology/aoi-coverage-contribution.md) for the canonical definitions.

Regime:
- **`[WILD, attcur]`** — Attentive Cursor Dataset (Leiva & Arapakis 2020), cursor + click only, no eye tracker, no pupil.
- **`[LAB, AdSERP]`** — AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR 2025), 47 participants, 150 Hz gaze + pupil + cursor.
- **`[BOTH]`** — same statistic computed in both regimes.

Rank-type (LAB-side only; WILD has no AOI-rank structure beyond the single native ad):
- **`absolute`** — legacy h3 + ads pooled, band-estimated AOIs (pre-2026-05-01).
- **`organic`** — bbox organics only, ads excluded (post-cascade primary).
- **`organic_hybrid`** — bbox organics + dd_top + native_ad in display order.
- **`rank-type-N/A`** — claim is rank-type-independent (single-AOI WILD; library JS↔Python parity tests; time-series with no AOI-rank structure).
- **`absolute legacy`** — pre-cascade values retained for historical comparison; cite with the cascade date so a reader knows the retirement context.

A K-ID without a rank-type tag (where one applies) is a citation bug. K-IDs are never renumbered; cascade-superseded rows get a new `K-bbox-#` row alongside the legacy and the legacy gets marked `(absolute legacy)`.

> **2026-08-30 substrate note.** AF's typed-flavor substrate was re-derived twice in late August (2026-08-28 y-DP realignment; 2026-08-30 AOI card-collision fix, corpus 2,776 → 2,764 with 12 alignment exclusions). **V1, V2, and V3 below are unmoved by both passes — by design, not by omission**: V1 is `[WILD, attcur]` (no AdSERP input at all), and V2/V3 are computed on the `organic` flavor, whose AOI maps were untouched by the typed-map realignment and collision fix. Rows citing typed-flavor AF artifacts (regression labels, replay surface) were re-derived 2026-08-30 and say so inline.

---

## V1: Brückner-ACD click-prediction replication

Source: [`analysis/attcur-validation/run_analysis.py`](../analysis/attcur-validation/run_analysis.py)
Output: [`analysis/attcur-validation/results.txt`](../analysis/attcur-validation/results.txt)
Doc: [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md)
Dataset: 954-session native-ad subset of ACD (Leiva & Arapakis 2020)
Protocol: 60/10/30 stratified split, 5 random seeds, weighted F1 + AUC-ROC reported as mean ± std.

### Click-prediction headlines (target = `ad_clicked`, 30.3 % positive)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| **AR-V1:K1** | Approach-retreat 11-feature LR | **AUC 0.821 ± 0.022** · F1ʷ 0.732 ± 0.011 | `[WILD, attcur]` |
| **AR-V1:K2** | 3-feature no-dwell subset (`min_dist + retreat_dist + ever_in_target`) | **AUC 0.798 ± 0.036** · F1ʷ 0.649 ± 0.019 | `[WILD, attcur]` |
| AR-V1:K3 | Brückner SIGIR '21 scalar baseline (`total_mouse_length` only) | AUC 0.696 ± 0.031 · F1ʷ 0.543 ± 0.004 | `[WILD, attcur]` |
| AR-V1:K4 | `min_dist` univariate baseline | AUC 0.564 ± 0.032 · F1ʷ 0.520 ± 0.012 | `[WILD, attcur]` |
| AR-V1:K5 | Geometry-only (no dwell, no min_dist): `retreat_dist + retreat_path + arc_ratio` | AUC 0.705 ± 0.020 · F1ʷ 0.586 ± 0.016 | `[WILD, attcur]` |
| AR-V1:K6 | Lift of K1 over K3 (full LR vs scalar baseline) | +0.125 AUC (+18 % relative) | `[WILD, attcur]` |
| AR-V1:K7 | Lift of K2 over K3 (3-feature no-dwell vs scalar baseline) | +0.102 AUC (+15 % relative) | `[WILD, attcur]` |
| AR-V1:K8 | Cross-dataset alignment: K1 (WILD) vs AdSERP M4 click-prediction LOSO AUC | (retired 2026-05-01: cascade replaced LAB anchor — see K-bbox-8) | `[BOTH, absolute legacy]` |
| AR-V1:K-bbox-8 | Cross-dataset transfer: K1 (WILD, AUC 0.821) vs AdSERP M4 LOSO AUC under bbox-organic attribution | 0.821 (WILD) vs 0.864 (LAB, AF NB21:K-bbox-4); +0.043 LAB-favoring gap (superseded 2026-09-18: the LAB anchor is the fixation-selected organic stream; see K-cursor-8) | `[BOTH]` LAB rank-type `organic` |
| **AR-V1:K-cursor-8** | Cross-dataset transfer: K1 (WILD, AUC 0.821) vs AdSERP M4-7 LOSO AUC on the cursor-only stream | 0.821 (WILD) vs **0.935** (LAB typed, `m4_cursor_aoi_mousedown/summary.json` `conditions.buf500.M4-7.pooled_auc`, fold 0.937 ± 0.023, 2,608 clicked trials); 0.928 under the `organic` flavour on the same protocol (`m4_cursor_aoi_flavor_organic/summary.json`, 2,227 clicked trials). +0.114 LAB-favoring gap; the two tasks differ (multi-AOI SERP vs single native ad), so this is a transfer statement, not an equality | `[BOTH]` LAB `[typed, cursor-only, press-anchored 500 ms]` |

### Attention/noticeability headlines (target = `noticed`, 69.5 % positive)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V1:K9 | Approach-retreat 11-feature LR | AUC 0.594 ± 0.007 · F1ʷ 0.602 ± 0.007 | `[WILD, attcur]` |
| AR-V1:K10 | 3-feature no-dwell subset | AUC 0.587 ± 0.019 · F1ʷ 0.621 ± 0.011 | `[WILD, attcur]` |
| AR-V1:K11 | Brückner BiLSTM AUC band on the noticed/attention task (Figure 2(a), 716-session cut) | 0.55–0.65 (Wilson CIs visibly wide on ~77 positives) | `[WILD, attcur]` |
| AR-V1:K12 | K9 sits inside K11 band | "Indistinguishable within confidence intervals" — not a point-AUC equality | `[WILD, attcur]` |

### Feature importance (full LR on `ad_clicked`, top 5)

| K-ID | Feature | Standardized coefficient | Direction |
|---|---|---:|---|
| AR-V1:K13 | `n_events` | −1.35 | → skip (general session agitation, nuisance regressor) |
| AR-V1:K14 | `dwell_in_target_ms` | +0.95 | → click (partly Fitts-mechanics; defused by K2's no-dwell ablation) |
| AR-V1:K15 | `retreat_dist` (attcur definition) | −0.72 | → skip (larger post-min excursion = less likely to click) |
| AR-V1:K16 | `ever_in_target` | +0.70 | → click |
| AR-V1:K17 | `n_target_entries` | +0.62 | → click |

### Bands extension (added 2026-04-19)

Source: [`analysis/attcur-validation/run_bands_analysis.py`](../analysis/attcur-validation/run_bands_analysis.py) · Output: [`results_bands.txt`](../analysis/attcur-validation/results_bands.txt)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V1:K18 | Retreat-alone (11 features) on `ad_clicked` | AUC 0.823 ± 0.013 | `[WILD, attcur]` |
| AR-V1:K19 | Bands-alone (6 features) on `ad_clicked` | AUC 0.828 ± 0.028 | `[WILD, attcur]` |
| AR-V1:K20 | Retreat + bands combined (17 features) on `ad_clicked` | **AUC 0.859 ± 0.013** | `[WILD, attcur]` |

---

## V2: M5 calibration (deferred-class detector)

Source: [`scripts/m5_inference.py`](../scripts/m5_inference.py) for inference. Current calibration producer: upstream `attentional-foraging/scripts/m4_cursor_only_downstream.py` → `scripts/output/m4_cursor_only_downstream/summary.json` (2026-09-06); ladder producer `scripts/deferred_drop_decomposition.py` → `scripts/output/deferred_drop_decomposition/summary.json` (2026-09-17). Historical rows: `m4_nb21_hybrid_rerun.py`.
Doc: [`docs/validation/m5-calibration.md`](validation/m5-calibration.md)
Target: NB22 `gaze_regression_label` (deferred = gaze returned for second examination)
Population: 9,932 approached (`min_dist` < 100 px) non-click rows on the cursor-only stream (current); the historical rows used 2,351 / 2,070 / 2,067 fixation-selected episodes

### Cursor-only stream (current, 2026-09-06 producer, transcribed 2026-09-18) `[LAB, AdSERP, typed, cursor-only, press-anchored 500 ms]`

Features are the seven-feature M4 vector as the library's `ResultFeatureTracker` computes it: one-dimensional cursor-to-AOI-centre distance on native `mousemove` events, samples within 500 ms of the `mousedown` anchor excluded, typed AOI maps (AllSERP v1.1.0). Every row is an approached non-click AOI in an included trial; no gaze input at any stage. LOSO by participant (47 folds), `StandardScaler` → balanced `LogisticRegression(C=1)`. Values are transcribed from the sidecar keys named in each row; prose rounds to three decimals.

| K-ID | Claim | Value | Sidecar key |
|---|---|---:|---|
| **AR-V2:K-cursor-1** | M5 LOSO pooled AUC, deployable M4-7 | **0.691** | `section_4_3.deployable_M4_7.pooled_auc` (0.69107) |
| AR-V2:K-cursor-2 | Per-fold AUC, mean ± sd (median) | 0.694 ± 0.070 (0.705) | `…deployable_M4_7.fold_auc_mean` / `fold_auc_sd` / `fold_auc_median` |
| AR-V2:K-cursor-3 | Youden-*J* operating threshold | *p* = 0.477 | `…deployable_M4_7.youden_j.threshold` (0.47672) |
| AR-V2:K-cursor-4 | Precision on predicted-deferred pool | 78.1 % | `…youden_j.precision` (0.78118) |
| AR-V2:K-cursor-5 | Recall on predicted-deferred pool | 72.8 % | `…youden_j.recall` (0.72765) |
| AR-V2:K-cursor-6 | F1 on deferred class | 0.753 | `…youden_j.f1` (0.75346) |
| AR-V2:K-cursor-7 | Pool size and class prior (deferred / evaluated-rejected) | 9,932 rows; 6,800 / 3,132 = **68.5 % / 31.5 %** | `population.approached_nonclick_pool`, `population.four_class.deferred` / `eval_rejected` |
| AR-V2:K-cursor-8 | Matched-row ceiling: gaze-gated cursor sampling (cursor at fixation onsets) vs native, same 9,911 rows, same labels, anchor and buffer | gaze-gated **0.715** vs native 0.692; paired participant Δ +0.007 [−0.005, +0.020], Wilcoxon *p* = 0.24 | `section_4_3.matched_row_ceiling.gaze_gated_ceiling.pooled_auc` (0.71511), `…deployable_native_on_shared_rows.pooled_auc` (0.69216), `…paired_ceiling_minus_deployable` |
| AR-V2:K-cursor-9 | Leave-one-feature-out, Δ pooled AUC vs the full seven | `mean_dist` **−0.055**; `dwell_in_proximity_ms` −0.009; `min_dist` −0.001; `max_approach_velocity` −0.001; `mean_approach_velocity` +0.001; `direction_changes` +0.002; `frac_decreasing` 0.000 | `section_4_3.leave_one_feature_out.<feature>.delta_pooled_auc_vs_full` |
| AR-V2:K-cursor-10 | Minimal four (`mean_dist`, `dwell_in_proximity_ms`, `min_dist`, `direction_changes`) vs the full seven | 0.691 vs 0.691; paired Δ +0.001 [−0.003, +0.005], *p* = 0.58 | `section_4_3.minimal_four.pooled_auc` (0.69061), `…paired_vs_M4_7` |
| AR-V2:K-cursor-11 | Click-thresholded partition (LOSO M4-7 click classifier, Youden-*J* on OOF probabilities) disagreement vs NB22 ground truth | 42.5 % | `section_4_2.disagreement_pct` (42.489) |
| AR-V2:K-cursor-12 | Deployable M5 (K-cursor-1 at K-cursor-3) disagreement vs NB22 ground truth | 32.6 % (34.6 % at *p* = 0.5) | `section_4_2.deployable_disagreement_pct` (32.602), `…deployable_disagreement_pct_at_0_5` |
| **AR-V2:K-cursor-13** | Supervision-signal advantage of K-cursor-12 over K-cursor-11 | **1.30 ×** label-disagreement reduction | 42.489 / 32.602 |
| AR-V2:K-cursor-14 | Click-thresholded split of the same pool vs the gaze-regression split | 4,840 / 5,092 (48.7 % deferred) vs 6,800 / 3,132 (68.5 %); Jaccard on evaluated-rejected 0.322 | `section_4_2.click_thresholded_split`, `…gaze_regression_split`, `…jaccard_eval_rejected` |

### The ladder: why the fixation-selected rows scored 0.75–0.77 `[LAB, AdSERP, typed]`

Producer `deferred_drop_decomposition.py` (2026-09-17), read with `attentional-foraging/docs/ablations/deferred_drop_decomposition.md`. Each rung changes one thing; the first three cursor-only rungs use the same 3,706 rows as the LAB rung. The final rung reproduces K-cursor-1 to 1e-6 (`gate.abs_diff` = 0.0).

| K-ID | Rung | Rows | Pooled AUC | Fold mean ± sd | Sidecar key |
|---|---|---:|---:|---:|---|
| AR-V2:K-ladder-1 | L · LAB typed: fixation-selected rows, fixation-to-cursor distance at fixation times, click-anchored buf500 (full LAB pool, 3,297 / 578) | 3,875 | 0.764 | 0.751 ± 0.119 | `rungs.L_full_lab_pool.pooled_auc` (0.76431) |
| **AR-V2:K-ladder-2** | L · same, restricted to the shared rows (3,148 / 558) | 3,706 | **0.771** | 0.757 ± 0.121 | `rungs.L_shared_rows.pooled_auc` (0.77091) |
| AR-V2:K-ladder-3 | G0 · cursor-only tracker features, cursor sampled at fixation onsets, buf0 | 3,706 | 0.665 | 0.689 ± 0.142 | `rungs.G0.pooled_auc` (0.66489) |
| AR-V2:K-ladder-4 | N0 · cursor-only, native sampling, buf0 | 3,706 | 0.663 | 0.687 ± 0.154 | `rungs.N0.pooled_auc` (0.66312) |
| AR-V2:K-ladder-5 | N5 · cursor-only, native sampling, press-anchored buf500 | 3,706 | 0.659 | 0.682 ± 0.156 | `rungs.N5.pooled_auc` (0.65886) |
| **AR-V2:K-ladder-6** | C · cursor-only, native, buf500, full approached non-click pool (= K-cursor-1) | 9,932 | **0.691** | 0.694 ± 0.070 | `rungs.C.pooled_auc` (0.69107) |

| K-ID | Step | What changes | Paired participant Δ, 95 % CI, Wilcoxon *p* | Sidecar key |
|---|---|---|---:|---|
| **AR-V2:K-ladder-7** | L → G0 | feature definition (fixation-to-cursor at fixation times → tracker's cursor-to-centre) | **−0.068 [−0.116, −0.017]**, *p* = 0.014 | `steps_paired_participant."L → G0 …"` (−0.06751) |
| AR-V2:K-ladder-8 | G0 → N0 | sampling, fixation onsets → native | −0.002 [−0.021, +0.016], *p* = 0.85 | `…"G0 → N0 …"` |
| AR-V2:K-ladder-9 | N0 → N5 | press buffer, 0 → 500 ms | −0.005 [−0.012, +0.002], *p* = 0.28 | `…"N0 → N5 …"` |
| AR-V2:K-ladder-10 | N5 → C | rows, fixation-selected → full cursor pool | +0.012 [−0.026, +0.052], *p* = 0.67 | `…"N5 → C …"` |
| AR-V2:K-ladder-11 | Class prior by pool | LAB fixation-selected pool 85 / 15 (3,297 / 578); full cursor pool 68.5 / 31.5 (6,800 / 3,132) | — | `rungs.L_full_lab_pool.n_deferred` / `n_rejected`; `rungs.C` |
| AR-V2:K-ladder-12 | Standoff threshold on C (approached = `min_dist` < px) | 50 px 0.690 (7,849 rows); 100 px 0.691 (9,932); 200 px 0.701 (12,710) | — | `standoff_threshold_on_C` |

Reading: the drop from ~0.77 to 0.69 is the feature definition (K-ladder-7); sampling, buffer and population each move under 0.01 and inside their intervals. The LAB stream's `mean_dist` and `min_dist` were distances from the fixation position to the cursor, sampled at fixation times, and its `dwell_in_proximity_ms` was weighted by fixation duration; the label is whether the fixation sequence returns to the result, so those features carried part of the label. The organic-flavour LAB rung on the current cache is 0.724 on 2,464 rows (`organic_rung.summary.pooled_auc`), which is where the May 0.752 / 0.769 figures sit in this lineage.

### Gaze-clean reference numbers (deployable — no eye tracker at inference)

### Historical rows (fixation-selected feature lineage; superseded 2026-09-18)

**Post-2026-05-01 cascade** `[LAB, AdSERP, organic]` (M5 retrained against bbox-derived NB22 labels via `compute_regression_labels.py --attribution organic`). The features behind every row in this subsection were computed by `compute_cursor_approach_features.py`: rows selected by fixation, cursor sampled at fixation times, fixation-to-cursor distance, fixation-weighted dwell. The ladder (K-ladder-7) puts the cost of that definition at −0.068 on identical rows. These are not cursor-only calibrations; the IDs are kept for citation history.

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K-bbox-1 | M5 LOSO AUC (legacy 9-feature set) | 0.769 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-1) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-2 | Youden-*J* operating threshold | *p* = 0.489 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-3) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-3 | Precision on predicted-deferred pool | 87.8 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-4) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-4 | Recall on predicted-deferred pool | 71.6 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-5) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-5 | F1 on deferred class | 0.789 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-6) | `[LAB, AdSERP, organic]` |

**Feature-set provenance (audited 2026-08-30).** K-bbox-1–5 come from the 2026-05-02 organic retrain (n = 2,070 episodes) on the **legacy nine-feature M4 set, which includes `final_dist` and `retreat_dist`** — the two distance terms later screened as structurally leakage-prone under the click-buffer protocol (the CIKM R1-W2 caveat). That run's model file is the one deployed at `scripts/models/m5_final_model.json` in this repo (`loso_auc` 0.7686, threshold 0.489 — matches these rows). AF's on-disk `m5_cursor_only_taxonomy_organic/summary.json` was **overwritten on 2026-05-09** by the canonical leakage-screened re-run below, so it no longer matches K-bbox-1–5; recover the 0.769 producer output from AF git (`06542d62`).

**Leakage-screened variant** `[LAB, AdSERP, organic]` (2026-05-09 producer refresh; seven-feature M4 set, `final_dist`/`retreat_dist` dropped; n = 2,067; on-disk `m5_cursor_only_taxonomy_organic/summary.json`). Same fixation-selected feature lineage as K-bbox-1–5; for head-to-head baseline tables use K-cursor-1–6:

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K-bbox-6 | M5 LOSO AUC (canonical 7-feature set) | 0.752 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-1) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-7 | Youden-*J* operating threshold | *p* = 0.449 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-3) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-8 | Precision on predicted-deferred pool | 86.7 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-4) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-9 | Recall on predicted-deferred pool | 77.1 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-5) | `[LAB, AdSERP, organic]` |
| AR-V2:K-bbox-10 | F1 on deferred class | 0.816 (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-6) | `[LAB, AdSERP, organic]` |

The 0.769 → 0.752 delta (−0.017 AUC) is the measured cost of removing the two leakage-prone distance terms on the fixation-selected stream. The deployed model file `scripts/models/m5_final_model.json` is the nine-feature 2026-05-02 fit (K-bbox-1–5) and is being replaced by `m5_cursor_only_v2.json`, a seven-feature fit on the cursor-only stream gated on reproducing K-cursor-1 (inventory §0).

**Pre-cascade reference (legacy)** `[LAB, AdSERP, absolute legacy]` — retired 2026-05-01; preserved for historical comparison:

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K1 | M5 LOSO AUC (legacy) | 0.709 (retired 2026-05-01: cascade replacement K-bbox-1 = 0.769) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K2 | Youden-*J* operating threshold (legacy) | *p* = 0.500 (retired) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K3 | Precision (legacy) | 88.9 % (retired) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K4 | Recall (legacy) | 73.0 % (retired) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K5 | F1 (legacy) | 0.802 (retired) | `[LAB, AdSERP, absolute legacy]` |

**Disagreement-vs-ground-truth (historical; current rows are K-cursor-11–14):**

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K6 | NB21-classifier-threshold disagreement vs NB22 ground truth | 43.8 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-11) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K7 | M5 disagreement vs NB22 ground truth | 29.4 % (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-12) | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K8 | Supervision-signal advantage of K7 over K6 | 1.49 × label-disagreement reduction (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-13, 1.30 ×) | `[LAB, AdSERP, absolute legacy]` |

### LAB diagnostic upper bound (gaze-gated extractor — not deployable)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K9 | LOSO AUC | 0.794 | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K10 | Precision (deferred) | 90.2 % | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K11 | Recall (deferred) | 83.4 % | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K12 | F1 (deferred) | 0.867 | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K13 | Supervision-signal ratio | 2.18 × | `[LAB, AdSERP, absolute legacy]` |
| AR-V2:K14 | Fidelity cost of going gaze-clean (K1 vs K9) | −0.085 AUC *(corrected 2026-08-30: prior value −0.040 did not match the stated K1-vs-K9 pairing, 0.794 − 0.709 = 0.085)*, −10.4 pt recall, −0.065 F1, ×0.69 supervision-signal ratio | `[LAB, AdSERP, absolute legacy]` |

*(Rank-type added 2026-08-30 provenance audit: K9–K14 were produced 2026-04-14 on the pre-cascade `absolute` substrate with the fixation-timed (gaze-gated) extractor — source `m5_cursor_only_taxonomy/summary.json`, n = 2,355. Doubly non-current: retired attribution **and** non-deployable extractor. Cite only as the diagnostic ceiling, never as an M5 headline. The current comparator is K-cursor-8: on the cursor-only stream, gaze-gated sampling reaches 0.715 against 0.692 native on the same 9,911 rows, paired +0.007 with a CI spanning zero.)*

### Class prior on AdSERP (calibration reference, not universal base rate)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K15 | Deferred / evaluated-rejected split in approached-non-click population | 81 % / 19 % (superseded 2026-09-18: fixation-selected pool; the cursor-only pool is 68.5 / 31.5, see K-cursor-7 and K-ladder-11) | `[LAB, AdSERP, absolute legacy]` |

---

## V3: Viewport-band calibration

> **Re-derived 2026-09-18 on the cursor-only pool.** Every row below the
> "Cursor-only pool" block was computed on the fixation-selected LAB pool
> with the nine-feature LAB retreat vector (superseded 2026-09-18:
> fixation-selected feature lineage; see K-cursor-*). Producer for the
> current rows: `attentional-foraging/scripts/viewport_bands_cursor_only.py`
> → `scripts/output/viewport_bands_cursor_only/summary.json`; note
> `docs/ablations/viewport_bands_cursor_only.md`.

Source (historical rows): [`attentional-foraging/scripts/viewport_bands_bootstrap.py`](../../attentional-foraging/scripts/viewport_bands_bootstrap.py)
Doc: [`docs/validation/viewport-bands-calibration.md`](validation/viewport-bands-calibration.md)
Outcome: NB22 `gaze_regression_label` (1 = deferred, 0 = evaluated-rejected)

### Cursor-only pool — current `[LAB, AdSERP, typed, cursor-only, press-anchored 500 ms]` (2026-09-18)

Pool: the 9,932 approached non-click rows of `m4_cursor_only_downstream` (6,800 deferred / 3,132 rejected), 47 participants; bands = cumulative ms the AOI centre spends in each viewport third, screenshot space, window cut at `mousedown` − 500 ms; gate: cursor M4-7 reproduces 0.6911 exactly. Within-trial AUC = P(deferred scored above rejected) over pairs inside one trial.

| K-ID | Model | Features | Pooled AUC | Within-trial AUC | JSON key |
|---|---|---:|---:|---:|---|
| **AR-V3:K-cursor-1** | Cursor M4-7 alone | 7 | 0.691 | 0.718 | `models.cursor_M4_7` |
| AR-V3:K-cursor-2 | `vp_any` alone | 1 | 0.746 | 0.720 | `models.vp_any` |
| **AR-V3:K-cursor-3** | Bands alone (`vt_top`, `vt_mid`, `vt_bot`) | 3 | **0.789** | **0.773** | `models.bands_3` |
| **AR-V3:K-cursor-4** | Cursor + bands | 10 | 0.789 | 0.776 | `models.cursor_M4_7_plus_bands_3` |
| AR-V3:K-cursor-5 | Bands, raw 1024 px screen height (sensitivity) | 3 | 0.797 | 0.777 | `models.bands_3_raw_screen_height` |
| AR-V3:K-cursor-6 | Paired by participant, bands − cursor | | +0.082 [+0.064, +0.100] | | `paired_by_participant` |
| AR-V3:K-cursor-7 | Paired, combined − bands | | +0.006 [+0.002, +0.011] | | `paired_by_participant` |
| AR-V3:K-cursor-8 | Coefficients, bands alone, standardized (+ = deferred) | | `vt_top` +1.45 · `vt_mid` +0.83 · `vt_bot` +0.28 | | `coefficients.bands_3` |
| AR-V3:K-cursor-9 | `vt_top` by position P0–P5, 1,000 participant-cluster draws | | +1.40 [+1.05, +1.88] · +1.27 [+1.02, +1.57] · +0.90 [+0.73, +1.13] · +0.74 [+0.50, +1.08] · +0.77 [+0.60, +1.00] · +0.58 [+0.31, +0.90] | | `rank_dependence_vt_top` |
| **AR-V3:K-cursor-10** | First-visit split (window ends at the end of the first gaze visit; 9,141 rows): bands full → first visit | 3 | **0.771 → 0.553** (paired −0.195 [−0.213, −0.176]) | 0.759 → 0.551 | `first_visit_carve.models.bands_3_*` |
| AR-V3:K-cursor-11 | Same split, `vp_any` | 1 | 0.729 → 0.464 | | `first_visit_carve.models.vp_any_*` |
| AR-V3:K-cursor-12 | Same rows, cursor M4-7 (no split needed; features end at the press) | 7 | 0.679 | 0.706 | `first_visit_carve.models.cursor_M4_7` |

Reading: unlike the NB36 kinematics vector, the band advantage over the cursor survives within trial; the coefficient ordering of the historical rows (K6–K8) holds; the historical P5 "significance transition" and P3 peak do not survive on 787–1,705 rows per position, `vt_top` is positive at every rank. The first-visit split shows the band signal is largely the return itself: a result the eyes come back to has been in the top third longer *because* of the return. A scroll-only deployment cannot compute that cutoff, so the deploy caveat in TODO (visit-number carve) applies to the viewport channel as it does to the cursor.

### Pooled performance — post-cascade `[organic]` (superseded 2026-09-18: fixation-selected feature lineage; see K-cursor-1..7)

| K-ID | Model | Features | Bootstrap median AUC | 95 % CI | Regime |
|---|---|---:|---:|---:|---|
| AR-V3:K-bbox-1 | Retreat alone (M4) | 9 | **0.775** | [0.748, 0.801] | `[LAB, AdSERP, organic]` |
| AR-V3:K-bbox-2 | Viewport `bands_any` alone | 1 | 0.712 | [0.668, 0.760] | `[LAB, AdSERP, organic]` |
| AR-V3:K-bbox-3 | Viewport bands alone (target AOI; `bands_local`) | 3 | 0.743 | [0.706, 0.780] | `[LAB, AdSERP, organic]` |
| **AR-V3:K-bbox-5** | **Retreat + bands (target AOI)** | **12** | **0.811** | **[0.788, 0.833]** | `[LAB, AdSERP, organic]` |

### Pooled performance — pre-cascade `[absolute legacy]` (preserved for comparison)

| K-ID | Model | Features | Bootstrap median AUC | 95 % CI | Regime |
|---|---|---:|---:|---:|---|
| AR-V3:K1 | Retreat alone (M4) | 9 | 0.796 | [0.759, 0.830] | `[LAB, AdSERP, absolute legacy]` |
| AR-V3:K2 | Viewport `bands_any` alone | 1 | 0.734 | [0.701, 0.766] | `[LAB, AdSERP, absolute legacy]` |
| AR-V3:K3 | Viewport bands alone (target AOI) | 3 | 0.800 | [0.774, 0.828] | `[LAB, AdSERP, absolute legacy]` |
| AR-V3:K4 | Fully-contextual viewport (10 AOIs × bands + rank) | 40 | 0.748 | (point only) | `[LAB, AdSERP, absolute legacy]` |
| AR-V3:K5 | Retreat + bands (target AOI) | 12 | 0.842 | [0.818, 0.864] | `[LAB, AdSERP, absolute legacy]` |

### Coefficient signs (pooled, standardized; + = predicts DEFERRED)

| K-ID | Feature | Coefficient |
|---|---|---:|
| AR-V3:K6 | `vt_top` | **+1.83** |
| AR-V3:K7 | `vt_mid` | +0.83 |
| AR-V3:K8 | `vt_bot` | +0.21 |

### Rank dependence of `vt_top` — post-cascade `[organic]` (superseded 2026-09-18; see K-cursor-9)

| K-ID | Position | n | `vt_top` median | 95 % CI | Verdict |
|---|---|---:|---:|---:|---|
| AR-V3:K-bbox-9  | P0 (rank 1) | 476 | **+0.62** | [+0.28, +1.08] | strong |
| AR-V3:K-bbox-10 | P1 (rank 2) | 494 | **+0.50** | [+0.16, +1.21] | strong |
| AR-V3:K-bbox-11 | P2 (rank 3) | 306 | **+1.09** | [+0.67, +1.65] | strong |
| AR-V3:K-bbox-12 | P3 (rank 4) | 219 | **+1.29** | [+0.77, +2.16] | **peak** |
| AR-V3:K-bbox-13 | P4 (rank 5) | 170 | +0.24 | [−0.10, +0.85] | attenuating |
| AR-V3:K-bbox-14 | P5 (rank 6) | 116 | +0.05 | [−0.19, +0.58] | **CI includes 0 — significance transition** |

The P0–P3-positive, P4–P5-attenuating pattern is preserved; the per-position magnitudes shift (P0–P1 lower under organic; P2–P3 retain or strengthen). All from `bootstrap_results_organic.json`.

### Rank dependence of `vt_top` — pre-cascade `[absolute legacy]` (preserved for comparison)

| K-ID | Position | n | `vt_top` median | 95 % CI | Verdict |
|---|---|---:|---:|---:|---|
| AR-V3:K9 | P0 (rank 1) | 645 | +2.02 | [+1.47, +2.69] | strong (legacy) |
| AR-V3:K10 | P1 (rank 2) | 545 | +1.67 | [+1.22, +2.38] | strong (legacy) |
| AR-V3:K11 | P2 (rank 3) | 396 | +1.48 | [+1.03, +2.17] | strong (legacy) |
| AR-V3:K12 | P3 (rank 4) | 262 | +1.10 | [+0.56, +2.05] | strong (legacy) |
| AR-V3:K13 | P4 (rank 5) | 180 | +0.49 | [+0.13, +1.05] | marginal (legacy) |
| AR-V3:K14 | P5 (rank 6) | 122 | +0.21 | [−0.17, +0.69] | CI includes 0 (legacy) |

### JS↔Python parity

| K-ID | Claim | Value |
|---|---|---|
| AR-V3:K15 | `computeViewportBandsPure` (JS) vs `viewport_ms_for_trial` (Python) on synthetic 6-AOI fixture | All 24 fields match (Δ = 0) |

### Library tag

| K-ID | Claim | Value |
|---|---|---|
| AR-V3:K16 | Library tag for the viewport-band feature | `edmonds-2026-vpbands-v1` |

---

## Open / retired

*(none yet)*

---

## How to cite

In prose: `[AR-V1:K1]`, `[AR-V2:K8]`, `[AR-V3:K5]`, etc. In figure captions, paste the value alongside the K-ID for human-readable context. In the methods paper, the schema mirrors AF's `[NB##:K##]` so the two repos read consistently.
