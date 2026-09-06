# Theory of approach/retreat

**Updated September 4, 2026.** For numerical results and source versions, use
[Current evidence](current-evidence.md); for the development of the ideas, use
[History](history.md).

## What the instrument observes

Approach-retreat records cursor entry, dwell, exit, return, and click relative
to a result's area of interest (AOI). It records viewport exposure separately.
These observations can be related to examination, but an event does not carry
its psychological interpretation with it: a cursor may rest while someone
reads elsewhere, and a result may be examined without any cursor contact.

The distinction between the **visit** and the **feature window** matters.
`Episode` represents an enter/exit visit. The seven-feature M4 vector summarizes
a result's distance trace over a longer observation window, potentially across
visits. Most reported offline analyses operate at per-(trial, result) grain.
The [research index](research.md) explains the implementation and works through
a trace numerically.

## The task-model proposal

Orient–Survey–Evaluate–Commit (OSEC) is a proposed account of search activity:
orient to the page, inspect a candidate set, examine a result, and commit to an
action or continue searching. It helps formulate questions about where to
aggregate observations and how to interpret non-clicks. Those stages are not
automatically observed just because the library has recorded an episode.

The concrete supervision proposal distinguishes four operational categories:

| Category | Observation or estimation | Interpretation limit |
|---|---|---|
| Clicked | A recorded click is attributed to the result | Click does not by itself establish satisfaction or relevance |
| Deferred | In the LAB target, an approached non-clicked result has a gaze-return label; cursor models estimate it | A return is not a direct report of an intention to defer |
| Evaluated-rejected | The complementary LAB approached/non-clicked class without that gaze-return label | Absence of a return does not prove a deliberate rejection |
| Not-approached | No qualifying cursor approach under the specified rule | The person may still have looked at or read it |

Browser heuristics, M5 predictions, and gaze-defined research labels must be
identified separately, even when their class names agree. Thresholds,
coordinate systems, and window boundaries are part of each definition.

## Why the motor control matters

Clicking requires bringing the pointer to a target. A feature that predicts
clicks can therefore succeed partly by measuring that movement. Removing the
last 500 ms is useful, but it does not necessarily remove the longer approach.
Reviewer feedback led to a control that excludes the entire operationally
defined final approach from every AOI's features.

The revised LAB experiment retains useful click discrimination under
truncation, while fixation-weighted cursor proximity loses much of its
strength. Its gaze-dependent feature construction differs from the browser
extractor and still needs a corresponding cursor-only control. That supports studying
which observations survive removal of final-approach information. It does not
identify a pure deliberation signal: the removed interval can include real
reading, and the retained interval can include motor planning. Its onset is
defined retrospectively from the click, so the control is not an online phase
detector. [Current evidence](current-evidence.md) gives the results and limits.

## What changed in our interpretation

The early “epistemic action” account proposed that retreat geometry encoded
rejection confidence through motor cost. The analyses did not establish that
mechanism. The later “curved and close means I will return” metaphor was also
retracted. We retain measurable trajectory properties without assigning those
stories to them.

Differences between ads and organic results likewise do not by themselves
identify a discrimination-cost mechanism. Element size, layout, task, and
exposure can contribute. They do not establish a violation of an economic
search model. Information-foraging and economic accounts remain useful ways
to pose hypotheses about cost and choice; causal interpretation requires tests
that separate those explanations.

The AllSERP investigations added a prior requirement: verify the page's units
before comparing behavior around them. Missing blocks, shifted labels, shared
DOM-node assignments, and incompatible coordinate systems can manufacture or
obscure apparent behavioral differences. [Attribution lineage](bbox-attribution-lineage.md)
records these failures and the remaining carousel-cell gap.

## Candidate supervision for ranking

The four classes can be encoded as graded training targets. Whether that
encoding improves a ranker is an empirical question, not a consequence of the
class names. A non-click should not automatically be called a strong negative,
and predicted deferral is not a relevance judgment.

The August ranking re-analysis found a much smaller gain over binary clicks
than earlier runs. The checked comparison holds features fixed, includes LAB
gaze dwell, and evaluates against clicked results. Independent relevance
judgments or prospective retrieval outcomes are still needed to assess the
broader training-data-quality claim.

Earlier searcher-model work already incorporated cursor and scroll observations;
[Huang, White, Buscher & Wang (SIGIR 2012)][huang] is an important precedent.
Approach-retreat contributes an explicit per-result representation and tests of
behavioral supervision. The representation could also be used by a sequence
model; nothing in the task-model proposal rules out learning these distinctions.

## Relation to ClickSense

[ClickSense](https://github.com/andyed/clicksense) instruments the way a click is
made on a target. Approach-retreat requires marked result AOIs and records visits
across them. The two instruments can run together. Their difference is the unit
and context of measurement, not proof that one captures commitment while the
other captures cognition.

The library needs no eye tracker to record its cursor and viewport channels.
Its rule-based classifications and `computeRelevance()` heuristic are available
in the browser. Training or validating an M5 estimate of a gaze-derived label
is a separate step; the library does not supply a validated relevance ranker.

[huang]: https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/Final_CursorModel_SIGIR12.pdf
