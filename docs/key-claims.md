# Key Claims — approach-retreat

*Aggregated load-bearing numbers from this repo's validation suites, with stable IDs for citation.*

## What this document is for

Every quantitative claim that ships from this repo to a paper, a README, a slide deck, or another lab gets a stable K-ID here. Prose elsewhere cites the K-ID; this document is the authoritative source for the value.

### The contract

- **If prose in a paper draft cites a value that disagrees with a row below, the prose is wrong** — not the validation script. The validation script is canonical; this aggregate is a transcription of the script outputs.
- **K-IDs are never renumbered.** Adding a new row gets a new K-ID. Retired claims get marked `(retired YYYY-MM-DD: reason)` but keep the ID.
- **Cite as `[AR-V#:K##]`** in prose — `V1` indexes the validation suite (V1 = Brückner ACD, V2 = M5 calibration, V3 = viewport bands), `K##` indexes the row within that suite.
- **Every row points at the script and output that produced it** so any reader can re-derive the value from raw data.

### Validation suites covered

- [V1: Brückner-ACD click-prediction replication](#v1-brückner-acd-click-prediction-replication) — `analysis/attcur-validation/`
- [V2: M5 calibration (deferred-class detector)](#v2-m5-calibration-deferred-class-detector) — `docs/validation/m5-calibration.md`
- [V3: Viewport-band calibration](#v3-viewport-band-calibration) — `docs/validation/viewport-bands-calibration.md`

### LAB / WILD regime tags

Every row carries a regime tag per `CLAUDE.md` § "Role in the CIKM paper":

- **`[WILD, attcur]`** — measured on the Attentive Cursor Dataset (Leiva & Arapakis 2020), cursor + click only, no eye tracker, no pupil.
- **`[LAB, AdSERP]`** — measured on AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR 2025), 47 participants, 150 Hz gaze + pupil + cursor.
- **`[BOTH]`** — same statistic computed in both regimes.

---

## V1: Brückner-ACD click-prediction replication

Source: [`analysis/attcur-validation/run_analysis.py`](../analysis/attcur-validation/run_analysis.py)
Output: [`analysis/attcur-validation/results.txt`](../analysis/attcur-validation/results.txt)
Doc: [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md)
Dataset: 954-session native-ad subset of ACD (Leiva & Arapakis 2020)
Protocol: 60/10/30 stratified split, 5 random seeds, weighted F1 + AUC-ROC reported as mean ± std.

### Click-prediction headlines (target = `ad_clicked`, 30.3 % positive)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| **AR-V1:K1** | Approach-retreat 11-feature LR | **AUC 0.821 ± 0.022** · F1ʷ 0.732 ± 0.011 | `[WILD, attcur]` |
| **AR-V1:K2** | 3-feature no-dwell subset (`min_dist + retreat_dist + ever_in_target`) | **AUC 0.798 ± 0.036** · F1ʷ 0.649 ± 0.019 | `[WILD, attcur]` |
| AR-V1:K3 | Brückner SIGIR '21 scalar baseline (`total_mouse_length` only) | AUC 0.696 ± 0.031 · F1ʷ 0.543 ± 0.004 | `[WILD, attcur]` |
| AR-V1:K4 | `min_dist` univariate baseline | AUC 0.564 ± 0.032 · F1ʷ 0.520 ± 0.012 | `[WILD, attcur]` |
| AR-V1:K5 | Geometry-only (no dwell, no min_dist): `retreat_dist + retreat_path + arc_ratio` | AUC 0.705 ± 0.020 · F1ʷ 0.586 ± 0.016 | `[WILD, attcur]` |
| AR-V1:K6 | Lift of K1 over K3 (full LR vs scalar baseline) | +0.125 AUC (+18 % relative) | `[WILD, attcur]` |
| AR-V1:K7 | Lift of K2 over K3 (3-feature no-dwell vs scalar baseline) | +0.102 AUC (+15 % relative) | `[WILD, attcur]` |
| AR-V1:K8 | Cross-dataset alignment: K1 (WILD) vs AdSERP M4 click-prediction LOSO AUC | 0.821 = 0.821 (same number, different datasets) | `[BOTH]` (LAB number is AF NB21:K3) |

### Attention/noticeability headlines (target = `noticed`, 69.5 % positive)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V1:K9 | Approach-retreat 11-feature LR | AUC 0.594 ± 0.007 · F1ʷ 0.602 ± 0.007 | `[WILD, attcur]` |
| AR-V1:K10 | 3-feature no-dwell subset | AUC 0.587 ± 0.019 · F1ʷ 0.621 ± 0.011 | `[WILD, attcur]` |
| AR-V1:K11 | Brückner BiLSTM AUC band on the noticed/attention task (Figure 2(a), 716-session cut) | 0.55–0.65 (Wilson CIs visibly wide on ~77 positives) | `[WILD, attcur]` |
| AR-V1:K12 | K9 sits inside K11 band | "Indistinguishable within confidence intervals" — not a point-AUC equality | `[WILD, attcur]` |

### Feature importance (full LR on `ad_clicked`, top 5)

| K-ID | Feature | Standardized coefficient | Direction |
|---|---|---:|---|
| AR-V1:K13 | `n_events` | −1.35 | → skip (general session agitation, nuisance regressor) |
| AR-V1:K14 | `dwell_in_target_ms` | +0.95 | → click (partly Fitts-mechanics; defused by K2's no-dwell ablation) |
| AR-V1:K15 | `retreat_dist` (attcur definition) | −0.72 | → skip (larger post-min excursion = less likely to click) |
| AR-V1:K16 | `ever_in_target` | +0.70 | → click |
| AR-V1:K17 | `n_target_entries` | +0.62 | → click |

### Bands extension (added 2026-04-19)

Source: [`analysis/attcur-validation/run_bands_analysis.py`](../analysis/attcur-validation/run_bands_analysis.py) · Output: [`results_bands.txt`](../analysis/attcur-validation/results_bands.txt)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V1:K18 | Retreat-alone (11 features) on `ad_clicked` | AUC 0.823 ± 0.013 | `[WILD, attcur]` |
| AR-V1:K19 | Bands-alone (6 features) on `ad_clicked` | AUC 0.828 ± 0.028 | `[WILD, attcur]` |
| AR-V1:K20 | Retreat + bands combined (17 features) on `ad_clicked` | **AUC 0.859 ± 0.013** | `[WILD, attcur]` |

---

## V2: M5 calibration (deferred-class detector)

Source: [`scripts/m5_inference.py`](../scripts/m5_inference.py) for inference; calibration runs in upstream `attentional-foraging/scripts/m4_nb21_hybrid_rerun.py`.
Doc: [`docs/validation/m5-calibration.md`](validation/m5-calibration.md)
Target: NB22 `gaze_regression_label` (deferred = gaze returned for second examination)
Population: 2,351 approached-non-click episodes on AdSERP

### Gaze-clean reference numbers (deployable — no eye tracker at inference)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| **AR-V2:K1** | M5 LOSO AUC | **0.709** | `[LAB, AdSERP]` (AF NB21-derived) |
| AR-V2:K2 | Youden-*J* operating threshold | *p* = 0.500 | `[LAB, AdSERP]` |
| AR-V2:K3 | Precision on predicted-deferred pool | 88.9 % | `[LAB, AdSERP]` |
| AR-V2:K4 | Recall on predicted-deferred pool | 73.0 % | `[LAB, AdSERP]` |
| AR-V2:K5 | F1 on deferred class | 0.802 | `[LAB, AdSERP]` |
| AR-V2:K6 | NB21-classifier-threshold disagreement vs NB22 ground truth | 43.8 % | `[LAB, AdSERP]` |
| AR-V2:K7 | M5 disagreement vs NB22 ground truth | 29.4 % | `[LAB, AdSERP]` |
| **AR-V2:K8** | Supervision-signal advantage of K7 over K6 | **1.49 ×** label-disagreement reduction | `[LAB, AdSERP]` |

### LAB diagnostic upper bound (gaze-gated extractor — not deployable)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K9 | LOSO AUC | 0.794 | `[LAB, AdSERP]` |
| AR-V2:K10 | Precision (deferred) | 90.2 % | `[LAB, AdSERP]` |
| AR-V2:K11 | Recall (deferred) | 83.4 % | `[LAB, AdSERP]` |
| AR-V2:K12 | F1 (deferred) | 0.867 | `[LAB, AdSERP]` |
| AR-V2:K13 | Supervision-signal ratio | 2.18 × | `[LAB, AdSERP]` |
| AR-V2:K14 | Fidelity cost of going gaze-clean (K1 vs K9) | −0.040 AUC, −10.4 pt recall, −0.065 F1, ×0.69 supervision-signal ratio | `[LAB, AdSERP]` |

### Class prior on AdSERP (calibration reference, not universal base rate)

| K-ID | Claim | Value | Regime |
|---|---|---:|---|
| AR-V2:K15 | Deferred / evaluated-rejected split in approached-non-click population | 81 % / 19 % | `[LAB, AdSERP]` |

---

## V3: Viewport-band calibration

Source: [`attentional-foraging/scripts/viewport_time_calibration.py`](../../attentional-foraging/scripts/viewport_time_calibration.py)
Doc: [`docs/validation/viewport-bands-calibration.md`](validation/viewport-bands-calibration.md)
Population: 2,351 approached-not-clicked AOIs on AdSERP, post 2026-04-12 coordinate-space audit
Outcome: NB22 `gaze_regression_label` (1 = deferred, 0 = evaluated-rejected)
Bootstrap: 1,000 participant-cluster-resampling seeds; point estimates from LOSO LR by participant.

### Pooled performance

| K-ID | Model | Features | Bootstrap median AUC | 95 % CI |
|---|---|---:|---:|---:|
| AR-V3:K1 | Retreat alone (M4) | 9 | 0.796 | [0.759, 0.830] |
| AR-V3:K2 | Viewport `bands_any` alone | 1 | 0.734 | [0.701, 0.766] |
| AR-V3:K3 | Viewport bands alone (target AOI) | 3 | **0.800** | **[0.774, 0.828]** |
| AR-V3:K4 | Fully-contextual viewport (10 AOIs × bands + rank) | 40 | 0.748 | (point only) |
| **AR-V3:K5** | **Retreat + bands (target AOI)** | **12** | **0.842** | **[0.818, 0.864]** |

### Coefficient signs (pooled, standardized; + = predicts DEFERRED)

| K-ID | Feature | Coefficient |
|---|---|---:|
| AR-V3:K6 | `vt_top` | **+1.83** |
| AR-V3:K7 | `vt_mid` | +0.83 |
| AR-V3:K8 | `vt_bot` | +0.21 |

### Rank dependence of `vt_top` (per-position, P0–P5)

| K-ID | Position | n | `vt_top` median | 95 % CI | Verdict |
|---|---|---:|---:|---:|---|
| AR-V3:K9 | P0 (rank 1) | 645 | **+2.02** | [+1.47, +2.69] | strong |
| AR-V3:K10 | P1 (rank 2) | 545 | **+1.67** | [+1.22, +2.38] | strong |
| AR-V3:K11 | P2 (rank 3) | 396 | **+1.48** | [+1.03, +2.17] | strong |
| AR-V3:K12 | P3 (rank 4) | 262 | **+1.10** | [+0.56, +2.05] | strong |
| AR-V3:K13 | P4 (rank 5) | 180 | +0.49 | [+0.13, +1.05] | marginal |
| AR-V3:K14 | P5 (rank 6) | 122 | +0.21 | [−0.17, +0.69] | **CI includes 0 — significance transition** |

### JS↔Python parity

| K-ID | Claim | Value |
|---|---|---|
| AR-V3:K15 | `computeViewportBandsPure` (JS) vs `viewport_ms_for_trial` (Python) on synthetic 6-AOI fixture | All 24 fields match (Δ = 0) |

### Library tag

| K-ID | Claim | Value |
|---|---|---|
| AR-V3:K16 | Library tag for the viewport-band feature | `edmonds-2026-vpbands-v1` |

---

## Open / retired

*(none yet)*

---

## How to cite

In prose: `[AR-V1:K1]`, `[AR-V2:K8]`, `[AR-V3:K5]`, etc. In figure captions, paste the value alongside the K-ID for human-readable context. In the CIKM 2026 paper, the schema mirrors AF's `[NB##:K##]` so the two repos read consistently.
