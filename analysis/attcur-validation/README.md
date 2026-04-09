# Attentive Cursor Dataset Validation

Reproduction of the approach-retreat feature-set validation against Brückner, Arapakis & Leiva (SIGIR '21) on the Attentive Cursor Dataset (Leiva & Arapakis, 2020).

**For the narrative writeup:** [`../../docs/validation/attcur-bruckner.md`](../../docs/validation/attcur-bruckner.md)

**Headline result:** 11-feature logistic regression on `ad_clicked` → AUC 0.821 ± 0.022, vs AUC 0.696 ± 0.031 for a scalar mouse-length baseline on the same 954-session native-ad subset.

## Prerequisites

- Python 3.13+
- `polars`, `numpy`, `scikit-learn`, `scipy`
- The Attentive Cursor Dataset — freely cloneable:

```bash
git clone https://gitlab.com/iarapakis/the-attentive-cursor-dataset \
    /tmp/attcur/the-attentive-cursor-dataset-master
```

The script expects the dataset at `/tmp/attcur/the-attentive-cursor-dataset-master`. Edit the `DATA` constant in `run_analysis.py` to point elsewhere.

## Run

```bash
# with an attentional-foraging uv environment:
uv run python run_analysis.py

# or with any Python env that has the deps:
python run_analysis.py
```

Runtime: ~30 s on a modern laptop. Full captured output in `results.txt`.

## Files

| File | What it is |
|---|---|
| `run_analysis.py` | Feature extraction + classifier pipeline. Self-contained. |
| `results.txt` | Captured output from the most recent run. |
| `notebook.ipynb` | Narrative notebook walking through the same analysis. Imports `parse_log`, `compute_features`, `DATA` from `run_analysis.py`. |
| `README.md` | This file. |
| `../../docs/validation/attcur-bruckner.md` | The 1-pager writeup with interpretation. |

## What the script does

1. **Loads labels and filters to native ads.** Joins `groundtruth.tsv` and `participants.tsv`, filters to `ad_type == 'native'`. Yields 960 sessions; 6 are dropped for fewer than 3 valid mouse events.
2. **Extracts features per session** from the `extras.middle` column precomputed by EvTrack (cursor-to-ad-center Euclidean distance at every mouse event). Eleven features covering approach, dwell, retreat, and total-motion primitives.
3. **Runs logistic regression** under Brückner's SIGIR '21 protocol: 60/10/30 stratified split, 5 seeds, weighted F1 and AUC-ROC. Five model configurations, two targets (`noticed` and `ad_clicked`).
4. **Reports feature importance** — standardized coefficients on a full-data fit for interpretability, sorted by magnitude.
5. **Computes Spearman correlations** of each feature with the raw attention Likert (1–5), with p-values and significance markers.

## Why the script lives here

`approach-retreat` is a cursor-focused library, and this validation is the public empirical evidence that the library's feature set beats Brückner-era scalar length primitives on their own benchmark. Keeping the reproduction code in the library repo means anyone who is evaluating whether to use `approach-retreat` can run the same analysis in a single command.

The AdSERP validation (multi-AOI, four-class taxonomy) lives in the sibling [`attentional-foraging`](https://github.com/andyed/attentional-foraging) repo, which is where the full SERP task model and its analyses live.
