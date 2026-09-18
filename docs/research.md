# Approach/Retreat — research index

**Updated September 7, 2026.**

Approach-retreat records how a cursor moves around individual results on a
search engine results page (SERP). It also records which results were in the
viewport. The research asks whether these observations help describe
examination and improve the behavioral labels used to train a ranker.

Start with [Current evidence](current-evidence.md) for the September press-anchored
re-analysis, matched-cohort checks, source-pinned numbers, and unresolved questions. [History](history.md) explains
how the instrumentation, collaboration, reviewer feedback, and page-parsing
audits brought us here. The companion methods manuscript is under revision.

## Measurement before interpretation

There are three related, distinct objects:

| Object | What it contains | What it does not establish |
|---|---|---|
| Browser cursor episode | Entry, dwell, exit, return, click, and motion relative to an AOI | Whether the user read, rejected, or intended to revisit the result |
| Per-result feature vector | Aggregates of cursor distance and approach rate over the observation window | That each aggregate describes one psychologically discrete episode |
| Research label | LAB gaze-return labels, or a model's cursor-based estimate of them | Independent relevance or satisfaction ground truth |

The library's `Episode` records are enter/exit visits. `getApproachFeatures()`
aggregates each result's samples across the tracked window, which can span
several visits. The main offline experiments use per-(trial, result) aggregates. The newest
LAB producer also differs in sensor construction: it samples at fixation
times and uses gaze–cursor distances, while the browser uses mousemove
cursor-to-AOI distances. Shared field names do not establish extractor parity.
A fully sessionized model of individual deliberation episodes remains a further
step; the process account should not imply that it is already the estimator.

The LAB deferred/evaluated-rejected target uses **gaze regression**. The browser
heuristic and the replay's M5 model are different estimators with the same class
vocabulary. [M5 calibration](validation/m5-calibration.md) and the
[replay curation rubric](CURATION.md) specify those distinctions.

## What the library computes

The canonical M4-7 vector consists of seven distance-trace features:

| Feature | Operational meaning |
|---|---|
| `min_dist` | Closest approach to the AOI center coordinate |
| `mean_dist` | Mean distance across samples |
| `dwell_in_proximity_ms` | Accumulated intervals ending within the proximity band |
| `mean_approach_velocity` | Mean signed rate of closing distance |
| `max_approach_velocity` | Maximum signed closing rate |
| `direction_changes` | Changes in the sign of closing rate, including transitions through zero |
| `frac_decreasing` | Fraction of sample transitions that reduce distance |

The current JS `ResultFeatureTracker` uses **vertical page-space distance**
`abs(pageY − pageYCenter)`. This is distinct from the two-dimensional bbox
hit-test used for episode entry. See the
[source](../src/approach-retreat.js) and generated
[feature glossary](feature-glossary.md) for each field's implementation and
its LAB/WILD counterpart.

`final_dist` and `retreat_dist` are also emitted, but excluded from M4-7 because
they are strongly affected by ending at the clicked target. The seven retained
features can also carry final-approach information: “seven features” is not a
guarantee of independence from clicking. Training and evaluation must specify
the available observation window.

### One distance trace worked through

This synthetic example illustrates the JS extractor; it is not participant
data or a validation result. Fix an AOI's page-space Y center at 500 px, use
a 100 px proximity band, and feed these five samples:

| Time (ms) | Cursor page Y (px) | Distance (px) | Signed closing rate (px/s) |
|---|---|---|---|
| 0 | 700 | 200 | — |
| 100 | 580 | 80 | +1,200 |
| 200 | 540 | 40 | +400 |
| 300 | 620 | 120 | −800 |
| 400 | 560 | 60 | +600 |

The resulting seven features are:

```js
{
  min_dist: 40,
  mean_dist: 100,
  dwell_in_proximity_ms: 300,
  mean_approach_velocity: 350,
  max_approach_velocity: 1200,
  direction_changes: 2,
  frac_decreasing: 0.75
}
```

Mean distance is `(200 + 80 + 40 + 120 + 60) / 5`. Three intervals end
inside the band, so proximity dwell is 300 ms under the implementation's
endpoint convention. The signed rates average to 350 px/s; their signs are
`+,+,−,+`, giving two changes. Three of four transitions close the distance.
The two additional descriptive fields are `final_dist: 60` and
`retreat_dist: 20`. These values were checked by feeding the samples to
`ResultFeatureTracker.update()` and reading `getFeatures()`.

This trace crosses the proximity threshold more than once. It also shows why
one per-result vector need not equal one visit. A real worked example for the
manuscript must additionally show the bbox, episode boundaries, and exclusion
window on the replay itself.

## What the controls changed

A 500 ms pre-click buffer removes the terminal lock-on window. Reviewer
questions prompted a stronger test: remove the whole final approach to the
click from every result's feature inputs. The current headline is the
**cursor-only typed replay** of the browser tracker, press-anchored with a
500 ms buffer (`attentional-foraging/scripts/output/m4_cursor_aoi_mousedown/summary.json`):
M4-7 pooled AUC 0.935, position alone 0.792. The full-approach excision
control has not yet been run on this stream. The August 31 excision numbers
(M4-7 0.9040 with the buffer, 0.7633 after excision, position 0.6654) were a
gaze-gated LAB diagnostic on the fixation-selected stream and are retained
as lineage in the [evidence record](current-evidence.md). When the excision
runs on the cursor-only stream, neither the removed nor the retained portion
can be assigned a purely cognitive or purely motor interpretation from that
test alone.

The [current evidence record](current-evidence.md) explains the changing
population, the retrospective definition of onset, and the distinction between
pooled and participant-paired effects. It also identifies a mixed-version trap
in the truncation output's embedded old baseline rows.

## Viewport measurements

The cursor-free channel combines scroll events and AOI bounding boxes. It
reports overlap duration, time near viewport center, average viewport position,
and scroll speed/reversals while an AOI is visible. Viewport presence is an
opportunity for examination, not proof of attention.

Top/middle/bottom bands remain useful descriptive outputs. Earlier claims that
a minimal continuous set recovered all predictive signal, with no additional
value from bands, should not be treated as current: the typed re-analysis
changed that comparison. The [upstream NB30 annotations][claims] distinguish
rerun results from pending feature-selection work.

The browser defaults to 15 Hz cursor sampling to reduce processing cost. The
older sampling ablation was nearly flat around 0.847 AUC from native rate to
1 Hz, but used pre-conversion features. That is historical evidence for this
engineering choice, not proof that every feature is rate-invariant or that the
same accuracy holds on the revised substrate.

## LAB and WILD answer different questions

**LAB / AdSERP** supplies cursor, gaze, pupil, page snapshots, and click data.
It supports comparisons with gaze-derived labels and scrutiny of the page
reconstruction. Its tasks, participants, and AOI construction bound the claims.
[AllSERP](https://arxiv.org/abs/2605.04949) documents the enrichment effort;
[attribution lineage](bbox-attribution-lineage.md) records later parsing gaps
and repairs. A paper version, flavor name, or plausible replay alone does not
certify every derived artifact.

**WILD / Attentive Cursor Dataset** supplies cursor and click data. The
[self-contained analysis](../analysis/attcur-validation/README.md) and
[replication report](validation/attcur-bruckner.md) test binary ad-click
prediction using feature analogs suitable for that telemetry. This is
construction-level replication on a different task/population, not validation
of the four-class gaze-return taxonomy outside the lab.

## Relation to earlier work

Cursor and scroll information in searcher models are established ideas.
[Huang, White, Buscher & Wang (SIGIR 2012)][huang] used hover and scroll data
to extend an examination model and improve click prediction. This is a direct
precedent, distinct from the three-author CHI 2012 gaze–cursor alignment study.
Reviewer feedback helped bring that relationship into focus.

Approach-retreat's emphasis is an inspectable per-result representation and
explicit tests of candidate non-click supervision. Feature count alone does
not establish superiority. A neural or sequence model could use the same AOIs,
observation windows, and supervision. Fair comparisons require matching those
choices. [Positioning](positioning.md) separates the contribution from the
comparisons still needed.

## Reproduction and further reading

- [Current evidence](current-evidence.md): pinned producer outputs and limitations.
- [Attribution lineage](bbox-attribution-lineage.md): parsing, coordinates, exclusions, cell-layer gaps.
- [Key claims](key-claims.md): stable historical claim IDs; check their measurement versions.
- [M5 calibration](validation/m5-calibration.md): training recipe and distinct legacy model runs.
- [Feature glossary](feature-glossary.md): generated field definitions and sensor distinctions.
- [One-page account](one-pager.md) and [theory](theory.md): the research question and interpretation limits.
- [History](history.md): the personal lineage and commit archaeology.

[claims]: https://github.com/andyed/attentional-foraging/blob/b5d66959/docs/notebook-key-claims.md
[huang]: https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/Final_CursorModel_SIGIR12.pdf
