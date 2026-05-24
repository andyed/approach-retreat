# Approach/Retreat — research index

The README ships the deployer-facing surface. This page is the researcher
landing pad: what the library measures, why it works, where the numbers come
from, and which features carry the LAB validation cleanly versus which have
caveats a deployment must respect.

> **AllSERP companion paper.** The typed AOI extraction the library uses to
> derive AOI labels in the replay viewer is documented in
> *AllSERP: Exhaustive Per-Element Enrichment of the Versatile AdSERP
> Dataset* — [arXiv:2605.04949](https://arxiv.org/abs/2605.04949) (2026).
> Local PDF: [`allserp-paper.pdf`](../allserp-paper.pdf).

---

## The task model in one paragraph

A search-result page is not a stream to be embedded; it is a sequence of
**per-result deliberation episodes**. Each result the user approaches becomes
a mini-foraging-patch: enter, evaluate, retreat. The cursor traces the
geometry of that episode against the result's AOI, and a short (≤ 7) feature
vector summarising approach + dwell + post-closest-approach geometry recovers
both binary click prediction *and* a four-class examination taxonomy
(clicked / deferred / evaluated-rejected / not-approached). The four-class
taxonomy maps onto the (2, 1, 0, 0) graded-relevance vocabulary that learning-
to-rank consumes natively. The whole apparatus is the *cognitive task model*
made runnable; the long lineage of cursor-feature bag-of-features approaches
(Arapakis & Leiva 2016 et seq.) is the alternative that the task model
beats with a feature kit two orders of magnitude smaller.

For the long form: [`docs/theory.md`](theory.md), [`docs/one-pager.md`](one-pager.md).

## What the library measures, organized by claim strength

### Cursor channel (approach-retreat episodes)

| Feature | Measures | Validation regime | Caveat |
|---|---|---|---|
| `min_dist` | Closest approach to AOI center | `[BOTH]` LAB + ACD | None |
| `mean_dist` | Mean cursor-AOI distance over trial | `[BOTH]` LAB + ACD | None |
| `dwell_in_proximity_ms` | Time within 100 px of AOI center | `[BOTH]` LAB + ACD | None |
| `mean_approach_velocity` | Mean signed approach speed | `[BOTH]` LAB + ACD | None |
| `max_approach_velocity` | Peak approach speed | `[BOTH]` LAB + ACD | None |
| `direction_changes` | Sign-flips in approach velocity | `[BOTH]` LAB + ACD | None |
| `frac_decreasing` | Fraction of samples with decreasing dist | `[BOTH]` LAB + ACD | None |
| `final_dist` | Last cursor-AOI distance in trial | `[LAB]` validated | **Click-buffer leak** — see below |
| `retreat_dist` | `final_dist − min_dist` (post-closest drift) | `[LAB]` validated | **Click-buffer leak** — see below |

**Click-buffer leakage (important for any production deployment).** The CIKM 2026
paper companion runs a click-buffer ablation (truncate the cursor stream at
*click_t − Δ* for Δ ∈ {0, 200, 500, 1000} ms) and shows that `final_dist` and
`retreat_dist` carry +0.022 LAB AUC at Δ = 0 that disappears once you screen
the lock-on window. The seven features above the line are buffer-robust
(LOSO AUC change ≤ 0.009 across the Δ grid); the two below the line collapse
toward chance once Δ ≥ 500 ms. **The library still emits both** because they
are useful as descriptive statistics in interactive replay and exploratory
notebooks; what the library should not be used to do is fit a click-prediction
model on a stream that includes the moment of click, then claim deployment
generalisation. If you are scoring at *inference* time before the click event
is consumable, you are fine; if you are training on logged sessions, truncate
your input window upstream of the click.

The validated headline for click prediction (CIKM 2026): the seven
buffer-robust features at Δ = 500 ms produce LOSO AUC 0.847 on
`organic_hybrid` vs a position-only baseline of 0.668 (+0.179 lift,
47-fold), and replicate to ACD/WILD at AUC 0.765 on the analogous binary
target. The nine-feature legacy variant (the +0.030 → +0.051 numbers cited
in earlier README revisions) lives in version history, not in current
deployment recommendations.

**Sampling rate — 15 Hz default.** The deployable extractor caps the
`mousemove` feature path at 15 Hz via `maxSampleHz` (since
[`9d4efc2`](https://github.com/andyed/approach-retreat/commit/9d4efc2)).
The §5.1 cursor sampling-rate ablation shows M4 click-prediction AUC flat
at 0.847 ± 0.001 from ~59 Hz down to 1 Hz — native browser rate is pure
over-sampling for the per-AOI episode features, costing user CPU /
battery via repeated `getBoundingClientRect` forced layouts for no
predictive lift. Time-uniform decimation (1000 / `maxSampleHz` ms gate)
preserves the seven-feature buffer-robust signal because each feature is
a running aggregate against a 100 px proximity zone whose
crossing-events are easily resolved at 15 Hz. Set `maxSampleHz` to `0`
or `Infinity` to disable for native-rate research replication; `click`
is a separate listener and is never throttled.

### Viewport channel (cursor-free, scroll + DOM bboxes)

The viewport-dynamics extractor operates wherever scroll events plus DOM
bounding boxes are available — desktop, mobile, feed surfaces — without a
cursor dependency. The headline validation result is on AdSERP-LAB against
the gaze-derived deferred-vs-evaluated-rejected label
`[LAB, AdSERP, organic, NB30/NB28]`: retreat + bands combined under
bbox-organic AOIs is **0.811 [0.788, 0.833]** (NB28:K38 retrain,
1,000-seed × 47-fold StratifiedGroupKFold bootstrap). The six-feature
minimal set (residence + kinematics) — `vt_any_ms`, `vt_center_ms`,
`avg_viewport_y_px`, `max_overlap_frac`, `min_abs_velocity_px_per_s`,
`n_reversals` — was selected by forward search (NB30:K18) and recovers the
full 11-feature lift within +0.003 AUC. Bands (`vp_top_ms` / `vp_mid_ms` /
`vp_bot_ms`) add no detectable AUC on top of the continuous six but are
retained for dashboard explainability — band-time heatmaps are
human-readable in ways `avg_viewport_y_px` alone is not.

Mobile / feed / grid transfer is capability-claimed but untested;
cross-surface validation is future work. See
[`docs/validation/viewport-bands-calibration.md`](validation/viewport-bands-calibration.md)
for the full bootstrap protocol.

## Validation evidence

### LAB — AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR 2025)

47 participants, 2,776 trials, simultaneous Gazepoint GP3 HD 150 Hz gaze +
pupil + cursor + scroll + ad bboxes. Validation lives upstream in
[`attentional-foraging`](https://github.com/andyed/attentional-foraging) —
NB20–NB24 + NB28/NB30. The four-class taxonomy is `[LAB]`-only by
construction: the deferred / evaluated-rejected split depends on the
gaze-fixation sequence revisiting earlier result positions
(see [`attentional-foraging/notebooks-v2/22_four_class_taxonomy.ipynb`](https://github.com/andyed/attentional-foraging/blob/main/notebooks-v2/22_four_class_taxonomy.ipynb)).
A scroll-only detector for the same partition is named future work.

Headline LAB numbers (post-2026-05-01 bbox-organic cascade,
post-CIKM-revision click-buffer screen):

- **Click prediction (M3 / M4-7).** LOSO AUC 0.847 under `organic_hybrid` at
  Δ = 500 ms; 0.864 under `organic`; 0.870 under hybrid attribution
  pre-buffer (legacy headline). Per-etype on hybrid: organic 0.868,
  dd_top 0.916, native_ad 0.831 — the dd_top advantage is structurally
  invisible under "rank-N" pooling.
- **Four-class deferred-vs-rejected (M5).** Cursor-only LOSO AUC 0.753 on
  the gaze-derived label (deployable classifier) under canonical 7-feature
  M4-7 + buffered screen; gaze-gated upper bound is 0.781 (matched protocol).
- **Retreat geometry dissociation.** `deferred_vs_rejected_four_panel.png`
  (n = 4,275 episodes, bbox-organic) shows cursor-gaze distance and total
  dwell separating deferred from evaluated-rejected at *p* < 10⁻⁹ and
  *p* < 10⁻¹⁹ respectively (NB22:K5–K7).

### WILD — Attentive Cursor Dataset (Leiva & Arapakis 2020)

~2,909 crowdsourced sessions, **cursor + click only, no eye tracker, no
pupil.** Self-contained replication pipeline at
[`analysis/attcur-validation/`](../analysis/attcur-validation/README.md).

- Approach-retreat features beat the Brückner et al. (SIGIR 2021) scalar
  mouse-movement-length baseline by **+12.5 AUC** (0.821 vs 0.696) on their
  own ad-click-prediction benchmark, using an 11-feature logistic
  regression — no neural network, no embeddings. Detail:
  [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md).
- Click-buffer-screened ACD AUC under canonical 7-feature M4-7 is 0.765 —
  see `analysis/attcur-validation/output/results-buffered-grid.txt` for the
  full grid.
- The four-class taxonomy is `[LAB]`-only on this dataset until the
  scroll-only deferred-detector lands; ACD lacks the gaze stream needed to
  ground the four-class label.

## Lineage and positioning

This library is one fork of a long cursor-instrumentation thread. The
[`docs/positioning.md`](positioning.md) four-lane map situates it against
contemporary work; [`docs/history.md`](history.md) covers the lineage.

**Precedents (2001–2003).** Two of the modern IR cursor literature's
foundational primitives were already codified before the SIGIR cursor-on-
SERP thread began.

| Year | Release | Primitive | Modern re-derivation |
|---|---|---|---|
| 2001 | [Optimoz](http://optimoz.mozdev.org/) — Firefox gesture extension, [Slashdotted](https://www.flickr.com/photos/andyed/125275288/) | Real-time cursor-vector compression via gesture-recognition algorithm | Villaizán-Vallelado et al. SIGIR 2025 — Seq2Seq Transformer over raw cursor-trajectory embeddings |
| 2003 | Edmonds. *[Uzilla: A new tool for Web usability testing](https://link.springer.com/article/10.3758/BF03202542)* (BRMIC 35(2):194–201) | "Mouse miles" — integrated cursor path length + horizontal/vertical decomposition | Brückner, Arapakis & Leiva SIGIR 2021 — *When Choice Happens* |

Uzilla also introduced the DOM-path click signature (identifying click
targets by full DOM-tree path, not pixel position), now silently embedded
in most session-recording and analytics tools.

**The Leiva/Arapakis research program.** The cursor-on-SERP lineage runs
through one sustained collaboration; approach-retreat is best understood
as a task-model layer on top of their instrument.

| Year | Paper | Contribution |
|---|---|---|
| 2016 | Arapakis & Leiva. ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) (SIGIR) | 638 cursor features → 0.86 AUC attention prediction |
| 2020 | Leiva & Arapakis. ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) (Frontiers) | 2,737 users, public, largest cursor-on-SERP dataset |
| 2020 | Arapakis, Penta, Joho & Leiva. "A Price-per-attention Auction Scheme" (TOIS) | Cursor-attention as auction-scheme currency |
| 2021 | Leiva, Arapakis & Iordanou. "My Mouse, My Rules" (CHIIR) | Privacy analysis of telemetry primitives |
| 2021 | **Brückner, Arapakis & Leiva.** ["When Choice Happens"](https://dl.acm.org/doi/10.1145/3404835.3463011) (SIGIR) | Scalar mouse-movement length as relevance signal — **closest published prior** |
| 2025 | Latifzadeh, Gwizdka & Leiva. AdSERP (SIGIR) | Eye + mouse + pupil + ad bbox dataset, 2,776 trials |
| 2025 | Arapakis et al. AdSight (SIGIR) | Transformer-based click prediction — modern black-box counterpart |

The library's contribution: each of those papers treats cursor behaviour as
a *signal to decode*. None adopt a task model for the evaluation phase. The
OSEC → four-class decomposition turns a 638-feature brute-force problem
into a ~6-feature parsimonious one and recovers an interpretable taxonomy
instead of a scalar score.

### Why a foundation model on the same data would not rediscover this

A reasonable reviewer asks: with enough data and a flexible enough model,
shouldn't end-to-end learning rediscover the per-AOI-episode prior, the
click-buffer leakage screen, and the four-class taxonomy? The honest answer
is *mostly no*, and the reasons are structural rather than sample-size:

1. **Per-AOI episode unit — sample efficiency.** Brückner et al. SIGIR 2021
   ran the experiment: BiLSTM end-to-end on raw `(x, y, t)` + AOI geometry,
   same data, AUC ≈ 0.69 vs the task model's 0.765 leakage-screened. With
   one positive per ~12 AOIs per session and ~2,800 trials, the gradient is
   too sparse for a flexible model to converge on the unbiased per-AOI
   episode prior. Cascade / DBN / UBM with 15 years of bigger data also
   never discovered episode geometry because their aggregation grain was
   per-rank from the start.
2. **Click-buffer leakage screen — structurally undiscoverable.** A learned
   model would *happily* exploit `final_dist` because nothing in the loss
   penalizes structural leakage. The +0.022 AUC band the screen removes is
   exactly what a hands-off model would extract and ship. The methodological
   prior — "don't aggregate features over the lock-on window" — is
   unreachable from data alone; it requires knowledge of the causal structure
   of the click event.
3. **Four-class taxonomy — gaze-required.** Cursor + AOIs alone give binary
   click. Self-supervised on raw cursor could cluster non-click behaviour
   into ≥ 2 modes, but with no theoretical anchor it could collapse to 2 or
   fragment to 12. The cluster boundaries would not align with the
   *cognitive* distinction (revisit-vs-not) that makes the deferred label
   LTR-useful. Gaze defines the cluster boundaries once at training time;
   the deployable classifier transfers to cursor-only inference.

The methodological priors — per-result-AOI aggregation, click-buffer
leakage screen, gaze-defined deferred cluster — are not in the cursor
stream's gradient and so are unreachable by end-to-end learning on the
same data.

## Reproducibility

- **Feature-extractor parity.** The JS `ResultFeatureTracker` is bit-
  compatible (≤ 1e-6) with the Python reference at
  [`attentional-foraging/scripts/compute_cursor_approach_features.py`](https://github.com/andyed/attentional-foraging/blob/main/scripts/compute_cursor_approach_features.py).
  Parity test: `scripts/test_feature_tracker_parity.{js,py}`.
- **Viewport parity.** `computeViewportAnalyticsPure` is bit-compatible
  with `attentional-foraging/scripts/nb30_scroll_trajectory.py`. Parity
  test: `scripts/test_viewport_analytics_parity.{js,py}`.
- **ACD reproduction.** `analysis/attcur-validation/run_analysis.py`
  supports `--click-buffer-ms` and `--drop-retreat-dist`; the buffered grid
  output is committed at
  `analysis/attcur-validation/output/results-buffered-grid.txt`.

## Datasets

- [AdSERP](https://github.com/kayhan-latifzadeh/AdSERP) — primary, via
  [`attentional-foraging`](https://github.com/andyed/attentional-foraging).
- [The Attentive Cursor Dataset](https://gitlab.com/iarapakis/the-attentive-cursor-dataset) — public,
  2,737 users, self-reported attention labels.
- [Brückner et al. 2021 artifacts](https://dl.acm.org/doi/10.1145/3404835.3463011) —
  head-to-head documented in [`docs/validation/attcur-bruckner.md`](validation/attcur-bruckner.md).

## References

- Edmonds (2003). [*Uzilla: A new tool for Web usability testing*](https://link.springer.com/article/10.3758/BF03202542) — instrumented Mozilla, "mouse miles," DOM-path click signature, cursor-vector compression. Behavior Research Methods, Instruments, & Computers 35(2):194–201.
- Huang, White & Buscher (2012). ["User see, user point"](https://jeffhuang.com/papers/GazeCursor_CHI12.pdf) — gaze-cursor alignment on SERPs (CHI 2012).
- Guo & Agichtein (2012). ["Beyond dwell time"](https://dl.acm.org/doi/10.1145/2187836.2187914) — post-click cursor signals (WWW 2012).
- Arapakis & Leiva (2016). ["Predicting user engagement with direct displays"](https://dl.acm.org/doi/10.1145/2911451.2911505) — 638 cursor features (SIGIR 2016).
- Leiva & Arapakis (2020). ["The Attentive Cursor Dataset"](https://doi.org/10.3389/fnhum.2020.565664) — public cursor + attention dataset.
- Brückner, Arapakis & Leiva (2021). ["When Choice Happens"](https://dl.acm.org/doi/10.1145/3404835.3463011) — scalar mouse-movement length (SIGIR 2021).
- Latifzadeh, Gwizdka & Leiva (2025). AdSERP (SIGIR 2025).
- Edmonds (2026). *AllSERP: Exhaustive Per-Element Enrichment of the Versatile AdSERP Dataset.* [arXiv:2605.04949](https://arxiv.org/abs/2605.04949).
