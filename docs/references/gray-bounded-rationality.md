# Bounded Rationality and Continuous Motor-Cognitive Co-Optimization
## Key Claims from Gray's *Milliseconds Matter* and the *Soft Constraints Hypothesis*

This document captures the foundational claims from Wayne Gray and
collaborators that anchor the theoretical frame of the Edmonds 2026 CIKM
paper (*Cognitive Task Models Recover SERP Examination Signal Invisible to
Atheoretic Cursor Feature Extraction*) and the `approach-retreat` library
itself. Each claim has a stable K-ID, a verified citation, and a relevance
note explaining how it bears on cursor-cognition coupling on SERPs.

The intellectual chain is: **Simon (1956) → Anderson rational analysis
(1990) → Gray *Milliseconds Matter* (2000) → Gray *Soft Constraints
Hypothesis* (2006) → ACT-R production rules → cursor-gaze coupling
literature in IR → this paper**. Bounded rationality is the theoretical
mechanism; cursor-gaze coupling is the empirical signature; and the
deferred-class taxonomy + nine-feature M4 result are demonstrations.

---

## Sources

### Bounded-rationality lineage (psych side)

| ID | Citation |
|---|---|
| **Simon-1956** | Simon, H. A. (1956). *Rational choice and the structure of the environment.* **Psychological Review**, *63*(2), 129–138. (foundational bounded-rationality paper) |
| **Anderson-1990** | Anderson, J. R. (1990). *The Adaptive Character of Thought.* Hillsdale, NJ: Lawrence Erlbaum. (rational-analysis program; precursor to ACT-R) |
| **G&BD-2000** | Gray, W. D. & Boehm-Davis, D. A. (2000). *Milliseconds matter: An introduction to microstrategies and to their use in describing and predicting interactive behavior.* **Journal of Experimental Psychology: Applied**, *6*(4), 322–335. [PMID 11218341](https://pubmed.ncbi.nlm.nih.gov/11218341/) |
| **GSFS-2006** | Gray, W. D., Sims, C. R., Fu, W.-T. & Schoelles, M. J. (2006). *The soft constraints hypothesis: A rational analysis approach to resource allocation for interactive behavior.* **Psychological Review**, *113*(3), 461–482. [PMID 16802878](https://pubmed.ncbi.nlm.nih.gov/16802878/) |

### IR cursor-gaze coupling lineage

| ID | Citation |
|---|---|
| **CAS-2001** | Chen, M.-C., Anderson, J. R. & Sohn, M. H. (2001). *What can a mouse cursor tell us more? Correlation of eye/mouse movements on web browsing.* **CHI '01 Extended Abstracts**, 281–282. **Note:** This Anderson is the same John R. Anderson of *The Adaptive Character of Thought* (1990) and ACT-R. The IR cursor-gaze tradition has the rational-analysis lineage co-authored into its founding paper. |
| **HWB-2012** | Huang, J., White, R. W. & Buscher, G. (2012). *User see, user point: Gaze and cursor alignment in web search.* **CHI '12**, 1341–1350. DOI: 10.1145/2207676.2208591 |
| **S&C-2023** | Stone, S. A. & Chapman, C. S. (2023). *Unconscious Frustration: Dynamically Assessing User Experience using Eye and Mouse Tracking.* **Proceedings of the ACM on Human-Computer Interaction**, *7*(ETRA), Article 168, pp. 1–17. DOI: 10.1145/3591137 |

### IR-side bounded-rationality program (Azzopardi cluster — strategic interaction grain)

| ID | Citation |
|---|---|
| **Az-2011** | Azzopardi, L. (2011). *The economics in interactive information retrieval.* **SIGIR '11**, pp. 15–24. DOI: 10.1145/2009916.2009923 |
| **Az-2014** | Azzopardi, L. (2014). *Modelling interaction with economic models of search.* **SIGIR '14**, pp. 3–12. DOI: 10.1145/2600428.2609574 |
| **M&Az-2018** | Maxwell, D. & Azzopardi, L. (2018). *Information scent, searching and stopping.* **ECIR '18**. Foraging-grounded SERP-level stopping rules. |
| **ATM-2019** | Azzopardi, L., Thomas, P. & Moffat, A. (2019). *cwl_eval: An evaluation tool for information retrieval.* **SIGIR '19**, pp. 1321–1324. DOI: 10.1145/3331184.3331398. The canonical C/W/L framework paper. |
| **Az&Zu-2019** | Azzopardi, L. & Zuccon, G. (2019). *Building economic models of human computer interaction.* **CHI EA '19**. DOI: 10.1145/3290607.3299022. Extends the economic-model program from search to HCI broadly — the citation anchor for the Edmonds 2026 conclusion's "extend the move to other domains" call. |

---

## Claims

### K1. Microstrategies are deployed at the millisecond scale to optimize routine interactive behavior. `[G&BD-2000]`

> "The results of an experimental study suggest that alternative microstrategies can be deployed that shave milliseconds from routine interactive behavior. […] These two studies support the arguments that the microstrategies deployed can be sensitive to small features of an interface and that task analyses at the millisecond level can inform design." — *Gray & Boehm-Davis (2000), abstract, J Exp Psych: Applied 6(4), 322–335*.

**Operationalization.** Even *very small* (millisecond-magnitude)
differences in interactive-task time costs are differentially selected for
by users without explicit awareness. Strategy selection is sensitive to
sub-second interface design choices.

**Relevance to cursor-cognition coupling.** If users optimize at the
millisecond scale on basic perceptual-motor operations like "moving to and
clicking on a button," then **the cursor trajectory carries decision
information at exactly the granularity at which the user is doing the
optimization**. There is no theoretical room for the cursor to be "noise
around an internal cognitive ground truth" — the cursor is *part of* the
optimization process. This is the reason the nine M4 approach features
recover position at no AUC cost: position is a coarse downstream estimator
of what the cursor trajectory already encodes directly at the moment of
evaluation.

---

### K2. The Soft Constraints Hypothesis: perceptual-motor and cognitive resources are continuously co-allocated under temporal cost-benefit constraints at sub-1000 ms granularity. `[GSFS-2006]`

> "Soft constraints hypothesis (SCH) is a rational analysis approach that
> holds that the mixture of perceptual-motor and cognitive resources
> allocated for interactive behavior is adjusted based on temporal
> cost-benefit tradeoffs." — *Gray, Sims, Fu & Schoelles (2006), Psychological Review 113(3), 461–482, abstract*

**Temporal scale.** SCH operates "at the under-1000-ms level of analysis"
— rapid, real-time mixing of cognitive and motor resources, not long-term
strategic planning.

**Contrast with the minimum memory hypothesis (MMH).** MMH posits that
people protect cognitive/memory resources first and use perception-motor as
a substitute. SCH says the allocation is *flexible* — whichever resource
is cheaper at a given moment for a given subtask gets used, regardless of
which is "cognitively" preferable. The theory is grounded in Anderson's
rational analysis program and is implementable in ACT-R as a
reinforcement-learning policy that maximizes expected utility by minimizing
time.

**Relevance to cursor-cognition coupling on SERPs.** SCH predicts that
during phases where the cursor is *useful* to the cognitive task (e.g.,
fine-grained Evaluate-phase comparison shopping), users will tightly couple
cursor and gaze; during phases where the cursor offers no marginal benefit
(e.g., ballistic Survey-phase scanning, where the gaze is moving faster
than the cursor can usefully follow), users will decouple them. **The
phase-dependence of cursor-gaze coupling is a direct prediction of SCH**, not
an idiosyncratic empirical finding. The paper's §4.4 phase-restricted
ablation — Survey-phase cursor at AUC 0.643 (essentially position alone),
post-Survey cursor at 0.820 (matching whole-trial) — is consistent with
this prediction at the granularity of one cognitive task model (OSEC) and
one behavioral domain (SERP examination).

---

### K3. The cursor-gaze coupling literature in IR has been measuring SCH-predicted phenomena, with the bounded-rationality lineage embedded in it from the founding paper.

The IR cursor-gaze literature has, over two decades, established that
cursor and gaze are **coupled but not identical**:

- **Chen, Anderson & Sohn (CHI EA 2001)** — first observation that cursor
  position correlates with gaze during web browsing, with substantial
  variation by activity type. **The Anderson on this paper is the same
  John R. Anderson** who wrote *The Adaptive Character of Thought* (1990)
  and founded ACT-R — the architect of the rational-analysis program. The
  founding paper of the IR cursor-gaze tradition has the bounded-rationality
  lineage literally co-authored into it. *Citation:* `[chen2001mouse]`,
  CHI '01 Extended Abstracts, pp. 281–282.
- **Huang, White & Buscher (CHI 2012)** — quantified the cursor-gaze
  relationship at large scale on Bing: ~700 ms median lag from gaze to
  cursor, with cursor inactive ~59 % of the time, behavior-dependent
  alignment ranging from 233 px (idle) to 77 px (about-to-click), and
  alignment that tightens as users transition from scanning into directed
  action. *Citation:* CHI '12, pp. 1341–1350. Local copy:
  `attentional-foraging/docs/lit-notes/huang2012-gaze-cursor.md`.
- **Stone & Chapman (PACMHCI ETRA 2023)** — *Unconscious Frustration:
  Dynamically Assessing User Experience using Eye and Mouse Tracking*. Use
  combined eye + mouse tracking on a menu-navigation task to detect
  unconscious user frustration; the coordination between the two streams
  carries psychological state beyond what either modality carries alone.
  *Citation:* `[stone2023unconscious]`, DOI 10.1145/3591137.
- **AdSERP cursor-gaze coupling medians [LAB, NB22:K5–K7]** — three
  scalars (median 306 / 283 / 197 px on different population subsets),
  showing the coupling is real but partial.

**Citation hygiene note:** The first version of this document attributed
a "Stone, Hong & Tan TOCHI 2023" paper that does not exist — the Stone
& Chapman PACMHCI ETRA 2023 paper above is the real reference, and the
prior version was a confabulation caught during the 2026-04-15 review pass.

What this body of work has been measuring is **the empirical signature of
SCH in SERP examination**: the cursor and gaze couple where the task
demands tight motor-cognitive coordination, and decouple where it doesn't.
The 700 ms median lag in Huang et al. is not noise; it is the timescale at
which the cursor "catches up" to the gaze when the task switches from
ballistic survey (decoupled) to deliberative evaluation (coupled). The
Anderson co-authorship on the Chen et al. founding paper means the
theoretical lineage was *embedded from origin*, even if subsequent IR work
has not made it the central organizing frame.

**Relevance to cursor-cognition coupling on SERPs.** The IR literature has
been building empirical scaffolding for what bounded-rationality theory
predicts directly, and the lineage was on the author line of the founding
paper. The Edmonds 2026 paper closes the loop by:

1. Identifying *which phase* the coupling concentrates in (Evaluate, via
   OSEC) using a task model.
2. Measuring the cursor signal at that phase with nine task-aware features.
3. Showing the resulting feature vector matches a position-inclusive
   classical baseline at no AUC cost (M4 0.821 ≈ M3 0.820, paired
   per-fold Δ = +0.0014 ± 0.0015, M4 ≥ M3 in 40/47 folds).
4. Validating the phase locality with the §4.4 ablation: post-Survey
   cursor preserves the full signal (AUC 0.820), Survey-only cursor
   collapses to position-only (AUC 0.643 vs. M1 position-only 0.638).

The "cursor-gaze divergence is interesting" intuition that drove the
project — accumulated over two decades of applied search/recommender
work — is a 20-year industry-side observation of K2 + K3 in production
behavioral data. The AdSERP eye-tracker dataset is what made it tractable
to validate at LAB granularity.

---

### K3a. The IR-side bridge to bounded rationality has been built by Azzopardi at the strategic-interaction level.

Independent of the cursor-gaze coupling thread above, **the IR community
has its own fifteen-year-old bounded-rationality program** at the
strategic-interaction grain — what to query, when to read, when to stop,
what to count. Built primarily by Leif Azzopardi (Strathclyde) and
collaborators:

- **Azzopardi, *The Economics in Interactive Information Retrieval***,
  SIGIR '11 — foundational application of cost-benefit reasoning to
  interactive IR. *Citation:* `[azzopardi2011economics]`.
- **Azzopardi, *Modelling Interaction with Economic Models of Search***,
  SIGIR '14 — extends the 2011 framework from theory to predicted user
  behavior. *Citation:* `[azzopardi2014modelling]`.
- **Maxwell & Azzopardi, *Information Scent, Searching and Stopping***,
  ECIR '18 — applies Pirolli & Card's information-foraging stopping
  rules to SERP-level abandonment.
- **Azzopardi, Thomas & Moffat, *cwl_eval: An Evaluation Tool for
  Information Retrieval***, SIGIR '19 — the canonical C/W/L framework
  paper. Unifies utility, cost, and user-interaction models as a coherent
  substrate for ranked-list evaluation, replacing standalone metrics
  (RBP, INST, TBG, U-measure) with derivations from a single user-model
  formalism. *Citation:* `[azzopardi2019cwl]`.
- **Azzopardi & Zuccon, *Building Economic Models of Human Computer
  Interaction***, CHI EA '19 — extends the economic-model program from
  search to HCI broadly. *Citation:* `[azzopardi2019hci]`. The Edmonds
  2026 paper uses this as the citation anchor for §6's encouragement to
  apply the same task-model-informed feature-design move to other
  interactive-behavior domains (recommender dwell, conversational turn
  hesitation, session-aware reformulation).

**The relevance to cursor-cognition coupling.** Azzopardi's economic-model
program operates at the *strategic interaction* grain — Pirolli/Card-style
foraging applied to multi-action search sessions. Gray's microstrategies
and SCH operate at the *motor execution* grain — sub-1000 ms continuous
mixing of perceptual, motor, and cognitive resources during a single
interactive action. **These are the same intellectual program at different
timescales**, and bringing them together is the move the Edmonds 2026
paper makes. Azzopardi being a co-author on the paper is therefore not
incidental — his fifteen-year IR-side program is one of the two pillars
the paper rests on (the other being Gray's motor-side program). The
contribution is bringing the strategic-side and motor-side bounded-
rationality literatures into contact via OSEC + the cursor as empirical
probe.

---

### K4. Bounded rationality predicts that motor telemetry and decision telemetry are not separable measurements of the same process. `[Simon-1956, Anderson-1990, GSFS-2006]`

Simon (1956) introduced bounded rationality as the observation that humans
maximize utility under cognitive, perceptual, and time constraints, not the
unbounded "optimal" assumed by classical economics. Anderson (1990)
formalized this as **rational analysis**: cognitive systems can be
understood by asking *what optimal solution to the task environment they
implement under their resource constraints*. ACT-R is the production-rule
engine that operationalizes rational analysis.

Gray's soft constraints hypothesis is the rational-analysis treatment of
**resource allocation in real-time interactive behavior** at the sub-second
scale. The unifying claim across all three:

> Behavior at every level — from macro decision-making down to individual
> millisecond-scale motor microstrategies — is a *single co-optimized
> process* under the same utility-maximization principle. There is no
> separable "internal cognitive process" that the motor system later
> reports on, because the motor system is *itself* part of the
> optimization.

**Relevance to behavioral modeling generally.** Any modeling approach that
treats the cursor as a noisy proxy for a hidden cognitive ground truth has
the ontology backwards. The cursor and the cognition are facets of a
single process, jointly optimized at the millisecond scale, and they
**carry the decision in different places at different times** as the soft
constraints rebalance. Locating where the cursor carries the decision is
a task-model question; measuring it there is the empirical step. This is
the framing the CIKM paper adopts.

---

## Pulling these claims into the paper

These five K-claims are cited in the Edmonds 2026 CIKM paper as follows:

- **Abstract** — bounded rationality is the opening frame (K1 + K2). The
  Anderson-on-the-founding-paper observation (K3) is also surfaced briefly
  for the attribution claim.
- **§1 Introduction** — the full Simon → Anderson → Gray lineage opens the
  introduction (K1, K2, K4). The IR cursor-gaze tradition (K3) is the
  empirical instance, with explicit Anderson co-authorship of Chen et al.
  2001 surfaced. The Azzopardi cluster (K3a) is positioned as the
  fifteen-year-old IR-side bridge into bounded-rationality user modeling
  at the strategic-interaction grain. The paper's contribution is framed
  as extending the same intellectual program to the motor-execution grain.
- **§2.2 Cursor dynamics as a window into cognition** — K3 is the primary
  citation, with explicit forward reference to §2.4 for the theoretical
  anchor.
- **§2.4 Bounded rationality and continuous motor-cognitive
  co-optimization** (new section) — primary citations for K1, K2, K4.
  K3 is the bridge to §2.2. K3a is the bridge to the Azzopardi
  strategic-side IR program.
- **§6 "The principle"** (rewrite of §6 "The opportunity") — leads with
  K1 + K2 as the theoretical anchor, cites K3a (Azzopardi cluster) as the
  strategic-side IR bridge already built, and frames the paper as
  extending the same program one level deeper. K3a's Az&Zu-2019 entry
  is the citation anchor for the "extend the move to other interactive-
  behavior domains" call.

---

## Why these citations are safe for a CS/IR audience

The Gray papers are in **top-tier psychology venues** (J Exp Psych: Applied
2000 and Psych Review 2006 respectively), peer-reviewed, well-cited (the
2006 paper has 200+ citations), and have been replicated. Gray is a
long-standing ACT-R community member at RPI. The work has direct empirical
hooks (stopwatch-style task measurements, ACT-R model fits to behavior)
that translate cleanly to the kinds of evidence a CIKM reviewer values.
The references are not philosophical / theory-only.

The minimum-memory-hypothesis vs. soft-constraints comparison in
Gray et al. 2006 is itself a **rational-analysis instance** of the same
logic this paper uses — pick a competing model with a different assumption
about what the system optimizes, run the same experiments, see which
matches behavior. It is the same intellectual move at a different scale.

The **Azzopardi cluster (K3a) is even safer for an IR audience**: SIGIR is
the canonical venue for IR research, the C/W/L framework has its own
implementation toolkit (`cwl_eval`, available on GitHub at
[ireval/cwl](https://github.com/ireval/cwl)), and the framework is
presented as a unification that subsumes RBP, INST, TBG, and U-measure.
A CIKM reviewer will recognize Azzopardi's program as established IR work,
and the strategic-side / motor-side bridge framing positions the paper as
*continuing* his program rather than displacing it. Azzopardi being a
co-author on the Edmonds 2026 paper provides additional intellectual
provenance.

The **Anderson co-authorship of Chen, Anderson & Sohn 2001 (K3)** is the
cleanest possible attribution to the rational-analysis lineage from inside
the IR cursor-gaze tradition — it's literally on the author line of the
founding paper. No reviewer can challenge "the bounded-rationality lineage
has been latent in this literature since its founding" when the founding
author is the architect of the program.
