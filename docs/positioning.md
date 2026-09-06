# Where approach-retreat sits in the literature

**Updated September 4, 2026.** The methods manuscript is under revision.
The proposed contribution is an inspectable per-result representation and
candidate behavioral supervision for ranking. Its value must be assessed
against earlier work under matched tasks and measurement conditions.

## The relevant comparisons

| Research question | Relation to approach-retreat | What a fair comparison requires |
|---|---|---|
| Can hover and scroll improve searcher models? | An established precedent: Huang, White, Buscher & Wang (SIGIR 2012) extend an examination model with these signals | Same prediction target and evaluation protocol; do not imply cursor-assisted search modeling began here |
| Can cursor behavior estimate gaze or attention? | Related to the LAB calibration question, but predicting clicks, fixation, and gaze returns are different tasks | Match the supervised target and distinguish gaze at training from gaze at inference |
| How should a trajectory be represented? | Whole-session statistics, learned sequences, and per-result aggregates preserve different information | Same telemetry, AOIs, truncation, train/test split, and outcome; feature count is not an accuracy result |
| Can non-click behavior improve ranking supervision? | The four-class proposal tests candidate grades derived from behavior | Hold input features fixed; state grade encoding, label source, exclusions, and ranking ground truth |

[Huang et al.'s author-hosted SIGIR paper][huang] is the four-author
*Improving searcher models using mouse cursor activity*. It is distinct from
Huang, White & Buscher's three-author CHI 2012 *User see, user point* study.
Reviewer feedback helped expose the missing connection in the earlier account.

The [Liu et al. two-stage examination note](references/liu-2014-skimming.md)
is another relevant per-result comparison. The bibliography and literature notes
provide leads for positioning; their existence does not certify a matched
baseline or a field-wide novelty claim.

## What is specific to this project

The project makes per-result cursor measurements available in a browser library,
keeps episode records alongside feature aggregates, and links those measurements
to a research program using gaze-defined returns and candidate ranking grades.
It exposes the feature definitions and the observation window so the approach
can be inspected and reproduced.

The [history](history.md) traces Andy Edmonds' own instrumentation lineage from
Lucidity and Optimoz through Uzilla and ClickSense. Uzilla is documented prior
work for that line; it does not establish that all later path-length measures,
DOM instrumentation, or learned trajectory representations descended from it.
Later papers should be credited for their own tasks and methods.

Information-foraging and economic search models provide ways to ask about cost,
examination, and choice. Approach-retreat does not establish that an observed
ad/organic difference violates C/W/L, or that cursor geometry directly measures
a marginal-utility calculation. The collaboration with Leif Azzopardi helped connect this measurement work
to questions about search behavior, cost, and usable evidence.

## What the evidence supports so far

- **LAB click prediction:** the measured advantage over position survives full
  final-approach excision, with a reduced absolute AUC. The current
  LAB producer uses gaze-dependent features; this is neither browser
  cursor-only validation nor proof of a cognitive mechanism.
- **LAB gaze-return estimation:** M5 has several distinct historical calibration
  configurations. Their scores are not interchangeable, and browser predictions
  are not gaze ground truth.
- **WILD binary ad clicks:** the ACD replication evaluates cursor-compatible
  feature analogs. It does not validate the LAB four-class target in WILD.
- **Ranking supervision:** the checked updated grade-comparison experiment has
  a modest improvement over binary-click LambdaMART. It includes LAB gaze dwell
  as an input and uses clicked results as evaluation gold.
- **Portability:** demonstrations on other interfaces establish that the
  instrumentation can run there. They do not establish that the behavioral
  interpretation or prediction accuracy transfers unchanged.

[Current evidence](current-evidence.md) identifies the exact outputs behind
these statements. [Attribution lineage](bbox-attribution-lineage.md) explains
why the page-parsing corrections are part of interpreting every result.

## Claims still requiring a test

No general superiority over session classifiers, sequence models, or
Transformers has been established by comparing approach-retreat's own feature
ablations. A learned model could use the same AOI structure and supervision;
there is no basis to say it could not discover similar distinctions.

Likewise, strong click prediction does not establish high-quality relevance
labels. Matched baselines, recalibration on the repaired measurement pipeline,
and independent relevance or downstream retrieval evaluation are the next
steps. These are empirical questions the task model helps organize.

[huang]: https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/Final_CursorModel_SIGIR12.pdf
