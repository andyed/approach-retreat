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

## Buffer anchor and sweep

> Producer: `m4_seven_buffer.py` (approach-retreat `97bd942`). Sidecar: [`output/m4_seven_buffer_summary.json`](output/m4_seven_buffer_summary.json). Features: the seven M4 features on vertical distance, variant (b). Baseline: session mouse length.

**Why.** The committed rule cuts at the last click of any kind, minus Δ. At Δ = 500 ms it removes almost none of the approach:
- The last mousemove precedes the click by a median 470 ms (ad-clicked) and 554 ms (not clicked).
- Only 133 of the 256 ad-clicked sessions that log a click lose any pre-click mousemove.
- 34 of 290 ad-clicked sessions log no click and are never cut.
- In 12 ad-clicked sessions, the last click is not on the ad.

**Gate (passed).** Under the committed rule at Δ = 500, this producer reproduces 902 sessions, M4-7 0.765, and mouse length 0.653.

**Anchors.** For the 290 ad-clicked sessions:
- 244 are anchored on the last in-target `mousedown` at or before the first in-target `click`. That press precedes the click by a median 120 ms (p90 179 ms).
- 0 needed the in-target click as a fallback.
- 12 log clicks but none in the ad; they fall back to the last click of any kind.
- 34 log no click at all.

The 670 non-clicked sessions are anchored on the last click of any kind (610). The other 60 log no click.

**Rules.**
- *committed*: as run in §4.5. At Δ = 0 there is no cut.
- *ad-anchored*: keep events with ts < anchor − Δ. At Δ = 0 the cut is at the anchor itself. Sessions with no anchor are left whole.
- *drop pos*: ad-anchored, minus the 34 ad-clicked sessions with no click.
- *drop both*: ad-anchored, minus no-click sessions in both classes (34 clicked + 60 not clicked). This is the symmetric choice: no session in either class stays whole merely because it lacks a click.

Every row re-applies the ≥ 3-sample rule and re-draws its own splits.

**Column definitions.** In the table, every "a / b" pair is ad-clicked / not-clicked.
- *approach mm cut*: mousemoves removed from the window [anchor − Δ, anchor).
- *sessions hit*: sessions that lose at least one such mousemove.
- *all samples cut*: every event removed, including the press triple and any motion after the press.
- *dropped <3*: sessions removed by the ≥ 3-sample rule.

AUC is mean ± SD over the 5 committed splits, and over 100 splits.

| rule | Δ ms | n / pos | dropped <3 | approach mm cut | sessions hit | all samples cut | M4-7 (5) | M4-7 (100) | mouse (5) | mouse (100) |
|---|---|---|---|---|---|---|---|---|---|---|
| committed | 0 | 954 / 289 | 1 / 5 | 0 / 0 | 0 / 0 | 0 / 0 | 0.762 ± 0.025 | 0.761 ± 0.023 | 0.696 ± 0.031 | 0.669 ± 0.030 |
| committed | 500 | 902 / 251 | 39 / 19 | 190 / 382 | 133 / 274 | 1356 / 2724 | 0.765 ± 0.008 | 0.745 ± 0.025 | 0.653 ± 0.031 | 0.636 ± 0.035 |
| committed | 1000 | 842 / 213 | 77 / 41 | 458 / 1161 | 192 / 452 | 1775 / 3719 | 0.706 ± 0.029 | 0.708 ± 0.031 | 0.573 ± 0.037 | 0.604 ± 0.035 |
| committed | 2000 | 758 / 171 | 119 / 83 | 829 / 2367 | 232 / 543 | 2303 / 5333 | 0.658 ± 0.030 | 0.635 ± 0.032 | 0.566 ± 0.030 | 0.552 ± 0.033 |
| ad-anchored | 0 | 928 / 265 | 25 / 7 | 0 / 0 | 0 / 0 | 1160 / 1158 | 0.772 ± 0.008 | 0.781 ± 0.025 | 0.643 ± 0.027 | 0.651 ± 0.028 |
| ad-anchored | 500 | 889 / 238 | 52 / 19 | 267 / 382 | 158 / 274 | 1516 / 2724 | 0.748 ± 0.011 | 0.745 ± 0.025 | 0.617 ± 0.016 | 0.629 ± 0.031 |
| ad-anchored | **1000** | 828 / 199 | 91 / 41 | 539 / 1161 | 202 / 452 | 1923 / 3719 | **0.713 ± 0.014** | **0.694 ± 0.029** | 0.589 ± 0.045 | 0.596 ± 0.034 |
| ad-anchored | 2000 | 755 / 168 | 122 / 83 | 851 / 2367 | 231 / 543 | 2376 / 5333 | 0.648 ± 0.044 | 0.636 ± 0.039 | 0.556 ± 0.032 | 0.559 ± 0.035 |
| drop pos | 0 | 895 / 232 | 24 / 7 | 0 / 0 | 0 / 0 | 1160 / 1158 | 0.799 ± 0.021 | 0.802 ± 0.028 | 0.678 ± 0.022 | 0.664 ± 0.032 |
| drop pos | 500 | 856 / 205 | 51 / 19 | 267 / 382 | 158 / 274 | 1516 / 2724 | 0.759 ± 0.028 | 0.765 ± 0.029 | 0.649 ± 0.038 | 0.651 ± 0.035 |
| drop pos | 1000 | 795 / 166 | 90 / 41 | 539 / 1161 | 202 / 452 | 1923 / 3719 | 0.728 ± 0.041 | 0.707 ± 0.034 | 0.607 ± 0.035 | 0.613 ± 0.039 |
| drop pos | 2000 | 722 / 135 | 121 / 83 | 851 / 2367 | 231 / 543 | 2376 / 5333 | 0.602 ± 0.037 | 0.640 ± 0.040 | 0.553 ± 0.018 | 0.574 ± 0.042 |
| drop both | 0 | 840 / 232 | 24 / 2 | 0 / 0 | 0 / 0 | 1160 / 1158 | 0.818 ± 0.013 | 0.814 ± 0.025 | 0.649 ± 0.017 | 0.674 ± 0.035 |
| drop both | 500 | 801 / 205 | 51 / 14 | 267 / 382 | 158 / 274 | 1516 / 2724 | 0.779 ± 0.016 | 0.769 ± 0.027 | 0.656 ± 0.021 | 0.658 ± 0.035 |
| drop both | **1000** | 740 / 166 | 90 / 36 | 539 / 1161 | 202 / 452 | 1923 / 3719 | **0.725 ± 0.019** | **0.712 ± 0.034** | 0.622 ± 0.028 | 0.625 ± 0.038 |
| drop both | 2000 | 667 / 135 | 121 / 78 | 851 / 2367 | 231 / 543 | 2376 / 5333 | 0.622 ± 0.028 | 0.652 ± 0.041 | 0.588 ± 0.049 | 0.583 ± 0.037 |

**Reading the sweep.**
- Under every rule and at every Δ, M4-7 stays above mouse length on both split sets. On the 5 committed splits, the paired gap is:

  | Δ | ad-anchored | drop both |
  |---|---|---|
  | 500 ms | +0.130 ± 0.014 | +0.122 ± 0.026 |
  | 1000 ms | +0.124 ± 0.050 | +0.103 ± 0.023 |
  | 2000 ms | +0.092 ± 0.068 | +0.034 ± 0.025 |

- Both models lose AUC as Δ grows. M4-7 falls from about 0.77–0.82 at Δ = 0 to about 0.71–0.73 at 1000 ms and about 0.60–0.65 at 2000 ms.
- **The population changes with Δ, and not evenly by class.** The ≥ 3-sample rule removes short sessions, and those are mostly clicks. At 1000 ms, 90–91 of the 290 ad-clicked sessions are dropped, against 36–41 of the 670 non-clicked. So the long-Δ rows describe longer sessions with a lower positive rate, not the same sessions with less data.
- The 34 no-click positives behave as leakage carriers. Dropping them raises M4-7 at small Δ (0.772 → 0.799 at Δ = 0). Also dropping the 60 no-click negatives raises it again (0.818). Those sessions are not interchangeable with sessions cut at a press.
- At Δ = 1000 ms the cut does remove the approach. It takes a pre-press mousemove from 202 of the 256 ad-clicked sessions that log a click.

**Paper-ready (§4.5).**

> Because ACD's cursor usually comes to rest on the ad about half a second before the click, we also re-anchored the buffer on the ad press. That is the last in-target mousedown before the ad click (244 of 290 clicks), or the last click of any kind for non-clicked sessions. We excluded the 94 sessions that log no click in either class. At Δ = 1000 ms, a pre-press mousemove is removed from 202 of the 256 ad-clicked sessions that log a click. On the 740 remaining sessions (166 clicks), the seven M4 features reach 0.725 ± 0.019 AUC, against 0.622 ± 0.028 for session mouse length (0.712 ± 0.034 vs 0.625 ± 0.038 over 100 splits). At Δ = 2000 ms they reach 0.622 ± 0.028 vs 0.588 ± 0.049. The ≥ 3-sample rule removes short sessions as Δ grows, and these are disproportionately clicks: 90 of 290 clicked vs 36 of 670 non-clicked at 1000 ms.
