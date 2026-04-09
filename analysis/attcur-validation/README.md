# Attentive Cursor Dataset — External Validation

Independent empirical test of the `approach-retreat` feature set against a published baseline on a public dataset the library has never seen. Run time: ~30 s.

**Narrative writeup for paper readers:** [`../../docs/validation/attcur-bruckner.md`](../../docs/validation/attcur-bruckner.md)

---

## Why this validation exists

The `approach-retreat` library claims that a handful of cursor-geometry features (approach, dwell, retreat, re-visit) beat the Brückner-era "total mouse path length" scalar as a predictor of ad engagement on SERPs. That claim needs to be tested on data the library was not designed against. This directory is that test.

Three reasons the Attentive Cursor Dataset (ACD, Leiva & Arapakis 2020) is the right external test:

1. **No eye tracking.** ACD collected cursor data from 2,737 users on real SERPs with no eye tracker at all — just browser `mousemove` events, click outcomes, and a post-task attention Likert (1–5). The library's feature extractor has to produce its 11 features from cursor data alone, with no fixation timestamps to key off. This is the cleanest possible test of "the feature set is cursor-only" because gaze data is not available to cheat with.
2. **Published baseline.** Brückner, Arapakis & Leiva (SIGIR '21) reported a scalar-mouse-length classifier on this exact dataset under a 60/10/30 train/val/test protocol. We reproduce that protocol (same split ratios, same 5-seed averaging) so the numbers are directly comparable.
3. **Different target than AdSERP.** The native-ad subset has one AOI per session (the ad), so the four-class taxonomy of `approach-retreat` collapses to a binary clicked / non-clicked decision. This is structurally different from AdSERP's ten-result SERPs, so it tests the feature set's transfer rather than just re-fitting on a familiar shape.

A feature set that survives all three constraints is load-bearing; one that doesn't, isn't.

---

## Headline result

**Target: `ad_clicked`** (did the participant click the native ad?)

| Model | AUC | F1 (weighted) |
|---|---|---|
| **approach-retreat (11 features)** | **0.821 ± 0.022** | **0.732 ± 0.011** |
| Brückner primitive (`total_mouse_length` only) | 0.696 ± 0.031 | 0.543 ± 0.004 |
| `min_dist` only | 0.564 ± 0.032 | 0.520 ± 0.012 |
| `min_dist + retreat_dist + ever_in_target` | 0.798 ± 0.036 | 0.649 ± 0.019 |
| Retreat-only (`retreat_dist + retreat_path + retreat_arc_ratio`) | 0.705 ± 0.020 | 0.586 ± 0.016 |

**Reading the table.** The 11-feature approach-retreat classifier beats the scalar Brückner baseline by **+0.125 AUC** (0.821 vs 0.696). Scalar mouse-length is well above chance (0.5) but far below what the geometry-aware features recover. A three-feature subset (`min_dist + retreat_dist + ever_in_target`) already reaches 0.798, meaning most of the approach-retreat gain is captured by just those three — the remaining eight features contribute a further +0.023 AUC. Retreat features alone (without any approach or dwell) get to 0.705, slightly above the Brückner baseline — retreat geometry is carrying real signal independently, not just as a correlate of something else.

**Dataset and subset.** 954 sessions on native-ad SERPs, after filtering ACD's 3,020 total sessions to `ad_type == 'native'` and dropping 6 sessions with fewer than 3 valid mouse events. Positive rate 30.3 % (289 clicks).

**Protocol.** Brückner et al. SIGIR '21: 60 / 10 / 30 stratified train/val/test split, 5 random seeds, mean ± SD reported. Features standardized per split; logistic regression with default regularization.

---

## What the 11 features measure

The classifier input is 11 scalar features computed per session from the raw cursor stream and the ad's bounding box. Every feature is reproducible from cursor events alone — no eye tracking, no DOM introspection beyond the ad boundary, no external data.

| Feature | What it measures |
|---|---|
| `min_dist` | Closest the cursor got to the ad center during the session, in pixels |
| `max_dist` | Farthest the cursor got from the ad center |
| `n_events` | Total mousemove event count — a proxy for cursor activity |
| `session_ms` | Total session duration |
| `total_mouse_length` | Accumulated path length in px (**this is the Brückner baseline feature**) |
| `ever_in_target` | Binary — did the cursor ever enter the ad's bounding box |
| `n_target_entries` | Number of distinct cursor visits to the ad (re-approach count) |
| `dwell_in_target_ms` | Total milliseconds cursor spent inside the ad bounding box |
| `retreat_dist` | Straight-line distance from ad center at the point of maximum retreat |
| `retreat_path` | Path length during the retreat |
| `retreat_arc_ratio` | Retreat path length divided by straight-line retreat distance — curvature indicator |

The baseline model uses only `total_mouse_length`. The approach-retreat model uses all 11.

---

## Why the Brückner primitive loses

Feature-importance fit on the full dataset (standardized logistic regression, approach-retreat features, target = `ad_clicked`):

| Feature | Coefficient | Direction |
|---|---|---|
| `n_events` | **−1.353** | more cursor activity → *less* likely click |
| `dwell_in_target_ms` | **+0.952** | longer dwell over the ad → click |
| `retreat_dist` | **−0.723** | bigger retreat → rejection |
| `ever_in_target` | +0.700 | cursor crossed into the ad → click |
| `n_target_entries` | +0.617 | multiple visits (reconsideration) → click |
| `retreat_path` | +0.219 | small positive |
| `session_ms` | +0.169 | small positive |
| `retreat_arc_ratio` | −0.140 | small negative |
| `max_dist` | +0.131 | small positive |
| **`total_mouse_length`** | **−0.024** | essentially dead once other features are present |
| `min_dist` | +0.017 | surprisingly weak in the full-feature fit |

The story this tells:

- **`dwell_in_target_ms` is the strongest positive signal.** Sessions in which the cursor lingers inside the ad's bounding box are much more likely to end in a click. This is the "evaluation" part of approach-retreat — the user is actively considering the ad, not just skimming past.
- **`retreat_dist` is the strongest negative motor signal.** Sessions with large retreats are sessions where the user actively disengaged after evaluating — the hard-negative signature. This is the "retreat" part.
- **`n_events` is the strongest negative overall.** A high mousemove count, once controlled for dwell and retreat, predicts *non*-click. Interpretation: sessions with high cursor activity but no dwell-in-target are "browsers" who scan the page without committing to the ad. This matches the AdSERP "chattiness" finding that chatty cursor users fixate fewer result positions.
- **`total_mouse_length` is effectively zero** (−0.024) when placed alongside the geometry-aware features. Once you know how close the cursor got, how long it dwelt, how far it retreated, and how many events there were, the total path length adds almost nothing. This is why the Brückner scalar baseline plateaus at 0.696 while the geometry-aware model reaches 0.821 — the scalar is not wrong, it's just redundant once you have the shape features.
- **`min_dist` alone looks weak in the full fit (+0.017)**, but as the third row of the first table shows, it reaches 0.564 AUC on its own — meaning it carries signal, but that signal is mostly captured by `ever_in_target` and `dwell_in_target_ms` in the joint model. Collinearity, not irrelevance.

The three-feature subset result (`min_dist + retreat_dist + ever_in_target` at 0.798) is consistent with this story: approach-plus-retreat-plus-contact captures most of the signal, and the other eight features add diminishing returns.

---

## The `noticed` target is much weaker — and that's a data story, not a feature story

The dataset ships two labels per session: `ad_clicked` (objective, did they click) and `noticed` (subjective, self-reported attention Likert ≥ 3). Brückner 2021 reported on `noticed`. We report both.

**Target: `noticed`** (attention Likert ≥ 3, positive rate 69.5 %)

| Model | AUC | F1 (weighted) |
|---|---|---|
| approach-retreat (11 features) | 0.594 ± 0.007 | 0.602 ± 0.007 |
| Brückner primitive | 0.505 ± 0.008 | 0.551 ± 0.012 |
| `min_dist` only | 0.566 ± 0.026 | 0.592 ± 0.023 |
| `min_dist + retreat_dist + ever_in_target` | 0.587 ± 0.019 | 0.621 ± 0.011 |
| Retreat-only | 0.532 ± 0.025 | 0.610 ± 0.019 |

The 11-feature classifier still beats the Brückner scalar (0.594 vs 0.505 — Brückner is at chance), but the ceiling is much lower than on `ad_clicked` (0.594 vs 0.821). Why:

1. **Subjective labels are noisy.** "Noticed" is a Likert rating collected post-task, subject to memory bias, social desirability, and the usual self-report confounds. The ground truth is partly the cursor and partly the participant's reconstruction of what they were attending to.
2. **The positive class is the majority (69.5 %).** At near-7:3 balance, a chance model sits at 0.5 AUC with F1w ~0.58, so the headroom for the classifier is smaller.
3. **Attention is a weaker behavioral construct than intent.** Clicking an ad is a decision with motor commitment; noticing an ad is a perceptual state with no commitment signature. The cursor-geometry features were designed to capture commitment, not perception.

This is a result about the target, not a limitation of the feature set: the same 11 features that produce AUC 0.821 on a clean objective outcome produce AUC 0.594 on a noisy subjective one. If you are evaluating `approach-retreat` for your own use case, ask whether your downstream label is closer to "clicked" (objective, committed) or "noticed" (subjective, perceptual). The library targets the former.

---

## Spearman correlations with the attention Likert

A finer-grained view of the noticed-target story. Spearman ρ of each feature with the raw attention score (1–5):

| Feature | ρ | p | Signif. |
|---|---|---|---|
| `dwell_in_target_ms` | **+0.163** | 4.0 × 10⁻⁷ | \*\*\* |
| `n_target_entries` | +0.129 | 6.3 × 10⁻⁵ | \*\*\* |
| `ever_in_target` | +0.127 | 8.6 × 10⁻⁵ | \*\*\* |
| `min_dist` | −0.087 | 7.3 × 10⁻³ | \*\* |
| `max_dist` | −0.082 | 1.1 × 10⁻² | \* |
| `retreat_dist` | −0.065 | 4.5 × 10⁻² | \* |
| `retreat_path` | −0.050 | 0.12 | ns |
| `n_events` | −0.039 | 0.23 | ns |
| `total_mouse_length` | −0.027 | 0.41 | ns |
| `retreat_arc_ratio` | −0.019 | 0.55 | ns |
| `session_ms` | −0.012 | 0.71 | ns |

Three things worth noting:

- **Dwell, entries, and contact are the only measures that monotonically track self-reported attention.** All three are positively correlated and significant at *p* < 0.001. The user's own report of "I noticed this ad" aligns with cursor contact and cursor time over the ad. This is behaviorally obvious but empirically worth confirming.
- **Proximity features (`min_dist`, `max_dist`) correlate *negatively* with attention.** Closer cursor → higher reported attention. Expected direction.
- **`total_mouse_length` is not significantly correlated with self-reported attention at all** (ρ = −0.027, p = 0.41). The Brückner baseline feature does not even weakly track the subjective label. The gap between ρ = +0.163 for `dwell_in_target_ms` and ρ = −0.027 for `total_mouse_length` is a direct illustration of what geometry-aware features buy over scalar primitives.

---

## Reproducing the numbers

**Prerequisites:**

- Python 3.13+
- `polars`, `numpy`, `scikit-learn`, `scipy`
- The Attentive Cursor Dataset — freely cloneable:

```bash
git clone https://gitlab.com/iarapakis/the-attentive-cursor-dataset \
    /tmp/attcur/the-attentive-cursor-dataset-master
```

The script expects the dataset at `/tmp/attcur/the-attentive-cursor-dataset-master`. Edit the `DATA` constant in `run_analysis.py` to point elsewhere.

**Run:**

```bash
# with an attentional-foraging uv environment:
uv run python run_analysis.py

# or with any Python env that has the deps:
python run_analysis.py
```

Runtime ~30 s on a modern laptop. Full captured output in [`results.txt`](./results.txt).

---

## What this directory contains

| File | What it is |
|---|---|
| `run_analysis.py` | Feature extraction + classifier pipeline. Self-contained. Loads ACD, filters to native ads, extracts 11 features per session from the `extras.middle` cursor-distance column, runs logistic regression under Brückner's protocol, reports coefficients and Spearmans. |
| `results.txt` | Captured output from the most recent run — the numbers in this README come from this file. |
| `notebook.ipynb` | Narrative notebook walking through the same analysis step by step, importing `parse_log`, `compute_features`, and `DATA` from `run_analysis.py`. |
| `README.md` | This file. |
| [`../../docs/validation/attcur-bruckner.md`](../../docs/validation/attcur-bruckner.md) | One-pager writeup with broader interpretation for paper readers. |

---

## Why this lives in the `approach-retreat` repo

The `approach-retreat` library's core claim is that a small set of cursor-geometry features — built around the evaluation → retreat dynamic — extracts more signal from cursor telemetry than scalar mouse-movement primitives. Validation of that claim should live with the library itself, not buried in a sibling repo, so that anyone evaluating whether to adopt `approach-retreat` can run the same test in one command.

The **AdSERP** validation (multi-AOI SERPs, ten results per page, four-class taxonomy, eye-tracked ground truth) lives in the sibling [`attentional-foraging`](https://github.com/andyed/attentional-foraging) repo, where the full task model and its notebook pipeline are maintained. Together, the two validations bracket the feature set's transfer:

- **AdSERP** tests the full multi-AOI task-model taxonomy on eye-tracked ground truth in controlled lab conditions (47 participants, 2,776 trials).
- **ACD** tests the binary ad-click target on cursor-only in-the-wild data at scale (954 native-ad sessions, no eye tracking).

Same feature set. Different labels, different populations, different dataset constraints. The numbers in both validations support the same claim — the cursor geometry is carrying the signal — which is exactly what an external test is supposed to establish.
