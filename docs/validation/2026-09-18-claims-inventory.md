# Claims inventory against the current producers — 2026-09-18

**Purpose.** Every number in this repo's docs, checked against the producer
that now stands behind it in `attentional-foraging`. Written before changing
anything. Verdicts: **HOLDS** (current lineage), **STALE** (computed on the
fixation-selected LAB stream or a pre-conversion cache; a current replacement
exists), **RE-DERIVE** (no current replacement yet; needs a producer run),
**LEGACY-OK** (already labelled historical and quarantined).

**The lineage fact this inventory turns on** (`attentional-foraging/docs/
ablations/deferred_drop_decomposition.md`, 2026-09-17): the "cursor" features
that produced every LAB M5 / V2 / V3 / ablation number here were computed by
`compute_cursor_approach_features.py`, which selects rows by fixation, samples
the cursor at fixation times, measures fixation-to-cursor distance, and
weights proximity dwell by fixation duration. On identical rows and labels
those features score 0.771 on the deferred split and the tracker's
cursor-only features score 0.665 (paired −0.068 [−0.116, −0.017]); sampling,
buffer and population each move < 0.01. The old features carried part of the
gaze-return label. `docs/current-evidence.md` (checked 2026-09-07) already
carries the cursor-only numbers for the click model, the deferred classifier
and the ranking experiment; the rest of the docs do not.

---

## 0. The item that matters most: the deployed M5 model

`scripts/models/m5_final_model.json`, consumed by `scripts/m5_inference.py`:

| property | as shipped | consequence |
|---|---|---|
| features | **nine**, including `final_dist` and `retreat_dist` | the two terms the click-buffer screen excludes on principle (CIKM §3.4; 0.949 → 0.997 with no buffer) |
| training features | LAB organic stream, 2026-05-02: fixation-selected rows, gaze-to-cursor distance at fixation times, fixation-weighted dwell | not the measurement `m5_inference.py` computes at runtime (1-D cursor-to-centre on native events); −0.07 AUC on identical rows for this reason alone |
| scaler statistics | from that distribution (`min_dist` mean 61 px, `dwell_in_proximity_ms` mean 1,488 ms) | runtime features are drawn from a different distribution; standardisation is off before the coefficients are applied |
| n | 2,070 episodes, full-data refit, no holdout | the current cursor-only pool is 9,932 (or 9,269 label-complete) |
| `loso_auc` | 0.769 | the current cursor-only deployable classifier is **0.691** (0.680 on the label-complete pool) |
| threshold | 0.489 (Youden-J) | `docs/CURATION.md` line 59 applies **0.395**; the two disagree today. Current Youden-J on the cursor-only stream is **0.477** (precision 78.1 %, recall 72.8 %, F1 0.753) |

**Action.** Retrain and re-export: seven features, `cursor-only-typed-features-mousedown.json` buf500, NB22 typed labels, full-data refit after the LOSO gate reproduces 0.6911 (the `m4_cursor_only_downstream.py` protocol; the producer already has every piece except the export). Ship as `m5_cursor_only_v2.json` with the old file kept as `m5_final_model.legacy-2026-05-02.json`; update `m5_inference.py` to the seven-feature vector; fix the CURATION threshold to whichever the new model records. Document the expected drop (0.769 → 0.691) with the ladder as the reason, not as a regression.

---

## 1. `docs/key-claims.md`

### V1 — Brückner ACD (WILD)

| rows | verdict | note |
|---|---|---|
| K1–K7, K9–K20 | **HOLDS** | no AdSERP input; unaffected by the lineage finding |
| K-bbox-8 (cross-dataset: 0.821 WILD vs 0.864 LAB, NB21:K-bbox-4) | **STALE** | the LAB anchor is the gaze-selected organic stream. Current: M4-7 **0.935** `[typed, cursor-only, press-anchored 500 ms]`, or 0.928 under the `[organic]` flavour on the same protocol. Add K-cursor-8; retire K-bbox-8 |

### V2 — M5 calibration

| rows | verdict | current replacement (producer) |
|---|---|---|
| K-bbox-1..5 (0.769 / 0.489 / 87.8 / 71.6 / 0.789; nine features) | **STALE**, and it is the deployed model (§0) | `m4_cursor_only_downstream/summary.json` §4.3: **0.691** pooled (mean 0.694 ± 0.070), Youden 0.477, precision 78.1 %, recall 72.8 %, F1 0.753, on 9,932 rows (6,800 / 3,132) |
| K-bbox-6..10 (0.752 seven-feature) | **STALE** | same row as above; the seven-feature number on the current stream is the 0.691 |
| K6–K8 (43.8 % / 29.4 % / 1.49×) | **STALE** | same producer §4.2: click-thresholded 42.5 % disagreement, deployable **32.6 %**, **1.30×** |
| K9–K14 (gaze-gated 0.794, legacy) | **LEGACY-OK** in its own terms; add the current comparator | matched-row ceiling: gaze-gated sampling **0.715** vs native 0.692 on 9,911 shared rows, paired +0.007 [−0.005, +0.020] |
| K15 (81 / 19 split) | **STALE** | 68.5 / 31.5 on the cursor-only approached non-click pool; and 85 / 15 on the fixation-selected pool, which is why the two differ |
| new | add | the ladder itself as a K-block: L 0.771 → G0 0.665 → N0 0.663 → N5 0.659 → C 0.691 (`deferred_drop_decomposition/summary.json`) |

### V3 — viewport bands

| rows | verdict | note |
|---|---|---|
| K-bbox-1..5, K1–K5 (retreat alone 0.775 / 0.796; bands alone 0.743 / 0.800; combined 0.811 / 0.842) | **RE-DERIVE** | the rows are the fixation-selected pool with the nine-feature LAB retreat vector; nothing here is on the cursor-only stream. The nearest current evidence is NB36 (`36_scroll_vs_cursor_deferred.ipynb`): on the full scroll-eligible pool (8,653 rows) viewport vector 0.713 vs cursor 0.692 pooled, **within-trial cursor 0.710 vs viewport 0.684, paired test null (20/46, p 0.72)**; combined +0.05 pooled over either; viewport vector 0.714 → **0.633** after the first-visit split (NB36 K7; the single residence feature on the 5,255-row scroll subset falls 0.702 → 0.479, `deferred-dwell-carve.md`). These are the viewport *vector*, not the three `vt_*` bands; the bands need their own run on the cursor-only pool (`scroll_only_carve.py` has the residence features; a bands variant is a small addition) |
| K6–K8 coefficient signs, K9–K14 / K-bbox-9..14 rank dependence | **RE-DERIVE** | same pool problem; the P0–P3 pattern may well survive, but it has not been measured on the current rows |
| K15–K16 (JS↔Python parity, tag) | **HOLDS** | code facts |

---

## 2. `docs/findings.md`

| section | claim | verdict | replacement |
|---|---|---|---|
| §1 headline (ACD 0.821) | | **HOLDS** | |
| §1 cross-dataset "0.821 LAB = 0.821 WILD" | already retracted in text | LEGACY-OK | the current LAB number is 0.935 |
| §1 "hover alone 0.821, within 0.026 of the full seven-feature M4 (0.847)" | | **STALE** | cursor-only stream: `dwell_in_proximity_ms` alone **0.853**, `min_dist` alone 0.872, M4-7 **0.935** (CIKM §4.1 LOFO / single-feature sweep, `m4_cursor_aoi_mousedown/summary.json`) |
| §1 "93.2 % of 2,589 clicked AOIs receive any proximity dwell; 82.7 % ≥ 500 ms; median 2.5 s" | | **RE-DERIVE** | pre-conversion buf500 cascade; recompute on the 2,608 cursor-only clicked rows (one pass over the cache) |
| §2 M5, all bullets | | **STALE** | §1 V2 rows above; the supervision-signal paragraph survives with 1.30× in place of 1.49× |
| §2 class prior 81 / 19 | | **STALE** | 68.5 / 31.5 |
| §3 viewport bands, all | | **RE-DERIVE** | V3 above; until then, cite NB36 and say the bands rows are on the fixation-selected pool |

---

## 3. Other docs

| file | claim | verdict | action |
|---|---|---|---|
| `docs/validation/m5-calibration.md` | bannered as historical (2026-09-04) | LEGACY-OK | add a short current section: 0.691 / 0.477 / 78.1 / 72.8 / 0.753, class prior 68 / 32, and the ladder as the explanation. Its advice "do not sample the cursor at fixation timestamps" is right and incomplete: the distances were fixation-to-cursor too |
| `docs/validation/feature-ablation-cross-stage.md` | baselines 0.8468 / 0.7525 / 0.6940 and the LOFO matrix | **STALE** (pre-conversion LAB stream, organic / typed-gapfill) | replace with the cursor-only LOFO: click `min_dist` −0.026, `mean_approach_velocity` −0.013, distance group alone 0.901; deferred `mean_dist` −0.055, `dwell_in_proximity_ms` −0.009; ranker LOFO `mean_approach_velocity` −0.033 binary / −0.028 four-grade, `mean_dist` −0.028 / −0.015 (`m4_cursor_aoi_mousedown`, `m4_cursor_only_downstream`, `ltr_cursor_only_four_grades` sidecars) |
| `docs/CURATION.md` | M5 0.769 deployed; threshold 0.395 at line 59 | **STALE** + internal inconsistency | follows §0 |
| `docs/one-pager.md` l.32–34, `docs/research.md` l.112–113 | "August 31 LAB diagnostic: 0.9040 with buffer, 0.7633 after excision, position 0.6654" | **STALE** as the headline; correctly labelled as LAB diagnostic | point at `current-evidence.md`: 0.935 cursor-only; the excision control on the cursor-only stream is still owed (CIKM note §4.4) |
| `docs/one-pager.md` l.48 | "0.008–0.010 MRR@10 over binary" | HOLDS | gaze +0.0114, nested cursor +0.0050 / +0.0055 |
| `README.md` l.354 | sampling ablation "nearly flat around 0.847 … pre-conversion" | HOLDS (already caveated) | optionally add the current pair: click 0.934 native → 0.901 at 1 Hz; deferred flat 0.691 → 0.701 |
| `README.md` M3 / M5 mentions in the feature docs | descriptive | HOLDS | no numbers |
| `docs/current-evidence.md` | 2026-09-07 numbers | **HOLDS**; extend | add the 09-17/18 results: the ladder; graded gaze labels (+0.012 click, **+0.05 NDCG against the four-grade relevance**, neutral beyond four grades, reverses without the cursor filter); C/W/L derived-vs-measured if the collector doc wants the C(i) framing |
| `TODO.md` deploy-collector section (2026-09-13) | six items | HOLDS | add item 7: the deployed M5 model mismatch (§0). Item 1 (visit-number carve) is confirmed by the ladder from the training side |

---

## 4. Order of work

1. **§0, the model.** One producer run plus an export, then `m5_inference.py`
   to seven features and the CURATION threshold. This is the only item that
   changes what a consumer of the library gets.
2. **`key-claims.md` V2** transcription from the two sidecars, with the
   ladder block; V1 K-bbox-8 replacement.
3. **`findings.md` §2** rewritten from the new rows; §1 hover sentence.
4. **`feature-ablation-cross-stage.md`** replaced from the three sidecars.
5. **`current-evidence.md`** extended with the 09-17/18 results.
6. **V3 / bands** last, because it needs a producer run on the cursor-only
   pool before anything can be transcribed. Until then, one banner on V3
   and findings §3: "fixation-selected pool; re-derivation pending; see
   NB36 for the current viewport-vs-cursor comparison."

Nothing in `src/` changes. The tracker is what the current producers call;
the claims around it are what moved.
