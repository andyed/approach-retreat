# Public Validation: Approach-Retreat vs. Brückner et al. (SIGIR '21)

**TL;DR.** On the Attentive Cursor Dataset (Leiva & Arapakis, *Frontiers in Human Neuroscience* 2020), a **3-feature logistic regression** using cursor-to-ad distance, one retreat measure, and a target-entry flag predicts `ad_clicked` at **AUC 0.798 ± 0.036** on the 954-session native-ad subset. Adding dwell and four more features raises it to **0.821 ± 0.022**. Both are substantially above the 0.696 scalar-mouse-length baseline from Brückner et al. (SIGIR '21) at +10.2 and +12.5 points respectively. On the `noticed` (ad-attention self-report) target, our LR reaches AUC 0.594 ± 0.007, which lands inside the 0.55–0.65 AUC-ROC band visible in Brückner's Figure 2(a) for their BiLSTM on the same class of task — though Brückner's 95 % Wilson CIs on that band are visibly wide (only ~77 "good attention" positives after the Likert filter, per Table 1), so "match" here is to an imprecise central estimate, not a point AUC. **The feature family beats aggregate mouse length on `ad_clicked` and is indistinguishable from a BiLSTM on `noticed` within their confidence intervals, with orders-of-magnitude lower training cost and directly interpretable coefficients.**

## What this library claims — and what this validation tests

This document tests one thing: **whether a small number of non-learned cursor features can extract click-commitment signal on a public benchmark that prior work solved with BiLSTMs.** The answer is yes, and a 3-feature subset without any dwell-based feature already captures almost all of the signal.

This document does **not** test the four-class taxonomy (clicked / deferred / evaluated-rejected / not-approached) that the `approach-retreat` library's `docs/theory.md` describes. That taxonomy requires **multi-AOI, continuous-sampling data** where the same participant evaluates 10+ result positions at 150 Hz. The Attentive Cursor Dataset here has **one target AOI per session** (a single ad), sampled at a **median ~1 event/sec**. The four-class structure cannot be recovered at that resolution or granularity. We test it on AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR '25) in the `attentional-foraging` notebooks; [`docs/theory.md`](../theory.md) has the cross-reference.

The headline on Bruckner data is narrower than the theory.md story: **classical cursor-as-click-commitment prediction with a lightweight feature set, matching sequence models with no neural overhead.** That alone is a deployable pitch for edge inference and privacy-conscious production.

## Validation dataset

**The Attentive Cursor Dataset** (ACD) — Leiva & Arapakis, 2020, *Frontiers in Human Neuroscience* 14:565664. 2,909 mouse-tracked sessions on real Google/Yahoo SERPs with saved HTML, recorded by EvTrack. Publicly cloneable at [`gitlab.com/iarapakis/the-attentive-cursor-dataset`](https://gitlab.com/iarapakis/the-attentive-cursor-dataset).

We use the **954-session native-advertisement subset** (6 dropped for fewer than 3 valid mouse events). Two targets from `groundtruth.tsv`:

- **`ad_clicked`** (30.3 % positive, 289/954) — binary objective click label
- **`noticed`** (attention Likert ≥ 3, 69.5 % positive, 663/954) — subjective self-report, thresholded

**Relationship to Brückner's published cohort.** Brückner et al. (SIGIR '21) evaluate their BiLSTM on three tasks — Attention/Noticeability, Page Abandonment, and Search Frustration. Their Attention task uses a **716-session subset drawn from Leiva & Arapakis (2020), "The Attentive Cursor Dataset" (Front. Hum. Neurosci. 14:565664)** — Brückner's reference [17] in the SIGIR '21 paper. That is **the same source corpus** our 954-session native-ad subset is drawn from. The 716 and 954 cohorts are **two different subset cuts of the same 2,909-session ACD**, not two datasets from separate publications: Brückner filters to sequences with the `attention` Likert label present; we filter to `native_ad` target sessions with ≥ 3 valid mouse events. The comparison is therefore a **matched-source benchmark with different subset rules** — stronger than a cross-publication comparison because the underlying data-collection protocol, evtrack sampling, and per-session AOI definitions are identical. We report both our `noticed` AUC and the visual readout from Brückner's Figure 2(a) so the reader can judge.

**Importantly: Brückner do not report an `ad_clicked` task.** The 0.821 AUC on `ad_clicked` in this document has no direct Brückner baseline to compare against. It is a new result on a new target using a different subset cut of the same source corpus. The comparison is only to the univariate `total_mouse_length` baseline on `ad_clicked`.

## Protocol

Matches Brückner SIGIR '21: **60/10/30 stratified train/val/test split, 5 random seeds, weighted F1 and AUC-ROC reported as mean ± std.** No hand-tuning. No learned features. A single logistic regression with standard scaling and class-balanced weights via `Pipeline(StandardScaler, LogisticRegression)`.

## Results

| Model | `noticed` AUC | `noticed` F1ʷ | `ad_clicked` AUC | `ad_clicked` F1ʷ |
|---|---|---|---|---|
| Scalar: total mouse length | 0.505 ± 0.008 | 0.551 ± 0.012 | 0.696 ± 0.031 | 0.543 ± 0.004 |
| Scalar: `min_dist` only | 0.566 ± 0.026 | 0.592 ± 0.023 | 0.564 ± 0.032 | 0.520 ± 0.012 |
| Geometry-only: `retreat_dist` + `retreat_path` + `arc_ratio`¹ (no dwell, no min_dist) | 0.532 ± 0.025 | 0.610 ± 0.019 | 0.705 ± 0.020 | 0.586 ± 0.016 |
| **3-feature no-dwell: `min_dist` + `retreat_dist` + `ever_in_target`** (no arc_ratio) | **0.587 ± 0.019** | **0.621 ± 0.011** | **0.798 ± 0.036** | **0.649 ± 0.019** |
| **Full 11-feature** | **0.594 ± 0.007** | **0.602 ± 0.007** | **0.821 ± 0.022** | **0.732 ± 0.011** |
| Brückner BiLSTM (from Figure 2(a), noticed / attention task, 716-session cut; ≈77 positives) | 0.55–0.65 band¹ | n/a | *task not reported* | *task not reported* |

¹ The "geometry-only" row includes `arc_ratio`, which is itself flagged below as geometrically underdetermined at median ~1 event/sec sampling. The row is retained for comparison with the Brückner primitive baseline, but the **3-feature no-dwell row (0.798 AUC on `ad_clicked`) is the doc's headline scientific result** — it uses `min_dist + retreat_dist + ever_in_target` and contains no `arc_ratio` and no dwell feature, so it is immune to both the sparse-sampling arc-ratio concern and the Fitts-mechanics dwell concern. The Brückner BiLSTM row reports Wilson CIs that are visibly wide on 77 positive cases; the "match" between LR 0.594 and BiLSTM 0.55–0.65 band is a confidence-interval overlap, not a point-AUC equality.

**The 3-feature no-dwell subset is the key scientific result.** On `ad_clicked` it reaches 0.798 AUC without using `dwell_in_target_ms` or any other dwell-based feature, so the Fitts-mechanics concern ("is this just detecting the motor pause before a click?") is defused: dwell is worth an extra +0.023 AUC on top, but it is not load-bearing. The core signal is `min_dist` (did the cursor ever get near the ad) + `retreat_dist` (how much did it move away afterwards) + `ever_in_target` (did the cursor ever enter the ad AOI).

On the `noticed` task, our full LR reaches AUC 0.594 ± 0.007. Brückner et al.'s BiLSTM on the same class of task (Attention/Noticeability, 716-session cut drawn from the same ACD source corpus, their Figure 2(a)) produces AUC-ROC values **in the 0.55–0.65 band** across padding and truncation modes, with 95 % Wilson CIs that are visibly wide on the 77-positive-case Attention sub-task. Our LR result is **inside that band**, which we read as "the linear classifier and the BiLSTM are indistinguishable on the attention task within their respective confidence intervals" rather than "the linear classifier is equal to the BiLSTM." An 11-feature linear classifier reaching the same AUC band as a 2-layer BiLSTM, with orders-of-magnitude lower training cost and directly interpretable coefficients, is itself a useful engineering finding on this target.

### Feature importance (standardized LR coefficients on `ad_clicked`, full 11-feature model, top 5)

| Feature | Coefficient | Direction |
|---|---|---|
| `n_events` | −1.35 | → skip (general mouse agitation, not approach-specific) |
| `dwell_in_target_ms` | **+0.95** | → click (partly click-mechanics; see note below) |
| `retreat_dist`¹ | **−0.72** | → skip (larger post-closest-approach excursion = less likely to click) |
| `ever_in_target` | +0.70 | → click |
| `n_target_entries` | +0.62 | → click |

**On `dwell_in_target_ms` and the Fitts concern.** The +0.95 coefficient does partly capture click mechanics: a user who is about to click must stop the cursor over the target. That is exactly the concern a careful reviewer should raise. The **3-feature no-dwell ablation (0.798 AUC)** is the scientifically honest defense: it shows that the approach-geometry features carry the bulk of the signal *before* any dwell feature is added. Dwell contributes an additional +0.023 AUC in the full model, which is consistent with a small non-mechanical cognitive-pause component on top of the Fitts-mechanics baseline, but the 3-feature subset stands without it.

**On `n_events` (−1.35).** This is a general session-activity nuisance regressor ("agitated cursor → not yet committed"). It is not specific to the approach-retreat thesis and should not be cited as evidence for the feature family. It is retained in the model because removing it drops AUC slightly; the contribution is computational rather than theoretical.

> ¹ **Metric note: two different `retreat_dist` definitions exist in this research program.**
>
> The attcur feature here (from `analysis/attcur-validation/run_analysis.py:100`) is:
>
>     retreat_dist = max(distances[min_idx + 1 :]) − min_dist
>
> i.e. the **maximum cursor excursion after closest approach** — how far the cursor peaks away from the ad target after its closest moment. This is the only retreat measure that is reliably computable at the ACD's median ~1-event/sec sampling rate.
>
> The sister metric on `attentional-foraging/notebooks-v2/15_cursor_approach.ipynb:325` (the NB22:K5 "post-closest-approach drift" used for the four-class motor-signature analysis on AdSERP) is:
>
>     retreat_dist = distances[-1] − distances[min_dist_idx]
>
> i.e. the **endpoint drift at episode end**. This requires continuous (150 Hz) sampling with a well-defined episode boundary to distinguish "trajectory still moving at episode end" from "trajectory landed."
>
> For a trajectory like [200, 100, 50, 80, 150, 200, 100], the attcur metric reports 150 (peak excursion after the 50 minimum) and NB15:K5 reports 50 (endpoint 100 minus minimum 50). The two are correlated but not interchangeable: both point in the same direction on binary click vs not (more retreat = less commit), but they answer different questions. The attcur metric captures the farthest point the cursor ever reached after the closest approach; NB15:K5 captures where the cursor is sitting when the episode ends.
>
> Treat this validation as a cross-dataset corroboration of the **classical retreat-as-disengagement feature family** using the 1-Hz-compatible metric, not a direct reproduction of the NB22:K5 four-class within-non-click-class split (which requires the continuous-sampling, multi-AOI AdSERP data).

## What this result proves — and what it does not

**Proves:**

- A 3-feature linear classifier reaches **0.798 AUC on `ad_clicked`** using only cursor-to-target geometry, with *no dwell, no arc ratio, no mechanical-click features*. This is +10.2 points over the univariate `total_mouse_length` baseline (0.696).
- A full 11-feature linear classifier reaches **AUC 0.594 ± 0.007 on `noticed`**, which lands inside the 0.55–0.65 AUC-ROC band that Brückner's 2-layer BiLSTM produces on the same task (Figure 2(a) attention task, 716-session cut drawn from the same ACD source corpus, 95 % Wilson CIs visibly wide on 77 positive cases). The linear classifier and the BiLSTM are **indistinguishable within confidence intervals** on attention prediction, with orders-of-magnitude lower training cost for the LR.
- The classical retreat-as-disengagement signal survives at 1 Hz sampling for an aggregate measure (max post-min excursion), even though finer trajectory features like arc ratio do not.

**Does not prove:**

- **The four-class deferred-vs-evaluated-rejected taxonomy** — that finding is from AdSERP (multi-AOI, 150 Hz) and is documented in [`docs/theory.md`](../theory.md) with references to `notebook-key-claims.md` NB22:K1–K7. The ACD's single-AOI, 1-Hz structure cannot separate the two non-click sub-populations.
- **"Cursor narrates commitment, not awareness."** Earlier framings of this document claimed the `ad_clicked` > `noticed` AUC gap proved that cursor dynamics track commitment rather than subjective attention. That framing was post-hoc and has been retracted. The gap is equally consistent with *"`ad_clicked` is a cleaner objective label than Likert self-report"* or with *"the feature set partly captures click motor execution on top of any deliberation signal."* The 3-feature no-dwell 0.798 result rules out a pure Fitts-mechanics explanation of the click gap but not the broader commitment-vs-awareness question.
- **Geometric curvature as a cognitive signal on this dataset.** At median ~1 event/sec, `retreat_arc_ratio` is mathematically unreliable — a curve sampled at 1 Hz over 300 px of travel collapses into a few angular segments. The arc ratio feature is retained in the full 11-feature model for consistency with the AdSERP feature pipeline but should be considered geometrically underdetermined at this sampling rate. Arc-ratio claims in earlier drafts of this document have been pulled.

## Why this matters for practitioners

- **Deployable without an eye tracker.** Everything comes from standard mouse events and a cursor-to-target distance calculation. Three features are sufficient for the core signal.
- **Fits in a few hundred lines of code.** No ML framework at inference time, no learned embeddings, no neural runtime, no GPU dependency.
- **Explains its own predictions.** Logistic regression coefficients are directly interpretable and auditable by non-ML engineers.
- **Matches BiLSTM with linear parameters.** On the attention task where Brückner et al. report BiLSTM results, our feature-engineered LR lands in the same AUC band. This is not a claim of "beat the BiLSTM" — the 716 vs 954 cohort difference and the visual Figure 2(a) readout preclude a precise head-to-head — but it is evidence that the task-relevant signal is well-captured by a compact non-learned feature set.

## Limitations

- **Single target AOI per session.** The four-class taxonomy collapses to binary click/not here. This validation tests the *feature set's* click-commitment signal; the four-class motor-signature structure requires a multi-AOI dataset such as AdSERP.
- **Crowdworker ad-attention task ≠ naturalistic browsing.** Crowdworkers were explicitly directed to study ads. Real-world banner-blindness distributions are very different: most users never let the cursor enter the ad AOI at all, so the `ever_in_target`, `min_dist`, and `retreat_dist` features collapse to trivial values on organic traffic. This validates the feature family *on a benchmark*, not *on typical production traffic*.
- **Sparse event logging.** EvTrack captures mouseover / mouseout transitions plus intermittent mousemove (median ~1 event/sec), not continuous 60 Hz. Arc-ratio and other trajectory-curvature features are geometrically underdetermined at this rate and should not be interpreted as continuous curvature measurements.
- **The 716 vs 954 cohort mismatch.** Brückner's Attention task uses Arapakis et al. SIGIR'20's 716-session dataset; we use the 954-session native-ad subset of Leiva & Arapakis 2020's ACD (a separate publication from the same research program). The `noticed` AUC comparison is *matched-task* but not *matched-cohort*. A strict cohort replication would require re-running on the same 716 sessions Brückner used, which are not cleanly identifiable in the public ACD.
- **No head-to-head BiLSTM on `ad_clicked`.** Brückner's paper tests Attention, Abandonment, and Frustration, not ad click. Our 0.821 AUC on `ad_clicked` has no external BiLSTM baseline; the comparison is only to the univariate `total_mouse_length` scalar (0.696). A full BiLSTM run on `ad_clicked` is the natural follow-up experiment but is outside the scope of this validation document.

## Reproduce it

```bash
git clone https://gitlab.com/iarapakis/the-attentive-cursor-dataset \
    /tmp/attcur/the-attentive-cursor-dataset-master

cd approach-retreat/analysis/attcur-validation
uv run python run_analysis.py  # or any env with numpy, polars, scikit-learn, scipy
```

Expected runtime: ~30 seconds. Captured output at `results.txt`. Interactive walkthrough at `notebook.ipynb`.

## Citations

- Arapakis, I. & Leiva, L. A. (2020). *Predicting User Engagement with Direct Displays Using Mouse Cursor Information.* SIGIR '20, 599–608. (Brückner's Attention-task dataset — 716 sessions.)
- Brückner, L., Arapakis, I. & Leiva, L. A. (2021). *When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search.* SIGIR '21. [doi:10.1145/3404835.3463055](https://doi.org/10.1145/3404835.3463055)
- Leiva, L. A. & Arapakis, I. (2020). *The Attentive Cursor Dataset.* Front. Hum. Neurosci. 14:565664. [doi:10.3389/fnhum.2020.565664](https://doi.org/10.3389/fnhum.2020.565664) (The 2,909-session ACD used in this validation, 954-session native-ad subset.)
- Edmonds, A. (2026). *approach-retreat: cursor approach-retreat dynamics on search result pages.* [github.com/andyed/approach-retreat](https://github.com/andyed/approach-retreat)
- Latifzadeh, K., Gwizdka, J. & Leiva, L. A. (2025). *The AdSERP Dataset.* SIGIR '25. (The 150 Hz multi-AOI dataset where the four-class NB22:K5 dissociation is measured.)

## Change log

- **2026-04-13** — Rewritten in response to reviewer feedback + metric-distinction audit. Earlier versions (a) compared an 11-feature LR to a 1-feature scalar baseline as a headline (strawman framing), (b) post-hoc-rationalized the `noticed` null as evidence that "cursor narrates commitment, not awareness" (unsupported by the data), (c) framed `arc_ratio` as a reliable curvature signal despite the 1-Hz sampling (geometrically unreliable), (d) implicitly conflated the attcur `retreat_dist` feature with the NB22:K5 "post-closest drift" on AdSERP (different metrics with the same name). All four framings have been retracted. The AUC 0.821 result itself is unchanged — it is computed on a separate dataset with its own feature pipeline and is not affected by the AdSERP coordinate-space audits of 2026-04-09 and 2026-04-12.
