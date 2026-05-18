# The Diffusion Decision Model as the Formal Scaffold for Approach-Retreat Geometry

## Key Claims from Ratcliff & McKoon's 2008 Diffusion-Model Review

This document captures the foundational claims from the canonical
Ratcliff & McKoon (2008) review of the **diffusion decision model
(DDM)** that anchor the *formal* side of the approach-retreat
feature factorization. Where [`gray-bounded-rationality.md`](gray-bounded-rationality.md)
supplies the *cognitive-architectural* lineage (bounded rationality,
soft constraints, motor-cognitive co-optimization), this document
supplies the *psychometric mechanism*: a noisy accumulator with
three principal parameters that map one-to-one onto the three
dimensions of the AR feature set (proximity, approach rate,
monotonicity).

The intellectual chain is: **Ratcliff (1978) original DDM →
Ratcliff & McKoon (2008) review and synthesis → mouse-tracking
literature (Spivey 2005, Freeman & Ambady 2010) treating the
cursor as a continuous accumulator path → per-AOI deliberation
episode as a 2-choice DDM realization → AR feature set as
DDM-parameter readout from cursor telemetry**.

The DDM is the most empirically validated decision model in cognitive
psychology. Anchoring the AR feature set in it gives the AR program
a mathematical backbone that holds up under CS/IR review — the
features are not psychology-flavoured proxies; they are estimators of
parameters of a model whose generative process has fit RT and accuracy
distributions across thousands of empirical studies.

---

## Sources

### Primary

| ID | Citation |
|---|---|
| **R&M-2008** | Ratcliff, R. & McKoon, G. (2008). *The Diffusion Decision Model: Theory and Data for Two-Choice Decision Tasks.* **Neural Computation**, *20*(4), 873–922. DOI: [10.1162/neco.2008.12-06-420](https://doi.org/10.1162/neco.2008.12-06-420). PMCID PMC2474742. — Canonical contemporary review covering model formulation, parameter recovery, applications across lexical decision / recognition memory / signal detection / brightness discrimination, and the relationship to neural single-unit data. |
| **R-1978** | Ratcliff, R. (1978). *A theory of memory retrieval.* **Psychological Review**, *85*(2), 59–108. — Original formulation of the model as applied to recognition memory. Foundational. |

### Bridging — cursor as DDM accumulator path

| ID | Citation |
|---|---|
| **SGK-2005** | [CITE: Spivey, Grosjean & Knoblich 2005 PNAS — continuous attraction toward phonological competitors] — first demonstration that real-time cursor trajectories are continuous expressions of decision-state evolution. Phonological competitors pull cursor paths in proportion to their activation. The cursor is not a delayed report of a discrete cognitive decision; it is the accumulator path itself. |
| **F&A-2010** | [CITE: Freeman & Ambady 2010 — MouseTracker software for real-time mental processing] — methods paper that operationalized the cursor-as-accumulator framing for psychology labs. Used in hundreds of subsequent studies. |
| **HSF-2015** | [CITE: Hehman, Stolier & Freeman 2015 — review of mouse-tracking analytic techniques] — review of the mouse-tracking-as-decision-process literature, including the DDM-compatibility argument. |

### Multi-alternative extensions (relevant for SERPs)

| ID | Citation |
|---|---|
| **B&T-1993** | [CITE: Busemeyer & Townsend 1993 — decision field theory] — extension of diffusion models to dynamic decision-making in uncertain environments; foundational for multi-alternative variants. |
| **DDM-N** | [CITE: multi-alternative diffusion-model variants Roe Busemeyer Townsend 2001 or similar] — N-alternative extensions that handle the SERP case where multiple result AOIs compete for commitment within a single search trial. |

> **Citation hygiene note.** Only **R&M-2008** and **R-1978** are
> fully resolved bibliographic entries above. The bridging and
> N-alternative citations are placeholders pending the standard
> two-pass citation discipline (see CLAUDE.md). Do not propagate
> these placeholders into paper prose without first verifying the
> exact citations against the source venues.

---

## Claims

### K1. The DDM models a two-choice decision as a noisy continuous accumulator that drifts between two response boundaries. `[R&M-2008, R-1978]`

> "The diffusion model assumes that evidence is accumulated over time
> from a starting point z toward one of two boundaries representing
> the two response alternatives. The mean rate of accumulation is the
> drift rate v; the boundary separation a determines how much evidence
> is needed before a decision; within-trial variability in evidence
> accumulation produces variable response times and occasional errors
> even when drift rate favours the correct response." — *Ratcliff & McKoon (2008), §2, paraphrased*.

**The three principal model parameters:**

| Symbol | Name | Cognitive meaning |
|---|---|---|
| **v** | drift rate | average rate of evidence accumulation toward the preferred boundary; indexes signal quality and stimulus discriminability |
| **a** | boundary separation | how much evidence is required to commit; indexes speed-accuracy trade-off and caution |
| **s** | within-trial noise | random walk variance; indexes the inherent stochasticity of evidence sampling |

Plus auxiliary parameters: starting-point z (bias), non-decision time
Ter (sensory encoding + motor execution outside the deliberation),
between-trial variability in v / z / Ter.

**Relevance to AR.** Every cursor-derived AR feature is an estimator
of one of these three principal parameters, evaluated on the
per-result deliberation episode. The mapping is direct, not analogical
— see K3.

---

### K2. Cursor trajectories are continuous-time expressions of the accumulator process, not delayed reports of discrete decisions. `[SGK-2005, F&A-2010, HSF-2015]`

The mouse-tracking literature has empirically established that during
binary-choice tasks, cursor trajectories curve toward competing
alternatives in proportion to the competitor's activation — and the
curvature unfolds continuously across the decision interval, not in
a single discrete commit. The cursor is the accumulator path made
visible.

**Operationalization.** The DDM's evidence-accumulation process
`E(t)`, normally treated as an unobservable latent variable, has a
direct cursor analog `d(t)` (signed distance from cursor to AOI
centre) under the per-AOI deliberation framing. The cursor is
*continuously sampled* from the same accumulator that produces the
binary commit-or-leave outcome at the end.

**Relevance to AR.** The library extracts features from `d(t)`
treating it as an estimator of the latent accumulator. This grounds
the feature semantics: they are not hand-picked engineering proxies
— they are read-outs of a generative-model state variable that
cognitive psychology has spent fifty years calibrating.

---

### K3. The seven AR features partition onto the three DDM parameters along the derivative orders of `d(t)`. `[R&M-2008]`

| AR dimension | Features | DDM parameter | Derivative order of `d(t)` |
|---|---|---|---|
| **Commitment** (proximity) | `min_dist`, `mean_dist`, `dwell_in_proximity_ms` | boundary separation `a` (and dwell ≈ decision time) | zeroth |
| **Decisiveness** (approach rate) | `mean_approach_velocity`, `max_approach_velocity` | drift rate `v` | first, magnitude |
| **Vacillation** (monotonicity) | `direction_changes`, `frac_decreasing` | within-trial noise `s` (and competitor pull from N-alternative variants) | first, sign |

**The argument.** Given `d(t)` as the cursor accumulator path:

1. **Boundary proximity.** `min_dist` is the closest the accumulator
   came to the commit boundary; `mean_dist` is the central tendency
   of the accumulator over the episode; `dwell_in_proximity_ms` is
   the time the accumulator spent inside a fixed neighbourhood of
   the boundary. All three are estimators of how close the
   deliberation came to crossing `a`.

2. **Drift rate.** `mean_approach_velocity` is the mean rate of
   accumulator descent during approach phases (i.e., `−E[dE/dt | dE/dt < 0]`
   in DDM notation, where the sign convention is flipped to "descent
   toward boundary"). `max_approach_velocity` is the peak instantaneous
   accumulation rate — sensitive to high-drift moments when the
   evidence stream surges in favour of commit.

3. **Within-trial noise.** A pure DDM accumulator under high drift
   would be near-monotonic (frac_decreasing near 1, few sign-flips).
   `direction_changes` counts the sign-flips in `d′(t)`;
   `frac_decreasing` is the share of the episode the accumulator
   was descending. Both indirectly estimate the noise-to-drift
   ratio: high noise relative to drift produces many reversals and
   low monotonicity, low noise produces clean monotonic descent.

**Relevance to AR.** This is the load-bearing claim the AR program
rests on. The feature set is *not* a bag-of-mousemove-statistics
chosen for predictive performance — it is a structured estimator of
the three DDM parameters, where the structure comes from the model
formulation and not from feature search.

---

### K4. Per-AOI deliberation episodes are realizations of a 2-choice DDM embedded in an N-alternative search context. `[R&M-2008, B&T-1993]`

A SERP trial is not, formally, a 2-choice task — there are 10+
ranked results plus skip/leave. But each *per-result deliberation
episode* is approximately a 2-choice DDM: commit-to-this-AOI vs
leave-this-AOI-for-the-next. The multi-alternative aspect lives one
level up, at the cross-AOI cascade of episodes.

**Why this matters for AR.** The library treats each per-AOI episode
as an independent 2-choice instance. The seven features summarize one
DDM realization per (trial × AOI). Cross-AOI competition — *which*
AOI gets the commit when several are weakly attractive — is encoded
in the cascade of episodes within a trial, not within a single
episode. This justifies the library's per-AOI partition: each
episode is a well-defined DDM sample, and the cross-AOI dynamics
fall out as aggregate statistics over episodes.

**Relevance to AR.** Decision Field Theory (Busemeyer & Townsend
1993) and the N-alternative DDM extensions provide the formal
treatment of the cross-AOI competition that produces direction
changes and partial approaches — the cursor is being pulled by
multiple competitors simultaneously, and the within-episode
oscillations indexed by `direction_changes` / `frac_decreasing`
are signatures of that competition.

---

### K5. The DDM-AR correspondence is empirically defensible — same parameter recovery argument the DDM uses, applied to a cursor data type DDM was not originally designed for.

The DDM has been validated against RT and accuracy distributions in
thousands of studies across lexical decision, recognition memory,
signal detection, brightness/motion discrimination, value-based
choice, and (in extensions) sequential sampling tasks. Parameter
recovery is well-characterized: drift rate scales with stimulus
discriminability, boundary separation with experimentally-induced
caution, noise with task structure.

**The AR claim is the parallel.** Cursor-extracted estimators of these
parameters should:

- Track stimulus quality: high-relevance results should show higher
  drift rate (faster `v_max`, `v_mean`) and shorter dwell.
- Track task caution: under high-uncertainty queries the boundary
  separation analog (mean_dist, min_dist) should be larger and dwell
  longer.
- Track noise/competition: ambiguous SERP positions (e.g.,
  contiguous similar-relevance results) should produce more
  direction changes and lower frac_decreasing.

The CIKM paper does not formally fit a DDM (a proper DDM fit would
require multi-trial RT distributions per condition); instead it
shows that **the cursor-derived parameter estimators predict click
outcome at AUC 0.847 LOSO**, with the M3 ≈ M4 result establishing
that the AR feature set absorbs the per-rank position proxy. That
is the empirical defence: the structured DDM-parameter estimators
recover the decision-relevant signal that classical rank-level
models had only been encoding indirectly.

---

## Pulling these claims into the paper

The Edmonds 2026 CIKM submission cites this lineage as follows:

- **§3.4 "The seven approach features (M4 cursor probe)"** — the
  paragraph immediately after the feature table introduces the
  three-dimensional factorization and closes with the DDM
  correspondence as a one-sentence citation pointer: *"The
  corresponding drift-diffusion factorization of choice processes
  [@ratcliff2008diffusion] groups these three dimensions as
  boundary proximity, drift rate, and noise."* This is the only
  in-paper DDM reference for the IR submission — the framing is
  deliberately compressed to avoid pulling the paper into a
  cognitive-modeling defence.

- **Supplemental § (or the CHI 2027 task-model paper) — full
  derivation** — K3's parameter-to-feature mapping table belongs in
  a supplemental section or in the broader CHI 2027 task-model
  paper, where the cognitive-modeling lineage is the main
  contribution rather than an anchoring citation.

- **AR library README** — the K3 mapping (three dimensions × DDM
  parameters) can appear as a short section under "Theoretical
  Grounding" to make the library's design philosophy explicit for
  downstream users.

---

## Why this citation is safe for a CS/IR audience

- **Venue & reach.** Ratcliff & McKoon 2008 is in *Neural
  Computation*, a high-prestige interdisciplinary venue with strong
  CS/ML overlap. Over 4,000 Google Scholar citations as of writing.
  It is not a niche psychology reference.
- **Mathematical content.** The paper is heavy with model equations,
  parameter recovery simulations, and quantitative fits — exactly the
  kind of evidence a CS reviewer is comfortable with. It reads as
  applied probability theory, not as theory-only psychology.
- **Connection to ML.** Drift-diffusion models have direct connections
  to sequential analysis (Wald 1947), to optimal stopping theory, and
  to reinforcement-learning value accumulators. The DDM is recognized
  by ML reviewers as a principled probabilistic decision model, not as
  cognitive-science speculation.
- **One sentence in the main paper.** Per the strategic framing in
  the CIKM submission, the DDM citation is a one-sentence anchor in
  §3.4 — a reviewer who wants to follow it up can; one who does not
  can read past it without the paper becoming "about" cognitive
  modeling.

---

## Companion documents

- [`gray-bounded-rationality.md`](gray-bounded-rationality.md) — the
  cognitive-architectural lineage (Simon → Anderson → Gray) anchoring
  *why* the cursor carries decision information at sub-second
  timescales. The DDM is the formal mechanism; bounded rationality
  is the architectural justification for why the mechanism is
  realized in motor telemetry. The two documents are complementary,
  not redundant.
- [`regressions-lit-review.md`](regressions-lit-review.md) — the
  regression / re-examination literature that motivates the
  deferred-vs-evaluated-rejected split downstream of the AR
  primitive.
