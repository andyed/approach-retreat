# Dumais, Buscher & Cutrell — *Individual Differences in Gaze Patterns for Web Search* (IIiX 2010)

[`dumais2010individual`](references.bib) · [DOI 10.1145/1840784.1840812](https://doi.org/10.1145/1840784.1840812) · *Proceedings of the Third Symposium on Information Interaction in Context (IIiX '10)*, New Brunswick, NJ.

The participant-level taxonomy precedent. Dumais's group (with Buscher and Cutrell, Microsoft Research) used eye-tracking on a Bing-style SERP encounter and **clustered participants by their gaze-pattern signatures** to identify groups with distinct examination styles — how exhaustively they examined results, and which page regions (organic results, ads, related searches) they paid attention to.

## Method

- Eye-tracking on web search tasks, instrumented at the same Microsoft Research lab whose at-scale cursor work [Huang, White & Buscher 2012] follows two years later.
- AOIs include the 10 organic results *plus* page chrome — ads, related searches, the SERP layout components contemporary search engines were adding around the organic core. The methodological choice of including non-organic AOIs is a precedent for `approach-retreat`'s `organic_hybrid` attribution in CIKM §3.1.
- **Clustering** on per-participant gaze-pattern descriptors yielded a small number of groups with qualitatively distinct examination styles. The paper names the resulting taxonomy at the participant grain — *this person scans exhaustively, this person locks onto the first relevant-looking result, this person attends to ads*.

## Where approach-retreat extends this

Approach-retreat's four-class taxonomy operates at the **per-(trial, position) grain** rather than the per-participant grain. The 2D structure (clicked / deferred / evaluated-rejected / not-approached, indexed by trial × AOI position) is a finer-resolution version of Dumais's participant-level clustering: instead of asking "what kind of searcher is this person?" the taxonomy asks "what kind of engagement did this AOI receive on this trial?"

Both levels of resolution are useful, and they answer different questions:

| Question | Grain | Construct |
|----------|-------|-----------|
| What kind of searcher is this person? | Per-participant | Dumais 2010 clusters |
| What kind of engagement did this AOI receive on this trial? | Per-(trial, position) | Approach-retreat 4-class taxonomy |
| What kind of decision phase is the cursor in right now? | Per-fixation-window | Soft-constraints / Gray microstrategies (CIKM §3.3) |

The mapping from per-trial-position to per-participant is a sum or distribution over the participant's trials — Dumais's taxonomy is recoverable from approach-retreat's grid by aggregation. The reverse is not true: approach-retreat's per-(trial, position) labels carry information the participant-level cluster cannot represent, which is what makes the four-class taxonomy a graded-relevance label generator (CIKM §4.6).

## Notes for the CIKM paper

§2 cites this work as the **participant-level taxonomy precedent**:

> The 2D structure operationalizes per-(trial, position) the participant-level taxonomy Dumais, Buscher & Cutrell [IIiX '10] obtained via gaze-pattern clustering.

Cite as `\cite{dumais2010individual}`. The framing matters: this is a precedent (the *idea* of clustering search behavior into a behavioral taxonomy), not a competitor (the unit of resolution and the downstream LTR target are different). The paper is best read alongside `joachims-2005-clickthrough.md` for the IR-side antecedents to behavioral graded-relevance labels.

## Adjacent work

- **Buscher, Dumais & Cutrell — *The Good, the Bad, and the Random* (SIGIR '10).** Same group, same year. Eye-tracking study of ad quality and how gaze patterns shift with ad relevance. Companion volume to this paper.
- **Buscher et al. — *Large-Scale Analysis of Individual and Task Differences in Search Result Page Examination Strategies* (WSDM '12).** Two years later, scales up the individual-differences finding using cursor-only telemetry on Bing — implicitly the move from per-participant gaze clustering to per-trajectory cursor analysis the cursor-feature classifier tradition (Brückner, Arapakis, Leiva) builds on.
