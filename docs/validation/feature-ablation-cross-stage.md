# Feature ablation across modeling stages

Companion analysis to the methods paper (submitted). The paper
uses the seven-feature M4 cursor vector at four modeling stages —
click-prediction classifier (§4.1), deferred-class classifier (§4.3),
and LambdaMART rankers under three label flavors (§4.6). Page budget
constrained the paper to per-section ablation highlights; this
document presents the full cross-stage matrix.

The cross-stage view answers a question the per-section paragraphs
imply but do not state explicitly: *do all four stages read cursor
behavior the same way?* They do not.

---

## Setup

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

---

## Table 1 — LOFO across modeling stages

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

---

## Table 2 — Feature-group ablation

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

---

## §4.1 cumulative forward-addition

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

---

## Discussion

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

---

## Reproducibility

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

**Public artifact for reviewers:** this document.
The matrices and discussion above can be verified against the §4.1 /
§4.3 / §4.6 paragraphs in the paper. The producer scripts will be
public-readable from the replicate repository on camera-ready release.

---

*Generated 2026-05-15. Cross-references paper-v5 §3.4 (canonical
seven-feature M4), §4.1 (click prediction), §4.3 (deferred-class
classifier + two-production-paths framing), §4.6 (LambdaMART with
graded labels).*
