# Arapakis & Leiva (2016) — Predicting User Engagement with Direct Displays

**Citation:** Arapakis, I. & Leiva, L. A. (2016). Predicting user engagement with direct displays using mouse cursor information. *SIGIR '16*, pp. 599-608.

**DOI:** 10.1145/2911451.2911505
**PDF:** https://luis.leiva.name/web/docs/papers/kme-sigir2016-preprint.pdf

## Key Numbers

| Metric | Value |
|--------|-------|
| Recruited | 612 AMT workers |
| Approved | 533 (226F, 307M) |
| Final analysis | 300 sessions |
| Cursor positions | 115,699 |
| Features extracted | 638 per session |
| Cursor polling | 150 ms |
| Queries | 144 unique, 4 topic categories |

## Prediction Targets (self-reported)

1. **Attention** — "Did you notice the Knowledge Module?" (binary)
2. **Usefulness** — KM utility (1-5 Likert)
3. **Perceived speed** — KM helped answer faster (1-5 Likert)

## Results (Random Forest, 10-fold stratified CV)

| Target | AUC | F1 | Best baseline F1 |
|--------|-----|-----|-----------------|
| Attention | **0.86** | 0.76 | 0.68 (all baselines) |
| Usefulness | **0.71** | 0.74 | 0.68 (all baselines) |
| Perceived speed | **0.77** | 0.73 | 0.63 (all baselines) |

## Top Features by Importance

Across all three targets, **cursor distance to KM reference points** dominates:
- Distance to KM center (MDA = 0.0105 for attention)
- Distance to KM corners (especially top-right, bottom-right)
- Hover ratio (KM vs other elements)
- Earth mover's distance
- Approximate entropy (order 2)
- SD of cursor speed

## Relevance to Approach-Retreat

This is the brute-force version of what we do with the task model. They extracted 638 features, ran recursive feature elimination, and the top features turned out to be **cursor distance to the element of interest** — retreat distance by another name.

Our approach-retreat library captures the same signal with ~6 features per episode because the OSEC task model tells you which features matter and why:
- Their distance-to-center = our retreat distance
- Their hover ratio = our visit count
- Their dwell time baseline = our episode dwell
- Their AUC 0.86 (638 features) vs our AUC 0.821 (episode-level signals)

The 638→6 compression IS the contribution of having a cognitive task model. Feature engineering discovers what theory predicts.

## Important Correction

Often cited as "predicting search satisfaction from cursor behavior" but the actual targets are engagement proxies (attention, usefulness, perceived speed) on Yahoo Knowledge Modules, not SAT/DSAT on organic results.

## Limitations

- Yahoo KM only (not organic results, not ads)
- Crowdsourced (AMT), not naturalistic
- Self-report ground truth
- Entity queries only (celebrities, movies, athletes, sports)
- 300 effective sessions after exclusions
- Yahoo SERP circa 2015 (outdated layout)
