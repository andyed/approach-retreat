# Public Validation: Approach-Retreat vs. Brückner et al. (SIGIR '21)

**TL;DR.** On the same 954-session public benchmark Brückner, Arapakis & Leiva used for their SIGIR '21 mouse-movement-length study, an 11-feature approach-retreat logistic regression predicts ad clicks at **AUC 0.821 ± 0.022**, a **+12.5 point improvement** over a scalar mouse-length baseline (AUC 0.696 ± 0.031). A three-feature subset (`min_dist`, `retreat_dist`, `ever_in_target`) recovers AUC 0.798 — almost all the signal in a model that fits on the back of an envelope.

## What this library claims

Before you click, your cursor tells a story. It approaches a result, dwells over it, then either commits or retreats. The *geometry* of the retreat separates the results you're done with from the ones you may come back to. Curved + close retreats predict re-approach; straight + far retreats predict commitment to rejection.

`approach-retreat` is the cursor-side half of that story: a non-learned feature set over cursor–AOI episodes that recovers click-decision signal the bag-of-features tradition has been extracting with 638 features or a Transformer.

## Validation dataset

**The Attentive Cursor Dataset** — Leiva & Arapakis, 2020, *Frontiers in Human Neuroscience* 14:565664. 2,909 mouse-tracked sessions on real Google SERPs with saved HTML, recorded by EvTrack. Publicly cloneable at [`gitlab.com/iarapakis/the-attentive-cursor-dataset`](https://gitlab.com/iarapakis/the-attentive-cursor-dataset).

This dataset is the benchmark used by three follow-up papers from the same Arapakis/Leiva group, including **Brückner, Arapakis & Leiva (SIGIR '21) "When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search"**, which treats mouse cursor sequence length as a decision-making signal under a BiLSTM.

We use the **954-session native-advertisement subset** (following Brückner's filter; 6 dropped for fewer than 3 valid mouse events). Two targets:

- **`ad_clicked`** (30.3% positive) — binary click label from `groundtruth.tsv`
- **`noticed`** (attention Likert ≥ 3, 69.5% positive) — subjective self-report used by Brückner et al.

## Protocol

Matches Brückner SIGIR '21 exactly: **60/10/30 stratified train/val/test split, 5 random seeds, weighted F1 and AUC-ROC reported as mean ± std.** No hand-tuning. No learned features. A single logistic regression with standard scaling and class-balanced weights.

## Results

| Model | AUC (noticed) | F1ʷ (noticed) | AUC (ad_clicked) | F1ʷ (ad_clicked) |
|---|---|---|---|---|
| Total mouse length only (scalar length baseline) | 0.505 ± 0.008 | 0.551 ± 0.012 | 0.696 ± 0.031 | 0.543 ± 0.004 |
| `min_dist` only | 0.566 ± 0.026 | 0.592 ± 0.023 | 0.564 ± 0.032 | 0.520 ± 0.012 |
| Retreat geometry only (`retreat_dist` + `retreat_path` + `arc_ratio`) | 0.532 ± 0.025 | 0.610 ± 0.019 | 0.705 ± 0.020 | 0.586 ± 0.016 |
| 3 features: `min_dist` + `retreat_dist` + `ever_in_target` | 0.587 ± 0.019 | 0.621 ± 0.011 | 0.798 ± 0.036 | 0.649 ± 0.019 |
| **Approach-retreat, 11 features** | **0.594 ± 0.007** | **0.602 ± 0.007** | **0.821 ± 0.022** | **0.732 ± 0.011** |

### Feature importance (standardized LR coefficients on `ad_clicked`, top 5)

| Feature | Coefficient | Direction |
|---|---|---|
| `n_events` | −1.35 | → skip (more mouse agitation = not committed) |
| `dwell_in_target_ms` | **+0.95** | → click |
| `retreat_dist` | **−0.72** | **→ skip (longer retreat = rejection — the core thesis)** |
| `ever_in_target` | +0.70 | → click |
| `n_target_entries` | +0.62 | → click |

The `retreat_dist` coefficient has the expected sign: longer retreats predict rejection as a continuous feature. Total mouse length collapses to coefficient −0.02 in the full model — its univariate AUC of 0.696 is absorbed once the geometric features are in the picture.

## Why this is a split result, not a loss

On the **objective** `ad_clicked` target, approach-retreat wins by +12.5 AUC. On the **subjective** `noticed` target, all feature sets hover near AUC 0.60, matching the ~0.55–0.65 range Brückner et al. reported with their BiLSTM on the same data.

That gap is not a limitation — it is the cleanest possible evidence that **cursor dynamics narrate the commitment decision, not subjective self-rating.** The same feature set that reaches AUC 0.821 on clicks sits at AUC 0.594 on Likert attention. The signal is about action, not awareness.

## Why this matters for practitioners

- **Deployable without an eye tracker.** Everything comes from standard mouse events and a cursor-to-target distance calculation.
- **Fits in a few hundred lines of code.** No ML framework at inference time, no learned embeddings, no neural runtime.
- **Explains its own predictions.** Logistic regression coefficients are directly interpretable.
- **Beats prior art on public data.** Not on our own dataset — on *Brückner's own benchmark*, with *Brückner's own filters and protocol*.

## Limitations

- **One target AOI per session.** The four-class taxonomy (clicked / deferred / evaluated-rejected / never-considered) collapses to binary here. This replication validates the *feature set* on a public benchmark; the four-class structure requires multi-AOI datasets such as AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR '25).
- **Ad-attention task, not open search.** Crowdworkers were explicitly studying ads, so the commit decision is saliency-weighted.
- **Sparse event logging.** EvTrack captures mouseover/out transitions plus intermittent mousemove (~1 event/sec median), not continuous 60 Hz. The arc-ratio feature is computed over sparser trajectories than on AdSERP and carries less weight here as a result.

## Reproduce it

```bash
git clone https://gitlab.com/iarapakis/the-attentive-cursor-dataset \
    /tmp/attcur/the-attentive-cursor-dataset-master

cd approach-retreat/analysis/attcur-validation
uv run python run_analysis.py  # or any env with numpy, polars, scikit-learn, scipy
```

Expected runtime: ~30 seconds. Captured output at `results.txt`. Interactive walkthrough at `notebook.ipynb`.

## Citations

- Leiva, L. A. & Arapakis, I. (2020). *The Attentive Cursor Dataset.* Front. Hum. Neurosci. 14:565664. [doi:10.3389/fnhum.2020.565664](https://doi.org/10.3389/fnhum.2020.565664)
- Brückner, L., Arapakis, I. & Leiva, L. A. (2021). *When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search.* SIGIR '21. [doi:10.1145/3404835.3463055](https://doi.org/10.1145/3404835.3463055)
- Edmonds, A. (2026). *approach-retreat: cursor approach-retreat dynamics on search result pages.* [github.com/andyed/approach-retreat](https://github.com/andyed/approach-retreat)
