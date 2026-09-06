# Current evidence and open questions

**Checked 2026-09-04: August LAB outputs audited; a new cursor-only typed replay executed.**

Approach-retreat measures cursor behavior relative to individual results on a
search engine results page (SERP). Its research question is whether that
behavior can improve our account of examination and the supervision used to
train a ranker. Click prediction, gaze-defined revisits, and ranking quality
are different tests of that question.

The companion methods manuscript is under revision. Reviewer feedback helped
clarify the measurement definitions, motivated stronger controls for the
final approach to a click, and highlighted the need for a worked example and
matched baselines. These pages acknowledge the substance of that feedback;
private reviews and correspondence are not reproduced here.

## Different producers measure different things

**The newest LAB scores are not a verified replacement for the browser's
cursor-only calibration.** The active [LAB producer][lab-producer] samples
cursor positions at fixation times, computes its distance fields from
**gaze–cursor distance**, and accumulates proximity dwell using fixation
durations. The browser's `ResultFeatureTracker` instead computes vertical
cursor-to-AOI distance and interval dwell from `mousemove` events. The shared
feature names and `M4-7` label conceal different measurements.

The refreshed click grid reads the LAB feature files; the excision script
calls that LAB producer directly. The ladder's “hover” row uses its
fixation-weighted proximity field. The table below therefore reports **LAB
diagnostics with gaze-dependent feature construction**, not demonstrated
cursor-only browser performance. The historical
[cursor-only hybrid extractor][cursor-producer] uses XPath observations plus
linear fallback centers; its code has no buffered `organic_hybrid` option.
Earlier documentation incorrectly attached the buffered-organic headline to
that script. The new typed stream below calls the actual browser accumulator
and identifies its different population and window explicitly.

## September 4: a cursor-only typed stream

The upstream NB21 notebook now has an independent executable reader for
`scripts/output/m4_cursor_aoi/summary.json`, produced by
`scripts/m4_cursor_aoi_rerun.py`. The producer calls the actual
`approach-retreat` `ResultFeatureTracker` through a Node bridge. The
[aggregate retained here](evidence/2026-09-04-cursor-typed-rerun.json) pins the
source hashes, AOI substrate, environment, coverage, and sampling diagnostics.
Only aggregates are retained; no trial-level features or predictions are
added to this repository.

This is **[LAB, AdSERP, typed, cursor-only]**, using the post-collision typed
maps and native mousemove. AOI centers are converted to document CSS pixels;
click labels require unique X+Y containment in a main-axis box. Every
main-axis AOI in an included trial gets a row, independently of gaze or
cursor contact. The final click defines the outcome and retrospective cutoff.
It is an offline all-AOI replay, without the browser's visibility gate or
sampling throttle, and does not replace the older organic experiment.

Of 2,776 stored trials, 12 fail the alignment gate, 108 have a final
click outside the main boxes, three have nonmonotonic mouse timestamps, and
one has no click. The remaining **2,652 trials / 34,916 AOI rows / 47 participants**
use identical rows and labels in the 0 and 500 ms conditions.

| Model | Pooled held-out AUC | Mean participant AUC ± SD |
|---|---:|---:|
| Position only (M1) | 0.7929 | 0.7996 ± 0.0579 |
| Seven cursor features (M4-7) | 0.9505 | 0.9510 ± 0.0208 |
| Nine cursor features (M4-9; terminal-distance diagnostic) | 0.9975 | 0.9975 ± 0.0025 |

For M4-7 versus M1, the mean participant-paired AUC difference is
**0.1514**, with participant-bootstrap 95% CI
**[0.1367, 0.1660]**. This compares models within the new typed protocol;
it is not an improvement estimate over the gaze-gated 0.9040 result.

**The 500 ms buffer removed zero samples in every included trial.** In the
recorded stream, the final mousemove precedes the click by at least
**672 ms** (median **1,799.5 ms**). Buffered and unbuffered features and
scores are consequently identical. The buffer has not tested removal of the
final approach. The very high nine-feature result is particularly compatible
with the terminal cursor position identifying the target; neither score
establishes deliberation, relevance, or browser deployment performance.
Full final-approach excision remains necessary on this cursor-only stream.

## What changed in August

The [AllSERP parsing history](bbox-attribution-lineage.md) is part of the
evidence: missing local packs and index-based joins shifted result labels;
parser/browser tree differences and duplicate DOM-node claims assigned some
cards the wrong identity or geometry. The card repairs did not rebuild the
carousel-cell producer. These are separate from the coordinate correction.

A September 4 candidate now extracts complete carousel cards and checks their
geometry against original screenshot borders. It raises count agreement from
**19/61 to 61/61** on a fixed sample, with **279 cards** and three corrected
HTML/screenshot layout shifts. Six targeted held-out spelling cases also pass.
The [comparison artifact](evidence/2026-09-04-carousel-match.json) pins sources
and denominators. A subsequent **2,776-trial full-corpus run** admits
**1,570/1,575 eligible top subdivisions**, with **7,265 cards** and matching
independent counts; the frozen source matches **465/1,575**. The
**5 rejected cases** remain unadmitted, and all 12 alignment exclusions
remain outside the candidate CSV. The [full-corpus record](evidence/2026-09-04-carousel-corpus.json)
pins the measurement. A separate eight-page review confirms captured card order
for 34 cards, with product-identity limits. The released cell export and
cell-dependent behavioral/model claims still await versioned-source adoption
and coordinated re-derivation; NB23/NB25 read the old snapshots directly.

Three changes must be distinguished: AOI realignment, correction of duplicated
card assignments, and conversion of the cursor stream into the screenshot
coordinate system. The analysis environment was also pinned after solver
changes moved some model results. The coordinate correction changed both
features and click attribution; a higher AUC after that correction is not a
new modeling contribution.

The [upstream environment and decomposition record][environment] compares the
old features in the pinned environment with the converted features. For the
seven-feature click model, the old AUC reproduces at 0.8468 and the converted
one is 0.9040; attributed clicked records change from 2,589 to 2,751. The
separate causes of the ranking-model changes have not yet been fully isolated.

## Current measured results

The [checked aggregate snapshot](evidence/2026-09-04-validation-snapshot.json)
records the selected output values, original generation dates, and SHA256
hashes. Some ablation outputs are retained locally rather than tracked
upstream; their source scripts are public. The table in this section audits
existing LAB outputs; the separate September 4 section reports the new fits.

All rows below are **LAB / AdSERP**, with leave-one-participant-out validation
(LOSO, 47 participants). These are offline results, not deployment evaluations.
AUC values in the table are pooled across held-out predictions. MRR@10 measures
reciprocal rank of the clicked result, not independently judged relevance.

| Test and measurement version | Result | Source |
|---|---|---|
| LAB click prediction, `organic_hybrid`, seven gaze-gated features (M4-7), 500 ms pre-click buffer, converted coordinates | AUC **0.9040**; position-only **0.6642** | [August 31 click-buffer grid][click-grid] |
| Binary click prediction after full final-approach excision, `organic_hybrid`, converted coordinates | M4-7 AUC **0.7633**; position-only **0.6654** | [August 31 truncation output][truncation] |
| Fixation-weighted cursor proximity dwell alone, `organic_hybrid` | AUC **0.846 → 0.637**, from 500 ms buffer to full-approach excision | [August 31 exposure/hover ladder][ladder] |
| Typed ranking, 500 ms buffer, gaze-derived four classes encoded as three grades (2/1/0/0), pinned environment | MRR@10 **0.8244**, binary LambdaMART **0.8147**; difference **+0.0097** | [August 31 grade-comparison output][ranking] |
| Same ranking experiment, four distinct grades (3/2/1/0) | MRR@10 **0.8226**; difference from binary **+0.0079** | [Same output][ranking] |

The ranking rows use the same eight input features, including **LAB gaze dwell**
(`total_dwell_ms`), and are evaluated on 2,685 ranked trials. They are a test of
label encodings with fixed features; they do not establish a cursor-only
end-to-end ranker. “Four classes” does not specify whether those classes were
encoded as three or four relevance grades. Older documents' approximately
+0.05 ranking gains must not be carried forward as current results.

For the **within-excision M4-7 versus position** comparison, the mean paired
participant AUC difference is **+0.1295** (95% bootstrap CI [0.1055, 0.1534],
Wilcoxon p = 5.27 × 10⁻¹², d_z = 1.54). This is a different aggregation from
the **+0.0979 pooled AUC difference** in the table. Do not subtract pooled
AUCs and label the result a mean paired effect.

## What the stronger control establishes

The full-approach control finds the final prominent local maximum in cursor
distance from the eventual click location, then removes subsequent cursor
and fixation samples from **every AOI's** features. It removes a median
2.88 seconds, about 18.8% of the recorded trial duration. The [producer][truncation-code]
specifies the prominence threshold, distance gate, and fallback rule.

The LAB feature set retains predictive information after this removal. The
fixation-weighted proximity field loses more discrimination and falls below position alone. That is
reason to distinguish time near the eventual click from broader examination
behavior. It is not proof that the remaining signal measures deliberation,
that the removed signal was exclusively motor preparation, or that position
bias has disappeared. Truncation also removes possible late reading and
changes which records have usable features. The onset uses the eventual
click and is therefore a retrospective diagnostic, not an online detector.

**A source-version trap:** the truncation JSON was produced before the
August 31 click-buffer grid was refreshed. Its embedded
`comparison_vs_published_buffers` and cross-window paired comparisons retain
the old buffer values. The table above reads the current buffer values from
the separate click-grid output and the truncated values from the truncation
output. The reported paired effect uses two rows from the same truncated
run. A fresh matched cross-window analysis is needed before quoting a
current percentage of the signal removed or attributing a mechanical share.

## What the labels mean

- **Observed behavior:** cursor entry, dwell, exit, return, and click; viewport
  overlap and scroll motion. Lack of cursor approach does not establish lack
  of visual examination.
- **Research supervision:** the LAB deferred/evaluated-rejected distinction
  uses gaze-regression labels. These operationalize a return of gaze; they
  do not directly measure intention, satisfaction, or document relevance.
- **Browser predictions:** the library's rules and the replay's M5 model use
  cursor information to classify behavior or estimate that research label.
  Identical class names do not make their outputs ground truth.

The [M5 calibration record](validation/m5-calibration.md) distinguishes three
historical runs: 0.794 from gaze-gated legacy features (diagnostic only),
0.769 from a gaze-clean nine-feature organic model (the replay model's
training lineage), and 0.752 from the seven-feature organic calibration.
These are different feature/supervision configurations, not interchangeable
estimates. The seven-feature summary is dated May 9; it is not evidence of an
August 31 recalibration. The 0.709 legacy gaze-clean result is retained in the
same record for provenance.

The ACD/WILD analysis is a separate **binary ad-click** experiment with
cursor-compatible feature analogs. It does not validate the four-class gaze
taxonomy outside the lab or transfer a trained LAB model unchanged. Its
[replication report](validation/attcur-bruckner.md) records the population and
feature variants.

## What remains open

1. **Cursor-only controls and matched model comparisons.** The new typed
   extraction resolves its feature provenance; full final-approach excision
   and browser visibility/sampling checks remain. The existing baselines do not establish
   superiority over all session classifiers, sequence models, or Transformers.
   Those comparisons require the same outcome, inputs, participants, and split.
2. **A fully worked real trace.** The [research index](research.md#one-distance-trace-worked-through)
   now includes a synthetic example checked against the JS extractor. A real
   replay with AOI attribution, segmentation, and all seven computations is
   still needed for the manuscript.
3. **Measurement-version propagation.** Recalibrate M5 and regenerate any
   outstanding sensitivity, sampling-rate, or viewport-selection analyses
   before treating older outputs as current. In particular, the old
   approximately 0.847 sampling-rate curve is a pre-conversion result, not a
   guarantee of rate invariance for every feature or dataset.
4. **Attribution and ranking controls.** Separate solver, geometry, and click
   label effects on the ranking gains. Cell-resolved results require their
   own rebuilt producer and validation; a corrected replay does not validate
   an old cell-level statistical claim.
5. **Prospective relevance evidence.** Test candidate behavioral grades against
   independent relevance judgments or a downstream retrieval outcome. Good
   prediction of clicks or gaze returns cannot settle that question alone.

[environment]: https://github.com/andyed/attentional-foraging/blob/a2e767db/docs/canonical-environment.md
[click-grid]: https://github.com/andyed/attentional-foraging/blob/6457394d/scripts/output/paper-output/click_buffer_ablation.json
[truncation]: evidence/2026-09-04-validation-snapshot.json
[truncation-code]: https://github.com/andyed/attentional-foraging/blob/6457394d/scripts/approach_truncation_ablation.py
[ladder]: evidence/2026-09-04-validation-snapshot.json
[ranking]: https://github.com/andyed/attentional-foraging/blob/8b30e2d7/scripts/output/ltr_typed_four_distinct_grades/summary_gaze_buf500.json

[lab-producer]: https://github.com/andyed/attentional-foraging/blob/6457394d/scripts/compute_cursor_approach_features.py
[cursor-producer]: https://github.com/andyed/attentional-foraging/blob/6457394d/scripts/m4_nb21_hybrid_rerun.py
