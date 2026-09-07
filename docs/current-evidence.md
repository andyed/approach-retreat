# Current evidence and open questions

**Checked 2026-09-07: press-anchored cursor-only results, nested ranking, and matched window/rate comparisons retained; earlier measurement versions remain dated below.**

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

## September 6: a press-anchored cursor-only headline

The [retained September 6 aggregates](evidence/2026-09-06-press-anchored-cursor.json)
pin the upstream source paths, complete source-file SHA256 hashes, original
producer hashes, AOI substrate, and analysis environment. They cover the click
model, deferred/rejected classifier, gaze-return diagnostics, and ranking
experiment. These are **[LAB, AdSERP, typed, native cursor-only predictors]**;
gaze-derived supervision is identified separately below. The source snapshot
was inspected at upstream commit `c55da325`.

The September 4 buffer removed nothing because the recorded final `click`
arrives well after the corresponding `mousedown`: a median **1,421 ms**
(IQR **1,172.75–1,853.25 ms**) in the new included population. The last
mousemove precedes the press by a median **294 ms**. The new producer therefore
ends the feature window at **`mousedown` minus the buffer**, while the final
click still supplies the outcome label. This timing diagnosis comes from the
subsequent author audit; reviewer questions had motivated the broader need to
test terminal-approach dependence.

The replay calls the actual browser `ResultFeatureTracker`, using native
mousemove and vertical cursor-to-AOI distance in document CSS pixels. Row
selection and click-prediction features use no gaze. Click labels require
unique X+Y containment in a main-axis typed box, and every main-axis AOI in an
included trial gets a row. There is no browser visibility gate or sampling
throttle, so this is an offline all-AOI experiment, not a browser calibration.

The 0/250/500/1,000 ms grid shares **2,608 trials / 34,328 AOI rows / 47
participants**. Starting from 2,776 trials, the filters remove 12 alignment
exclusions, 108 off-box clicks, three nonmonotonic mouse streams, one missing
click, and 44 trials without sufficient pre-buffer mousemove. The following
LOSO balanced-logistic-regression results use the **500 ms pre-press buffer**:

| Model | Pooled held-out AUC | MRR@10 against click |
|---|---:|---:|
| Position only (M1) | **0.7918** | 0.4471 |
| Position plus seven cursor features (M3) | **0.9348** | 0.7748 |
| Seven cursor features (M4-7) | **0.9348** | 0.7773 |
| Nine cursor features (M4-9; terminal-distance diagnostic) | **0.9903** | 0.9498 |

For M4-7 versus M1, the mean participant-paired AUC difference is **+0.1379**
(bootstrap 95% CI **[0.1242, 0.1514]**). M3 and M4-7 are nearly tied; this
particular comparison does not show an additional benefit from the position
feature. The pooled M4-7 AUC is **0.9494 without a buffer, 0.9348 at 500 ms,
and 0.8852 at 1,000 ms**. Unlike the September 4 click-anchored run, the 500 ms
buffer removes **21,223 samples across 1,705 trials**; the 1,000 ms buffer
removes **56,742 samples across 2,099 trials**. These are within-grid matched
comparisons. A useful time buffer still does not establish that the full
terminal approach is gone or give the surviving signal a psychological
interpretation. The nine-feature row remains diagnostic for endpoint effects.

## September 6: downstream tests on the same cursor features

The deferred/evaluated-rejected test uses **9,932 approached non-click rows**
(`min_dist < 100 px`) and retains the NB22 **gaze-regression target**. Seven
cursor features achieve **0.6911 pooled AUC** on the full pool. On **9,911
shared rows**, native cursor sampling achieves **0.6922**, compared with
**0.7151** when cursor positions are interpolated at fixation onsets. That is
a gaze-gated sampling comparator with the same rows, labels, anchor, and
buffer; it is not a gaze-free model. Its mean participant-paired AUC advantage
is **0.0074**, with bootstrap 95% CI **[−0.0049, 0.0198]**. The pooled gap and
the participant-paired difference answer different aggregation questions.
Neither score validates the research label outside LAB.

Two related diagnostics use the same underlying **2,608-trial cursor-feature
cache**, with separate populations:

- Among **6,800 deferred rows**, **55.37%** have at least two counted gaze
  re-entries into an earlier result position. This is a gaze-return measure,
  not cursor reconsultation or evidence of semantic integration.
- Among clicked, approached AOIs with exactly one detected cursor visit, the
  gaze-regression target occurs in **70.89% of 1,745 rows**. M4-7 yields
  **0.6599 pooled AUC**, with 45 evaluable participant folds. This subset shows
  what the cursor features predict when the specified cursor-visit detector
  records no revisit; its visit definition is pinned in the retained aggregate.

The September 6 ranking experiment holds seven **cursor-only input features**
fixed, uses an outer LOSO ranker split by participant, and evaluates against the
observed click on **2,608 trials**. Its training population excludes
`NotApprBelow` rows and its scoring population retains all rows. Behavioral
grades use either the LAB gaze-regression labels or predictions from the
cursor classifier trained to estimate that label. The September 7 audit below
qualifies the cursor-predicted-label rows; their original aggregate is retained
unchanged as a historical diagnostic.

| Ranking supervision/model | MRR@10 | Difference from binary LambdaMART |
|---|---:|---:|
| Binary-click LambdaMART | **0.7742** | — |
| Four distinct grades, gaze-derived labels | **0.7856** | **+0.0114** |
| Four distinct grades, cursor-predicted labels (**non-nested diagnostic**) | **0.7788** | **+0.0046** |
| Pointwise binary-click logistic regression | **0.7837** | **+0.0095** |

The binary-click and gaze-label rows do not have the label-generation
dependency identified below. Pointwise logistic regression exceeds the gaze
three-grade variant but is below the gaze four-grade result. The table reports
numerical differences, not a test of their uncertainty; none of these rows
evaluates independently judged relevance or deployment.

**September 7 label-generation audit:** the original cursor-label run first
computes one global LOSO label vector, then reuses it across outer ranker folds.
For held-out ranker participant P, a training participant Q can therefore have
labels predicted by a classifier trained on P's gaze labels. Leaving Q out of
that classifier is insufficient to keep P outside the complete ranker-training
pipeline. The historical **+0.0046** cursor-label gain is consequently **not a
clean end-to-end held-out estimate**. The completed nested rerun below generates
each outer ranker fold's training grades with inner LOSO restricted to the outer
training participants. The September 6 snapshot is kept intact to make
this correction traceable. This issue concerns learned ranking supervision;
it does not change the independently fitted cursor click model or the matched
window/rate results below.

## September 7: ranking with nested cursor-label generation

The [nested ranking aggregate](evidence/2026-09-07-nested-cursor-ranking.json)
keeps the same **2,608 trials / 34,328 AOI rows / 47 participants**, seven
cursor features, 500 ms pre-press buffer, grade rules, and estimators. In each
of **47 outer participant folds**, training grades are generated by **46 inner
participant folds**, using only the outer training partition. Feature scaling,
labeler fitting, and the fixed **0.5** threshold all operate without the outer
test participant's gaze labels entering the training-grade pipeline. The
ranker still evaluates against held-out clicks.

| Ranking supervision/model | MRR@10 | Difference from binary LambdaMART |
|---|---:|---:|
| Binary-click LambdaMART | **0.7742** | — |
| Three-grade collapse, nested cursor-predicted labels (2/1/0/0) | **0.7797** | **+0.0055** |
| Four distinct grades, nested cursor-predicted labels (3/2/1/0) | **0.7792** | **+0.0050** |
| Pointwise binary-click logistic regression | **0.7837** | **+0.0095** |
| Four distinct grades, gaze-derived labels | **0.7856** | **+0.0114** |

The modest cursor-label lift over binary LambdaMART remains after correcting
the split. The three-grade collapse is numerically **0.0006 MRR@10 above** four
distinct cursor grades; this result does not support a benefit from separating
all four grades. Both cursor-label rankers remain below pointwise binary-click
logistic regression. All five non-cursor benchmark metric objects, including
ad/organic slices, exactly reproduce the September 6 outputs.

No uncertainty test for these ranking differences is reported, and the nested
ranker's feature ablations have not run. The labeler remains trained against
LAB gaze-regression targets; correcting the split does not supply independent
relevance judgments or establish a WILD result. The retained September 6
**+0.0046** cursor-label result is historical, not the current estimate.

The four-grade result itself increased from **0.7788 to 0.7792**; three
grades increased more, from **0.7758 to 0.7797**. The unestablished extra-grade
advantage does not invalidate the four behavioral classes. The
[fourth-grade exploration](../../attentional-foraging/docs/null-findings/2026-09-07-cursor-fourth-grade-nested.md)
separates those claims and records the next diagnostics: participant-paired
uncertainty, label changes near the 0.5 threshold, and a controlled gain-mapping
comparison. These diagnostics are planned, not completed.

## September 7: the window comparison on shared trials

The original window and sampling-rate sweeps use different eligible trial
populations. The matched follow-up instead intersects **whole trials**, checks
that their AOI positions, types, and click labels agree, and refits the same
LOSO models on each condition's features. The native condition retains the
headline grid's requirement for usable samples before the 1,000 ms cutoff;
the sensitivity runs retain their original 500 ms eligibility rule before
intersection. All features in the comparison use the **500 ms pre-press
buffer**. These estimates apply to the shared cohort, not all eligible trials
from any one original run.

The window intersection contains **1,382 trials / 18,227 AOI rows / 46
participants**. The end of the fifth fixation defines the boundary: `pre5`
uses cursor samples before it, and `post5` uses those from that boundary to the
buffer cutoff. Predictors use cursor values; **gaze defines the boundary and
window eligibility**.

| Condition on the shared window cohort | Pooled held-out AUC |
|---|---:|
| Position only (M1) | **0.7943** |
| Native whole-window M4-7 | **0.9318** |
| M4-7 before the end of fixation 5 (`pre5`) | **0.7830** |
| M4-7 after the end of fixation 5 (`post5`) | **0.9370** |

The post5/pre5 contrast survives trial matching: its mean participant-paired
AUC difference is **+0.1566**, with bootstrap 95% CI **[0.1385, 0.1735]**.
Post5 also exceeds the native whole window by **+0.0044** on that participant
measure (95% CI **[0.0022, 0.0067]**); the corresponding pooled difference is
**+0.0052**. These are exploratory comparisons without multiplicity correction.
Pre5 is below position alone in pooled AUC here, but its **0.7830** score is not
chance-level performance.

Matching removes the change in trial membership from these comparisons. It
does not equalize window duration or sample count, and post5 can still retain
terminal approach. The result therefore does not isolate deliberation, prove
that endpoint information is absent, or validate a gaze-free window policy.
The [matched aggregate](evidence/2026-09-07-matched-sensitivity.json) retains the
source and feature hashes, intersection counts, and paired statistics.

## September 7: sampling rates on a shared cohort

The rate comparison shares **2,544 trials / 33,518 AOI rows / 47 participants**
across native, 30, 15, 5, and 1 Hz conditions. It uses the same whole-trial
matching and 500 ms pre-press feature cutoff, with no gaze-dependent boundary.
Position alone gives **0.7895 pooled AUC** on this cohort.

| Sampling condition | M4-7 pooled held-out AUC |
|---|---:|
| Native mousemove | **0.9338** |
| 30 Hz | **0.9338** |
| 15 Hz | **0.9341** |
| 5 Hz | **0.9332** |
| 1 Hz | **0.9012** |

At 5 Hz, the mean participant-paired AUC difference from native is **−0.0012**
(bootstrap 95% CI **[−0.0033, 0.0011]**). At 1 Hz it is **−0.0329**
(**[−0.0393, −0.0268]**), with a pooled difference of **−0.0327**. These are
exploratory comparisons without multiplicity correction. The observed
performance differences down to 5 Hz are small in this matched offline
experiment; no equivalence margin or equivalence test was specified, so the
result does not establish rate invariance. All conditions are restricted to
trials eligible at every tested rate, including 1 Hz. The experiment also does
not reproduce browser visibility or lifecycle filtering.

The [retained matched aggregate](evidence/2026-09-07-matched-sensitivity.json)
pins both comparison families and their input hashes. All six sensitivity
replays reproduced the original retained feature hashes before matching and
refitting. AOI-flavor sweeps have different candidate populations and retain
their separate protocol labels.

## Earlier producers measured different things

The **August gaze-gated LAB scores** below are not a verified replacement for
the browser's cursor-only calibration. Their [LAB producer][lab-producer]
samples cursor positions at fixation times, computes distance fields from
**gaze–cursor distance**, and accumulates proximity dwell using fixation
durations. The browser's `ResultFeatureTracker` instead computes vertical
cursor-to-AOI distance and interval dwell from `mousemove` events. The shared
feature names and `M4-7` label conceal different measurements.

The August click grid reads those LAB feature files; the August excision
script calls that LAB producer directly. The ladder's “hover” row uses its
fixation-weighted proximity field. Those dated results are therefore **LAB
diagnostics with gaze-dependent feature construction**. The historical
[cursor-only hybrid extractor][cursor-producer] uses XPath observations plus
linear fallback centers; its code has no buffered `organic_hybrid` option.
Earlier documentation incorrectly attached the buffered-organic headline to
that script. The September typed experiments resolve their feature provenance
by calling the actual browser accumulator, with their own populations and
windows.

## September 4: a cursor-only typed stream

**Historical click-anchored run; superseded as the headline by the September 6
press-anchored experiment above.** Its unchanged buffer is the observation that
led to the timing diagnosis, and its original aggregate remains intact.

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

## August LAB results, retained for lineage

The [checked aggregate snapshot](evidence/2026-09-04-validation-snapshot.json)
records the selected output values, original generation dates, and SHA256
hashes. Some ablation outputs are retained locally rather than tracked
upstream; their source scripts are public. The table in this section audits
the August LAB outputs; the September sections above identify the later fits.

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

## What the August full-approach control establishes

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

1. **Cursor-only controls and matched model comparisons.** The press-anchored
   typed extraction resolves feature provenance and makes the time buffer
   effective. Full final-approach excision and browser visibility/sampling
   checks remain. The existing baselines do not establish
   superiority over all session classifiers, sequence models, or Transformers.
   Those comparisons require the same outcome, inputs, participants, and split.
2. **A fully worked real trace.** The [research index](research.md#one-distance-trace-worked-through)
   now includes a synthetic example checked against the JS extractor. A real
   replay with AOI attribution, segmentation, and all seven computations is
   still needed for the manuscript.
3. **Measurement-version propagation.** Window, sampling-rate, and AOI-flavor
   sweeps now exist for the press-anchored cursor-only protocol. Window and
   rate comparisons have been refit on their respective shared cohorts;
   AOI-flavor differences retain separate candidate populations. M5
   recalibration and browser viewport-selection parity remain open. The old
   approximately 0.847 sampling-rate curve belongs to a pre-conversion protocol.
   The 148 replay bundles received substrate stamps in September; that metadata
   update is not retraining of their M5 model.
4. **Attribution and ranking controls.** The nested cursor-label rerun is
   complete; uncertainty for the small ranking differences and nested-ranker
   feature ablations remain open. Retain the earlier global-LOSO result as a
   non-nested diagnostic. Separate solver, geometry, and click-label effects on
   earlier ranking changes. Cell-resolved results require their
   versioned source adoption and consumer migration after candidate validation
   (1,570/1,575 = 99.68% eligible top-parent count agreement, five explicit
   rejections). The frozen source is still in use by cell-dependent consumers;
   a corrected replay does not validate an old cell-level statistical claim.
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
