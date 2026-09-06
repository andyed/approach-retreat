# Approach-retreat: measuring behavior around individual search results

**Research overview · September 4, 2026**

A non-click leaves an unanswered question: was the result considered, passed
over, returned to, or never examined? Approach-retreat records cursor visits
and motion around individual results, alongside viewport exposure. The aim is
to make those observations useful for studying search behavior and testing
better supervision for ranking.

## The unit of measurement

The browser library records enter/dwell/exit episodes against marked areas of
interest (AOIs). It also computes seven features of each result's distance
trace: closest and mean distance, proximity dwell, mean and peak approach
rate, direction changes, and the fraction of movements toward the result.
The current feature vector aggregates across the observed window; it can span
multiple visits. A [worked synthetic trace](research.md#one-distance-trace-worked-through)
shows exactly how the values are computed.

The four-class vocabulary is **clicked / deferred / evaluated-rejected /
not-approached**. In the LAB research, gaze returns supply the deferred/rejected
supervision. Cursor rules and a calibrated model estimate related behavior
without gaze at inference. The names are operational categories, not direct
reports of intent. A person can read a result without moving the cursor to it.

## What review and the parsing audits changed

Reviewer feedback called for clearer definitions, a worked episode, more
self-contained AOI construction, and stronger separation of examination from
movement toward a click. The final-approach excision control now makes that
last question testable. On the August 31 LAB diagnostic, seven-feature click AUC is
0.9040 with a 500 ms buffer and 0.7633 after full approach excision; position
alone under excision is 0.6654. These are pooled LAB AUCs under different
observation windows, not a causal decomposition of deliberation. The LAB
producer uses fixation timing and gaze–cursor distances; these scores do not
validate the browser's different cursor-only feature construction.

Collaborator review of AllSERP also uncovered substantial page-parsing gaps:
missing local packs shifted subsequent labels; browser and parser trees
could disagree; neighboring cards could claim the same rendered element.
The repaired card pipeline and the still-incomplete carousel-cell layer must
be distinguished. [History](history.md) and [attribution lineage](bbox-attribution-lineage.md)
record what happened and what remains unresolved.

Cleaner measurements changed the ranking result as well. In the checked
August 31 typed experiment, candidate behavioral grades add approximately
0.008–0.010 MRR@10 over binary-click LambdaMART, much less than earlier runs.
This experiment includes LAB gaze dwell as an input and evaluates ranking
against clicks. It does not establish a deployed cursor-only relevance model.
The [evidence record](current-evidence.md) specifies the grade encodings,
source outputs, and remaining attribution questions.

## Contribution and next test

The contribution is an inspectable per-result instrument and a proposal for
behavioral supervision that can be tested. It builds on earlier cursor-and-scroll
searcher models, including [Huang, White, Buscher & Wang (SIGIR 2012)][huang].
It makes no general claim to outperform large feature sets or sequence models;
matched comparisons and independent relevance validation remain necessary.

The ACD/WILD replication tests binary ad-click prediction with cursor-compatible
feature analogs. The LAB gaze-return taxonomy has not thereby been validated
in WILD. The next step is to carry the corrected measurements through each
calibration and ask where behavioral grades add useful information beyond
well-attributed clicks.

[huang]: https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/Final_CursorModel_SIGIR12.pdf
