# Joachims, Granka, Pan, Hembrooke & Gay — *Accurately Interpreting Clickthrough Data as Implicit Feedback* (SIGIR '05)

[`joachims2005clickthrough`](references.bib) · [DOI 10.1145/1076034.1076063](https://doi.org/10.1145/1076034.1076063)

The behavioral-signal precedent the four-class taxonomy refines. Clicks are informative but position-biased; the *skip-above* rule recovers preference information from rank-position structure: results above a click are presumptively examined and rejected.

## The skip-above rule

> Given a click on result at rank `k`, all results at ranks `1..k−1` were examined and not preferred.

This is an inference from rank position to a behavioral state ("examined and not preferred"). It is the operational answer to "how do you mine pairwise preferences from click logs?" — Cranfield judgments without annotators. The paper validates the inference against eye-tracking on a small lab study and shows the inferred preferences are accurate enough for ranker training.

## Where approach-retreat refines this

Skip-above's limitation is named in the construct itself: it infers "examined and rejected" from **rank position**, not from observable behavior. A result at rank 3 that the user never visually attended is treated identically to one they fixated, considered, and dismissed. Click logs cannot tell those apart.

Approach-retreat's four-class taxonomy operationalizes the difference at the per-(trial, position) grain:

| Joachims category    | Approach-retreat refinement | Where the distinction lives |
|----------------------|----------------------------|-----------------------------|
| Skipped (rank above click) | **not-approached** vs. **evaluated-rejected** vs. **deferred** | Cursor + gaze tell which non-click cell each above-click result belongs to. |

The cells map onto the (0/1/2) graded relevance format LambdaMART consumes. The deferred class (a *Relevant unclicked* layer) is invisible to skip-above by construction — it requires knowing whether the user revisited the AOI, which click position cannot represent.

## Empirical lift over skip-above-style training

CIKM §4.6 reports the comparison directly: a LambdaMART ranker trained on the four-class graded labels beats the binary-click baseline (the closest LambdaMART analog of skip-above) by ΔMRR@10 +0.051 on identical features. The improvement is the labeling refinement itself — same input vector, different labels — and the deferred-class signal click logs cannot recover.

## Notes for the CIKM paper

§2 cites this work as the **behavioral precedent for inferring preference from rank position**, calling out the limitation that motivates our four-class taxonomy. Cite as `\cite{joachims2005clickthrough}`. The skip-above limitation is the most reviewer-relevant single-sentence framing in §2 — keep it sharp.

## Adjacent work that uses skip-above

- Click models (Craswell, Chapelle & Zhang, Dupret & Piwowarski) all consume skip-above-style inferences as training signal.
- THUIR PSCM / CBCM (Wang '15, Zhang '21) work at the same click-likelihood granularity skip-above operates on; they refine the *examination model* but inherit skip-above's "rank position = behavior state" assumption.
- The hard-negatives literature (`hard-negatives-in-ltr.md`) treats skip-above as a hard-negative source for dense retrievers; the same critique applies — the inference is from rank, not from behavior.
