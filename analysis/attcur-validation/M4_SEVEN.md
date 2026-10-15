# The seven AdSERP M4 features, refit on ACD

> **Regime: [WILD, ACD].** Producer: `run_analysis.py --click-buffer-ms 500 --drop-retreat-dist --m4-seven` (logic in `m4_seven.py`). Sidecar: [`output/m4_seven_summary.json`](output/m4_seven_summary.json). Run date 2026-10-15, approach-retreat `07b2f55`.

The paper's §4.5 / Table 5 reported an "M4-analog" of **eight** ACD-adapted features (min_dist, max_dist, retreat_path, retreat_arc_ratio, ever_in_target, n_target_entries, n_events, session_ms). The AdSERP headline model M4 uses **seven**: min_dist, mean_dist, dwell_in_proximity_ms, mean_approach_velocity, max_approach_velocity, direction_changes, frac_decreasing. This run computes those seven on ACD.

§4.5 justified the swap on two grounds, and both are wrong. "ACD lacks the velocity terms": every EvTrack mouse event carries a ms timestamp, x, y and the cursor-to-ad distances, so velocities are computable. "final_dist requires fixation-timed sampling": final_dist is the last sample of the per-event distance series, so it is computable too. It stays excluded because M4 excludes it as a leakage screen, not because ACD lacks it.

## Reproduction gate (passed)

Same population and protocol as the committed run (`output/results-buffered-grid.txt`, Run C). The mode refuses to report anything unless these reproduce to three decimals:

| | committed | recomputed |
|---|---|---|
| sessions | 902 | 902 |
| session mouse length | 0.653 | 0.653 |
| M3-analog (10 features) | 0.765 | 0.765 |
| M4-analog (8 features) | 0.763 | 0.763 |

**954 vs 902.** Both are the 960 native-ad sessions minus sessions with fewer than 3 mouse events that carry a valid `extras.middle`. With no click buffer, 6 are dropped, which gives the README's 954. With the 500 ms buffer, a session is first truncated at its last `click` event minus 500 ms, and 52 more sessions fall below 3 events, which gives the paper's 902: 38 ad-clicked and 14 not. The positive rate falls from 0.303 (289/954) to 0.278 (251/902).

The truncation keys on any `click` event, not on an ad click. `run_analysis.compute_features`'s docstring says otherwise, but the code does not check the target. So 610 of the 670 non-ad-click native sessions are also truncated, at a click on something else. Meanwhile, 34 of the 290 ad-clicked sessions log no `click` event at all and are never truncated. This run reproduces that rule as committed. If §4.4/§4.5 describe the buffer as "truncate clicked sessions at the ad click", the text and the code disagree. Either the description or the rule should change before camera-ready.

## Distance definitions

The accumulator rules are the per-result block of `attentional-foraging/scripts/m4_nb21_hybrid_rerun.py` (`compute_hybrid_features`, the parity-verified Python port of the JS `ResultFeatureTracker`). That block is copied verbatim into `m4_seven.m4_from_dist`, and at run time the copy is checked to be textually identical to the upstream file (upstream `b9084a4`, lines 183–213; status recorded in the sidecar). The rules are: proximity d < 100 px; dwell sums Δt over in-proximity samples with 0 < Δt < 2000 ms; v = clip(−1000·Δd / max(Δt, 8), ±5000) px/s.

The rules are fixed. Two different distance series go into them:

- **(a) Euclidean, d_t = `extras.middle`**: EvTrack's distance from the cursor to the ad's bounding-box center. Uses the session's mouse events that carry a valid `middle`.
- **(b) Vertical, d_t = |y_t − ad_center_y|**: the AdSERP signal model, exactly. ACD does not store the ad box, but every mouse event's `extras` holds the distances to the four box corners and the center. The axis-aligned box (left, top, right, bottom) is recovered per session by a joint least-squares fit to all five distances over all of that session's mouse events. The box is page layout, not behaviour, so fitting it on post-click events leaks no label. Fit quality: the median absolute residual is 0.23 px at p50 and 0.27 px at p95. That is the rounding floor of the integer-logged distances. Median ad box is 616 × 184 px. Three of the 902 sessions have a median residual above 2 px and are flagged: one has all five distances equal on every event (a zero-size box), and in another the layout apparently changed mid-session. They stay in the population. A sensitivity rerun that drops them is reported below.

## Split protocol

The protocol is that of the committed `run_analysis.py`, which is **not** the 60/10/30 protocol its docstring and the README describe. There is no validation split and there are no folds. It is a repeated stratified holdout:

- `train_test_split`, 70% train / 30% test, stratified on `ad_clicked`, `random_state` = 0, 1, 2, 3, 4 (5 repeats);
- the unit is the session. ACD has **one session per participant**: 2,909 rows and 2,909 distinct `user_id`s overall, 960 and 960 in the native-ad slice. A participant-grouped split would therefore be identical, so none was run;
- StandardScaler + LogisticRegression(class_weight='balanced', max_iter=1000), refit per split;
- the reported value is the mean ± population SD (ddof = 0) of test AUC over the 5 splits. Table 5's caption says "over folds"; "over five random 70/30 splits" is accurate.

## Results: 902 sessions, `ad_clicked`, Δ = 500 ms

AUC, mean ± SD over the 5 committed splits. The last column uses the same protocol with 100 repeats (`random_state` 0–99), as a check on how far seeds 0–4 sit from the protocol's mean.

| Model | (b) vertical, 5 splits | (a) Euclidean, 5 splits | (b) 100 splits | (a) 100 splits |
|---|---|---|---|---|
| **M4-7** (seven only) | **0.765 ± 0.008** | 0.736 ± 0.021 | 0.745 ± 0.025 | 0.710 ± 0.029 |
| M4-7 + mouse length | 0.763 ± 0.003 | 0.736 ± 0.020 | 0.745 ± 0.025 | 0.713 ± 0.029 |
| M4-7 + dwell_in_target_ms | 0.775 ± 0.010 | 0.747 ± 0.024 | 0.760 ± 0.025 | 0.729 ± 0.027 |
| Session mouse length (baseline) | 0.653 ± 0.031 | ← same | 0.636 ± 0.035 | ← same |
| M4-analog, 8 features (committed, reference) | 0.763 ± 0.021 | ← same | 0.759 ± 0.028 | ← same |

Paired per-split differences on the 5 committed splits:
- (b): M4-7 − mouse length = +0.112 ± 0.026, and M4-7 − 8-feature analog = +0.001 ± 0.025.
- (a): +0.083 ± 0.012 and −0.027 ± 0.028.

Sensitivity check, dropping the 3 flagged-box sessions (n = 899, which re-draws the stratified splits): (b) M4-7 0.755 ± 0.025, (a) 0.725 ± 0.027, mouse length 0.646 ± 0.014.

**Reading the numbers.**
- The vertical series, which is the AdSERP definition, beats the Euclidean series by about 0.03 AUC. Distance to a 616 × 184 px box's center point is a poor proxy for being over the box.
- On the committed splits, the seven features match the eight-feature analog (0.765 vs 0.763). Over 100 splits they sit 0.014 below it (0.745 vs 0.759). That gap is within one split-SD, but its sign is not stable.
- Seeds 0–4 sit 0.005–0.026 above the 100-split means, depending on the model.
- Under every split set and every distance definition, the seven features beat session mouse length by 0.08–0.11 AUC.
- Adding mouse length to the seven changes AUC by at most 0.003. Adding the in-box dwell aggregate adds 0.010–0.019.

## Paper-ready text for §4.5

> ACD logs every mouse event with a millisecond timestamp, the cursor position, and EvTrack's distances from the cursor to the ad's four bounding-box corners and its center, so the seven M4 features can be computed exactly as on AdSERP. We recover each session's ad box by fitting an axis-aligned rectangle to those five distances (median residual 0.23 px, the rounding floor of the logged integers). We then set d_t = |y_t − y_ad| as on AdSERP and apply the same tracker rules: 100 px proximity, dwell over 0 < Δt < 2 s, and velocities with Δt floored at 8 ms and clamped at ±5,000 px/s. Population, target and protocol follow §4.4: 902 native-ad sessions with one session per participant and 251 clicks, the target is `ad_clicked`, and Δ = 500 ms. Each of five stratified 70/30 splits by session is fit with class-balanced logistic regression, and we report mean ± SD over the five splits. The same seven features, refit on ACD, reach 0.765 ± 0.008 AUC, against 0.653 ± 0.031 for session mouse length on the same splits. Adding mouse length to the seven gives 0.763 ± 0.003. Adding the in-ad dwell aggregate (`dwell_in_target_ms`) gives 0.775 ± 0.010. With Euclidean distance to the ad center in place of vertical distance, the seven features reach 0.736 ± 0.021. Over 100 splits under the same protocol, the seven features reach 0.745 ± 0.025 and mouse length 0.636 ± 0.035.

If Table 5 is revised, the matching rows are: session mouse length 0.653 ± 0.031; M4 (seven features, refit) 0.765 ± 0.008; M4 + mouse length 0.763 ± 0.003; M4 + dwell 0.775 ± 0.010. The caption should read "mean ± SD over five stratified 70/30 splits", not "over folds".
