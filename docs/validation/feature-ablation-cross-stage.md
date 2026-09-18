# Feature ablation across modeling stages

Companion analysis to the methods paper (under revision). The paper
uses the seven-feature M4 cursor vector at four modeling stages —
click-prediction classifier (§4.1), deferred-class classifier (§4.3),
and LambdaMART rankers under three label flavors (§4.6). Page budget
constrained the paper to per-section ablation highlights; this
document presents the full cross-stage matrix.

**Lineage note (2026-09-18).** The matrix below is computed on the
cursor-only typed stream: rows selected without gaze, features from
the browser `ResultFeatureTracker` replayed on native `mousemove`,
window ending at `mousedown` minus 500 ms. The earlier matrix (May 2026)
was computed on the fixation-selected LAB stream, whose "cursor" features
sampled the cursor at fixation times, measured fixation-to-cursor
distance, and weighted dwell by fixation duration; on identical rows and
labels those features score 0.771 on the deferred split against 0.665 for
the tracker's (paired −0.068 [−0.116, −0.017];
`attentional-foraging/scripts/output/deferred_drop_decomposition/summary.json`
`rungs.L_shared_rows` / `rungs.G0` / `steps_paired_participant`). That
matrix is kept at the end of this page under *Historical*; none of its
numbers are current.

The cross-stage view answers a question the per-section paragraphs
imply but do not state explicitly: *do all four stages read cursor
behavior the same way?* They do not, and the stage-by-stage split is
different from the one the fixation-selected stream showed.

---

## Setup

| | |
|---|---|
| Dataset | AdSERP LAB — 47 participants; typed AOI map; cursor-only `ResultFeatureTracker` replay on native `mousemove`; window ends at `mousedown` minus the buffer; **2,608 trials / 34,328 AOI rows** (`m4_cursor_aoi_mousedown/summary.json` `counts.included`, `conditions.buf500.M1.n_records`) |
| Click-buffer | Δ = 500 ms, press-anchored (canonical; grid at 0 / 250 / 500 / 1,000 ms below) |
| §4.3 deferred pool | **9,932** approached non-click rows, `min_dist` < 100 px; 6,800 deferred / 3,132 evaluated-rejected on the NB22 gaze-regression label (`m4_cursor_only_downstream/summary.json` `population.approached_nonclick_pool`, `population.four_class`) |
| §4.6 ranker rows | **13,909** training rows (`NotApprBelow` excluded), all 34,328 rows scored (`ltr_cursor_only_four_grades/summary_buf500.json` `dataset.records_kept`) |
| Cross-validation | LOSO-by-participant, 47 folds, at every stage |
| §4.1 / §4.3 classifier | `StandardScaler` + balanced `LogisticRegression(C=1, max_iter=5000)` fit per fold (`protocol.estimator`) |
| §4.6 ranker | LightGBM `LGBMRanker` (`objective=lambdarank`, `ndcg@10`, `n_estimators=200`, `learning_rate=0.05`, `num_leaves=31`, `min_data_in_leaf=20`) (`protocol.ranker`) |
| Metric (§4.1 / §4.3) | Pooled LOSO AUC on out-of-fold `predict_proba` |
| Metric (§4.6) | Per-trial MRR@10 against the binary click, so comparable across label flavors |

The seven features are
`min_dist`, `mean_dist`, `dwell_in_proximity_ms`,
`mean_approach_velocity`, `max_approach_velocity`,
`direction_changes`, `frac_decreasing` —
the leakage-validated set after the paper's §3.4 click-buffer screen
excluded `final_dist` and `retreat_dist`. On this stream the nine-feature
diagnostic (M4-9) scores 0.990 at 500 ms against 0.935 for the seven
(`conditions.buf500.M4-9.pooled_auc`, `conditions.buf500.M4-7.pooled_auc`);
the two excluded terms still identify the click target.

Three sidecars in `attentional-foraging/scripts/output/` supply every
number below; the key path is given next to each table.

---

## Table 1 — LOFO across modeling stages

Each row drops one feature and trains on the remaining six.
Δ is change from the full-7 baseline. Bold cells mark features
that move the metric by ≥ 0.010 absolute.

Sources: §4.1 `m4_cursor_aoi_mousedown/summary.json`
`feature_ablation.buf500.leave_one_out.<feature>.delta_pooled_auc_vs_M4-7`;
§4.3 `m4_cursor_only_downstream/summary.json`
`section_4_3.leave_one_feature_out.<feature>.delta_pooled_auc_vs_full`;
§4.6 `ltr_cursor_only_four_grades/summary_buf500.json`
`ranker_leave_one_feature_out.{binary,3grade_cursor,4grade_gaze}.<feature>.delta_mrr10_vs_full`.

| Feature | §4.1 click<br/>ΔAUC | §4.3 deferred<br/>ΔAUC | §4.6 binary<br/>ΔMRR@10 | §4.6 cursor 3-grade<br/>ΔMRR@10 | §4.6 gaze 4-grade<br/>ΔMRR@10 |
|---|---:|---:|---:|---:|---:|
| `min_dist`                  | **−0.026** | −0.001     | **−0.014** | −0.009     | −0.010 |
| `mean_dist`                 | −0.006     | **−0.055** | **−0.028** | **−0.013** | **−0.015** |
| `dwell_in_proximity_ms`     | −0.003     | −0.009     | **−0.012** | **−0.014** | **−0.010** |
| `mean_approach_velocity`    | **−0.013** | +0.001     | **−0.033** | **−0.030** | **−0.028** |
| `max_approach_velocity`     | −0.003     | −0.001     | +0.001     | −0.003     | −0.000 |
| `direction_changes`         | −0.000     | +0.002     | +0.002     | −0.002     | −0.002 |
| `frac_decreasing`           | +0.000     | +0.000     | −0.003     | −0.003     | −0.009 |
| **baseline (full-7)**       | **0.935**  | **0.691**  | **0.774**  | **0.776**  | **0.786** |

Baselines: `conditions.buf500.M4-7.pooled_auc` 0.9348;
`section_4_3.deployable_M4_7.pooled_auc` 0.6911;
`metrics["LambdaMART (binary click)"].mrr10` 0.7742;
`metrics["LambdaMART (3-grade collapse, 2/1/0/0; cursor labels)"].mrr10` 0.7758;
`metrics["LambdaMART (4 distinct grades, 3/2/1/0; gaze labels)"].mrr10` 0.7856.

**Caveat on the cursor 3-grade column.** The ranker LOFO exists only in
the September 6 run, whose cursor labels come from one global LOSO label
vector reused across outer ranker folds (the label-generation dependency
recorded in [current-evidence.md](../current-evidence.md), "September 7
label-generation audit"). The nested rerun
(`ltr_cursor_only_nested_grades/summary_buf500.json`) moves that
baseline to 0.7797 but its `ranker_leave_one_feature_out` block is empty;
the cursor-label deltas here are a non-nested diagnostic. The binary and
gaze-label columns have no such dependency.

**Reading the matrix.**

- **No feature is load-bearing at every stage.** Each stage has its own
  largest term: `min_dist` for click prediction (−0.026),
  `mean_dist` for the deferred class (−0.055), and
  `mean_approach_velocity` for ranking (−0.033 / −0.030 / −0.028, the
  largest LOFO drop under all three label flavors).
- **`mean_dist` carries the deferred stage and is the only feature
  that does.** Dropping it costs 0.055; nothing else costs more than
  0.010. The click classifier reads it at −0.006. The rankers, though,
  do read it (−0.028 binary, −0.013 / −0.015 graded), so it is not
  noise outside §4.3 on this stream.
- **`dwell_in_proximity_ms` is not the universal feature it was on the
  fixation-selected stream.** Its LOFO drop is −0.003 for click
  prediction, −0.009 for the deferred class and −0.010 to −0.014 for
  the rankers. It scores 0.853 alone on the click task
  (`feature_ablation.buf500.alone.dwell_in_proximity_ms.pooled_auc`), so
  the small LOFO drop is redundancy with `min_dist` (0.872 alone) and
  `mean_dist` (0.872 alone), not weakness.
- **Velocity is no longer marginal.** `mean_approach_velocity` moves the
  click AUC by −0.013 and every ranker by ≥ 0.028. `max_approach_velocity`
  and the two dynamics features stay within ±0.003 at every stage
  except `frac_decreasing` under gaze four-grade labels (−0.009).
- **Graded labels do not redistribute the work.** Under the cursor
  3-grade and gaze 4-grade labels the same three features lead
  (`mean_approach_velocity`, `mean_dist`, `dwell_in_proximity_ms`) with
  `min_dist` shrinking from −0.014 to −0.009 / −0.010.

---

## Table 2 — Feature-group ablation (§4.1 only)

The seven features partition into three semantic groups:

```
distance  = min_dist, mean_dist, dwell_in_proximity_ms
velocity  = mean_approach_velocity, max_approach_velocity
dynamics  = direction_changes, frac_decreasing
```

*minus* drops the group (trains on the complement); *only* trains on the
group alone. Pooled LOSO AUC at the 500 ms buffer, full-7 = 0.935.
Source: `m4_cursor_aoi_mousedown/summary.json`
`feature_ablation.buf500.groups.<group>.{without,only}.pooled_auc`.
The cursor-only ranker sidecars carry per-feature LOFO only, so the
§4.6 group columns of the historical table have no current counterpart.

| Group | §4.1 minus (AUC) | §4.1 minus (Δ) | §4.1 only (AUC) | §4.1 only (Δ) |
|---|---:|---:|---:|---:|
| distance | 0.611 | **−0.324** | 0.901 | −0.034 |
| velocity | 0.921 | **−0.013** | 0.613 | **−0.322** |
| dynamics | 0.935 | −0.000 | 0.582 | **−0.353** |

**Distance carries click prediction.** Without the three distance
features the click classifier falls to 0.611; on distance alone it
scores 0.901, 0.034 below the full vector. Velocity alone (0.613) and
dynamics alone (0.582) are near the position-only baseline of 0.792
(`conditions.buf500.M1.pooled_auc`) and below it; they add 0.013 and
0.000 respectively on top of the rest.

---

## §4.1 single-feature sweep, forward addition, and buffer grid

Single-feature pooled LOSO AUC at 500 ms
(`feature_ablation.buf500.alone.<feature>.pooled_auc`):

| Feature alone | AUC |
|---|---:|
| `min_dist` | 0.872 |
| `mean_dist` | 0.872 |
| `dwell_in_proximity_ms` | 0.853 |
| `mean_approach_velocity` | 0.615 |
| `frac_decreasing` | 0.579 |
| `max_approach_velocity` | 0.549 |
| `direction_changes` | 0.509 |

The sidecar records three steps of greedy forward addition
(`feature_ablation.buf500.forward_addition`): `min_dist` 0.872 →
+ `mean_approach_velocity` 0.909 → + `mean_dist` 0.929, against 0.935
for all seven. The second pick is the velocity term, not the second-best
single feature; the three distance features are largely redundant with
one another and velocity is the first non-redundant addition.

Buffer grid for M4-7 (`conditions.<buf>.M4-7.pooled_auc`): **0.949** at
0 ms, **0.948** at 250 ms, **0.935** at 500 ms, **0.885** at 1,000 ms.
The 500 ms buffer removes samples (21,223 across 1,705 trials, per
[current-evidence.md](../current-evidence.md)); the full-approach excision
control on this stream is still owed.

---

## §4.3 minimal set

`section_4_3.minimal_four` in `m4_cursor_only_downstream/summary.json`:
`mean_dist`, `dwell_in_proximity_ms`, `min_dist`, `direction_changes`
score **0.691** pooled (0.6906 against 0.6911 for the seven), paired
participant Δ +0.001 [−0.003, +0.005], Wilcoxon p = 0.58. The
nine-feature diagnostic (`section_4_3.deployable_M4_9_diagnostic`)
scores 0.693: the two terminal-distance terms that lift click
prediction from 0.935 to 0.990 add nothing to the deferred class.

---

## Discussion

Three observations the cross-stage view makes explicit.

1. **There is no universal feature.** The fixation-selected stream made
   `dwell_in_proximity_ms` look load-bearing everywhere; on the
   cursor-only stream its largest LOFO drop is 0.014. A cursor SDK built
   on this library should track distance (`min_dist`, `mean_dist`),
   proximity dwell, and mean approach velocity as a set; no single one
   of them is the quality signal.

2. **Different supervision targets pull different features into the
   lead.** §4.3's gaze-supervised classifier is carried by `mean_dist`
   (−0.055); §4.1's click-supervised classifier reads it at −0.006 and is
   carried by `min_dist`. This is the evidence behind the paper's
   two-production-paths framing (§4.3): the two classifiers extract
   different aspects of the same trace.

3. **The ranking gain from behavioral grades is small on this stream,
   and the ranker does read `mean_dist` itself.** The nested
   cursor-label lift over binary LambdaMART is +0.0055 (three grades) /
   +0.0050 (four grades)
   (`ltr_cursor_only_nested_grades/summary_buf500.json`
   `headlines.cursor.delta_mrr10_3grade_minus_binary`,
   `…_4grade_minus_binary`); the gaze-label lift is +0.0114. The
   historical +0.051 cursor-3-grade lift and the argument that
   sustained-distance information "has to enter through §4.3's
   classifier because LambdaMART never surfaces `mean_dist`" are both
   retired: LambdaMART on the cursor-only stream drops 0.028 MRR@10
   without `mean_dist`.

---

## Reproducibility

Three producers in `attentional-foraging` (public) generate the current
matrix. Each sidecar pins its input caches by SHA256.

| Script | Sidecar | Supplies |
|---|---|---|
| `scripts/m4_cursor_aoi_rerun.py` (mousedown anchor) | `scripts/output/m4_cursor_aoi_mousedown/summary.json` | §4.1 LOFO, single-feature, groups, forward addition, buffer grid |
| `scripts/m4_cursor_only_downstream.py` | `scripts/output/m4_cursor_only_downstream/summary.json` | §4.3 LOFO, minimal four, M4-9 diagnostic, pool counts |
| `scripts/ltr_cursor_only_four_grades.py` | `scripts/output/ltr_cursor_only_four_grades/summary_buf500.json` | §4.6 ranker LOFO under three label flavors (non-nested cursor labels) |
| `scripts/ltr_cursor_only_nested_grades.py` | `scripts/output/ltr_cursor_only_nested_grades/summary_buf500.json` | §4.6 nested cursor-label headlines (no LOFO block) |
| `scripts/deferred_drop_decomposition.py` | `scripts/output/deferred_drop_decomposition/summary.json` | the lineage ladder that retires the historical matrix |

The sidecar dates are 2026-09-06 (click, deferred, four-grade ranker),
2026-09-07 (nested ranker) and 2026-09-17 (ladder).

---

## Historical (fixation-selected LAB stream, pre-2026-08-31 coordinate conversion)

Everything below this heading is the May 2026 matrix, retained for
lineage and not for citation. It was computed on the organic (§4.1,
§4.3) or typed-gapfill (§4.6) cascade of the fixation-selected LAB
stream, before the coordinate conversion, with features from
`compute_cursor_approach_features.py` (cursor sampled at fixation times,
fixation-to-cursor distance, fixation-weighted dwell). The ladder in
`deferred_drop_decomposition/summary.json` attributes the difference
between these numbers and the current ones to that feature definition
(−0.068 paired on identical rows), not to sampling, buffer or population.
The "replicate repository" scripts named at the end are the ones that
produced this block.

### Setup

| | |
|---|---|
| Dataset | AdSERP — 47 participants, 2,776 trials, organic (§4.1, §4.3) or typed-gapfill (§4.6) cascade |
| Click-buffer | Δ = 500 ms (canonical, §4.4) |
| Cross-validation | LOSO-by-participant, 47 folds |
| §4.1 / §4.3 classifier | scikit-learn LogisticRegression (`solver=lbfgs`, `C=1.0`, `max_iter=2000`, `class_weight=balanced`) + `StandardScaler` fit per fold |
| §4.6 ranker | LightGBM `LGBMRanker` (`objective=lambdarank`, `metric=ndcg`, `n_estimators=200`, `learning_rate=0.05`, `num_leaves=31`, `min_data_in_leaf=20`, `label_gain=[0,1,3,7,15]`) |
| Metric (§4.1 / §4.3) | LOSO AUC on out-of-fold `predict_proba` |
| Metric (§4.6) | Per-trial MRR@10 (against binary clicked, so comparable across label flavors) |

The seven features are
`min_dist`, `mean_dist`, `dwell_in_proximity_ms`,
`mean_approach_velocity`, `max_approach_velocity`,
`direction_changes`, `frac_decreasing` —
the leakage-validated set after the paper's §3.4 click-buffer screen
excluded `final_dist` and `retreat_dist`.


### Table 1 — LOFO across modeling stages

Each row drops one feature and trains on the remaining six.
Δ is change from the full-7 baseline. Bold cells highlight features
that move the metric by ≥ 0.010 absolute.

| Feature | §4.1 click<br/>ΔAUC | §4.3 deferred<br/>ΔAUC | §4.6 binary<br/>ΔMRR@10 | §4.6 cursor 3-grade<br/>ΔMRR@10 | §4.6 four-grade ceiling<br/>ΔMRR@10 |
|---|---:|---:|---:|---:|---:|
| `min_dist`                  | **−0.0143** | +0.0010     | **−0.0147** | −0.0044     | −0.0013 |
| `mean_dist`                 | +0.0002     | **−0.0868** | **−0.0102** | −0.0054     | −0.0043 |
| `dwell_in_proximity_ms`     | **−0.0186** | **−0.0107** | **−0.0205** | **−0.0179** | **−0.0203** |
| `mean_approach_velocity`    | −0.0002     | +0.0003     | −0.0033     | −0.0074     | −0.0039 |
| `max_approach_velocity`     | −0.0005     | +0.0011     | −0.0029     | +0.0004     | +0.0020 |
| `direction_changes`         | +0.0002     | +0.0007     | −0.0003     | −0.0000     | +0.0031 |
| `frac_decreasing`           | −0.0044     | +0.0013     | −0.0081     | −0.0051     | −0.0012 |
| **baseline (full-7)**       | **0.8468**  | **0.7525**  | **0.6940**  | **0.6872**  | **0.6851** |

**Reading the matrix.**

- `dwell_in_proximity_ms` is **load-bearing at every stage** (ΔMRR ≈
  −0.020 in §4.6 across all three flavors; the only feature with that
  property).
- `min_dist` carries §4.1 click prediction (−0.014) *and* §4.6
  binary-click LambdaMART (−0.015) — but fades to noise once the §4.6
  labels go graded (−0.004 / −0.001). The graded LambdaMART
  re-distributes the work across the seven-feature set.
- `mean_dist` is the §4.3 MVP (drops AUC by 0.087, the largest single-
  feature effect in the entire matrix), but it is *noise* at every
  other stage. Sustained moderate distance is the deferred-class
  signal specifically; click prediction and ranker training do not
  surface it.
- Velocity and dynamics features sit at or below ±0.008 across all
  stages — they contribute marginally given the distance + dwell
  features.


### Table 2 — Feature-group ablation

The seven features partition into three semantic groups:

```
distance  = min_dist, mean_dist, dwell_in_proximity_ms
velocity  = mean_approach_velocity, max_approach_velocity
dynamics  = direction_changes, frac_decreasing
```

For each group at each stage, *minus* drops the group (trains on the
complement); *only* trains on the group alone. Cells report Δ from the
full-7 baseline.

| Group | §4.1 minus<br/>(ΔAUC) | §4.1 only<br/>(ΔAUC) | §4.6 bin minus<br/>(ΔMRR) | §4.6 bin only<br/>(ΔMRR) | §4.6 3-grade minus<br/>(ΔMRR) | §4.6 3-grade only<br/>(ΔMRR) |
|---|---:|---:|---:|---:|---:|---:|
| distance | **−0.0925** | −0.0098     | **−0.0825** | −0.0265     | **−0.0700** | −0.0246 |
| velocity | −0.0050     | **−0.1054** | −0.0187     | **−0.0977** | −0.0184     | **−0.0872** |
| dynamics | −0.0041     | **−0.1203** | −0.0073     | **−0.1084** | −0.0025     | **−0.0950** |

**Distance is load-bearing at every stage.** Drop it and the metric
collapses 0.07–0.09 across §4.1 and all three §4.6 flavors; train on
distance alone and you land within 0.01–0.03 of the full vector.
Velocity-only and dynamics-only each leave 0.08–0.12 of the headline
metric on the floor — they cannot substitute for distance, only
augment it.


### §4.1 cumulative forward-addition

Ranking the seven features by their *single-feature* AUC and adding
them one at a time produces the saturation curve below. *Added* names
the feature introduced at each step.

| # features | AUC | Δ vs full-7 | Added |
|---|---:|---:|---|
| 1 | 0.8212 | −0.0256 | `dwell_in_proximity_ms` |
| 2 | 0.8373 | −0.0095 | `min_dist` |
| 3 | 0.8428 | −0.0040 | `max_approach_velocity` |
| 4 | 0.8426 | −0.0042 | `direction_changes` |
| 5 | 0.8423 | −0.0045 | `mean_dist` |
| 6 | 0.8424 | −0.0044 | `mean_approach_velocity` |
| 7 | **0.8468** | — | `frac_decreasing` |

The curve saturates at three features (0.843, within 0.004 of full
performance), then plateaus until `frac_decreasing` adds the last
0.004 at step 7. Forward-addition order is *not* the load-bearing
ranking from Table 1: `mean_dist` ranks fifth here despite being M5's
MVP, because the gain it carries is for deferred-class recovery, not
click prediction.


### Discussion

Three observations the cross-stage view makes explicit.

1. **`dwell_in_proximity_ms` is the universal MVP.** The only feature
   that carries non-trivial weight at every stage. Any cursor-SDK
   shipping with this library should treat
   time-in-proximity-to-AOI as the primary quality signal to track.

2. **Different supervision targets pull different features into
   the lead.** §4.3's gaze-supervised classifier is carried by
   `mean_dist`; §4.1's click-supervised classifier ignores it. This
   is the diagnostic evidence behind the paper's two-production-paths
   framing (§4.3): the click-supervised and gaze-supervised
   classifiers are not redundant readouts of the same signal — they
   extract different aspects of cursor behavior, justifying carrying
   both classifiers downstream.

3. **The +0.051 cursor-3-grade ΔMRR@10 lift over binary-click
   LambdaMART is a label-side intervention.** The ranker reads the
   same features at every label flavor; the graded labels let it
   learn finer ordinal structure over those features. The deferred
   class is what carries new ranking information — and it has to
   enter through §4.3's classifier output, because LambdaMART itself
   never surfaces `mean_dist` as load-bearing.


### Reproducibility

Two harnesses produce the matrix.

**Replicate repository** (private until camera-ready):

| Script | Produces |
|---|---|
| `replicate/feature_ablation.py` | §4.1 click-prediction LOFO + groups + cumulative<br/>(`results.json` key `feature_ablation_m4`) |
| `replicate/classifier.py` | §4.3 single-feature LOFO<br/>(`results.json` key `ablate_single_feature_classifier`) |
| `replicate/ltr_feature_ablation.py` | §4.6 LambdaMART LOFO + groups across three label flavors<br/>(`results.json` key `feature_ablation_ltr`) |

**Source repository** (`attentional-foraging`, public):

| Script | Produces |
|---|---|
| `scripts/compute_diagnostic_ceiling.py` | §4.3 gaze-gated diagnostic ceiling LOSO fit (the 0.781 ceiling number paper §4.3 footnote cites) |
| `scripts/nb30_forward_selection_with_m4.py` | NB30 forward-selection on B∪C∪M4 with `--feature-set canonical/legacy` |
| `scripts/phase_restricted_ablation.py` | §4.4 phase-window ablation |
| `scripts/click_buffer_ablation.py` | §4.4 Δ-sweep producing the `M4-7` (canonical) and `M4-9` (legacy) rows |

**Status of this block:** the matrices above matched the §4.1 / §4.3 /
§4.6 paragraphs of paper-v5 at the time; they are retained for lineage
only. The current matrix at the top of this page is the citable one.


*Current matrix transcribed 2026-09-18 from the three cursor-only
sidecars; historical block generated 2026-05-15 and cross-references
paper-v5 §3.4 (canonical seven-feature M4), §4.1 (click prediction),
§4.3 (deferred-class classifier + two-production-paths framing), §4.6
(LambdaMART with graded labels).*
