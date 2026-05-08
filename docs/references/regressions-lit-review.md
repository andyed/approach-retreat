# Regressions — focused lit review for approach-retreat

Compiled 2026-04-30 during pre-meeting prep for Jacek Gwizdka / RIPA2 team.

**Scope.** What the literature has and has not done with *return movements* (scrolls back, regression saccades, cursor retreats, revisits) across IR, eye-tracking, reading research, and HCI. Frames where `approach-retreat`'s contribution sits.

**Companion doc.** A broader scroll-regressions review lives in `attentional-foraging/docs/lit-notes/lit-review-scroll-regressions.md`. This doc is approach-retreat-specific: cursor-episode geometry, AOI-level retreats, and where pre-committed motor execution differs from iterative re-examination.

---

## The four lanes of prior work on return movements

There are four distinct literatures that have something to say about regressions, and they don't fully cite each other. Approach-retreat sits between them.

### Lane 1 — IR click models with non-sequential examination

The IR community has been modeling non-sequential SERP examination at click-model granularity for ten years. Direction is treated as a feature in the click likelihood, not as a cognitive task state.

#### Wang, Liu, Wang, Zhou, Nie & Ma — *Incorporating Non-sequential Behavior into Click Models* (SIGIR '15)

The **Partially Sequential Click Model (PSCM)**. THUIR / Yiqun Liu group, Tsinghua. Eye-tracking-grounded. Two assumptions: (1) examination between adjacent clicks is locally unidirectional but users may skip results and examine at distance; (2) direction is consistent with click direction. Code: [github.com/THUIR/PSCMModel](https://github.com/THUIR/PSCMModel). DOI: [10.1145/2766462.2767712](https://doi.org/10.1145/2766462.2767712).

**Why this matters for approach-retreat.** PSCM models exactly the temporal window approach-retreat operates on — between adjacent clicks. The "locally unidirectional with skips" framing is the click-model version of what approach-retreat measures as approach + dwell + retreat episodes. PSCM treats this as a click-likelihood feature; approach-retreat treats it as cursor-episode geometry with internal trajectory descriptors.

**The gap.** PSCM operates on rank position. Approach-retreat operates on AOI episodes. PSCM has no construct for *retreat geometry* (arc length, lateral displacement, post-closest-approach drift) — these are within-episode shape descriptors that the click-model unit (rank) cannot represent.

#### Zhang, Liu, Mao, Zhang & Ma — *Comparison-Based Click Model* (WWW '21)

**CBCM.** Same THUIR group, six years downstream. Adds explicit *revisit* and *compare* primitives. Models comparison as alternating attention between candidates.

**Why this matters for approach-retreat.** CBCM's revisit primitive is the closest IR-side construct to what approach-retreat measures as a deferred-class episode (cursor returns to an already-evaluated AOI). CBCM treats it as a click-likelihood feature; approach-retreat captures the trajectory between the first leave and the second approach.

**The gap.** Same as PSCM — click-model granularity, no within-episode geometry. CBCM's compare primitive is close to the four-class taxonomy's *deferred* class but stops at the click-likelihood level.

#### Borisov, Wardenaar, Markov & de Rijke — *Click Sequence Model* (SIGIR '18)

Neural seq2seq absorbing non-sequential patterns end-to-end. Direction is implicit, learned from data. Sequence-model successor to PSCM at the click level.

**Why this matters.** Bag-of-features-over-sequence approach. Same gap as the cursor-feature classifier work in §2.1 of the CIKM paper: no per-result-AOI commitment, no explicit direction or revisit construct, no geometric descriptors.

---

### Lane 2 — Eye-tracking on SERPs with nonlinear scanpaths

This lane has been describing return behavior since the mid-2000s without naming it as task-relevant.

#### Lorigo, Haridasan, Brynjarsdóttir et al. — *Eye Tracking and Online Search* (JASIST 2008)

The canonical *~2/3 of scanpaths are non-sequential* paper. ~66% nonlinear on Yahoo SERPs. Challenges cascade. Documents the prevalence of return behavior empirically but doesn't decompose direction kinematically.

**For approach-retreat.** This is the standing replication baseline. Approach-retreat's 69% scroll-regression rate on AdSERP (mouse scroll, Google-scrape, 18 years later) replicates Lorigo at near-identical magnitude. The cross-decade replication is the credibility move.

#### Granka, Joachims & Gay — *Eyetracking Analysis of User Behavior in WWW Search* (SIGIR '04)

Earlier, less formalized — reports a *rapid scan followed by re-examination* pattern. Names the phenomenon at scanpath level, doesn't characterize kinematics.

#### Cutrell & Guan — *What Are You Looking For?* (CHI '07); Buscher, Dumais & Cutrell — *Good, Bad, and Random* (SIGIR '10)

Documents distinct examination patterns by snippet length and ad quality. Implicit phase structure, no formalization of return behavior as a phase-mode boundary.

**Aggregate gap.** This lane has the empirical pattern (returns happen, often, on most trials) but treats it as scanpath statistics rather than task-relevant. Approach-retreat (and OSEC) reframes returns as a separable cognitive state with motor signatures.

---

### Lane 3 — Reading research regressions

This is a deeply formalized literature on within-text saccadic regressions, at a different granularity than approach-retreat operates on.

#### Rayner — *Eye Movements in Reading and Information Processing* (Psych. Bull. 1998)

Canonical review. Establishes that 10–15% of fixations during text reading are saccadic regressions used to recover comprehension. Process models like E-Z Reader formalize their dynamics.

**For approach-retreat.** Reading-research regressions are *within-word-sequence saccadic*. Approach-retreat's regressions are *within-trial scroll/AOI* movements. The constructs are related (both are "going back to recheck") but not identical. Approach-retreat's contribution is the SERP-evaluation analog of reading regressions, at AOI granularity.

The vocabulary import goes the other way too — Rayner et al.'s framework treats regressions as comprehension recovery; approach-retreat's data suggest SERP-level regressions are *commitment-driven re-examination* of an already-evaluated candidate, not comprehension-driven re-reading. Different mechanism, related vocabulary.

#### Reichle et al. — *Toward a Model of Eye Movement Control in Reading: E-Z Reader* (Psych. Rev. 1998)

Process model with explicit regression dynamics. Word-level granularity. Cited by `references.bib` already (`reichle1998ezreader`).

---

### Lane 4 — Cursor-trajectory and gaze-cursor coupling literature

The lane approach-retreat extends most directly. Most of these are already cited in `docs/references/`.

#### Huang, White & Buscher — *User See, User Point* (CHI '12)

Cursor-gaze coupling at scale on Bing. ~700 ms median lag, behavior-dependent alignment from 233 px to 77 px. Does not decompose by direction. This is the gap approach-retreat fills.

#### Arapakis & Leiva — *Predicting User Engagement* (SIGIR '16); *AdSight* (Villaizán-Vallelado et al. SIGIR '25)

Feature-bag and transformer approaches to cursor → engagement / fixation prediction. Session-level or token-level, not per-result-AOI episode. No direction decomposition.

#### Brückner, Arapakis & Leiva — *Mouse Movement Length for Decision Making* (SIGIR '21); *Query Abandonment Prediction* (CIKM '20)

Mouse-trajectory features for decision-relevance prediction. Includes some directional components (e.g., direction changes, frac decreasing) but not a direction-decomposed motor signature.

**Aggregate gap.** This lane measures cursor-gaze coupling and cursor decision-relevance, but treats trajectories as feature bags. Approach-retreat commits to per-result-AOI episodes with internal geometric descriptors and decomposes by direction (forward approach vs regressive return).

---

## What approach-retreat adds

1. **Per-AOI episode unit.** Not per-rank (PSCM/CBCM), not per-session (Arapakis/Leiva feature classifiers), not per-trajectory-token (Brückner sequence models), not per-word (Rayner). The episode against a specific result AOI is the unit.

2. **Internal episode geometry.** Approach velocity, dwell, retreat arc length, lateral displacement, post-closest-approach drift, direction changes. The within-episode shape descriptors that PSCM/CBCM cannot represent at click-model granularity and that feature-bag classifiers don't aggregate at AOI level.

3. **Direction decomposition with motor signature separability.** Approach-retreat's *deferred* class (cursor returns to AOI) vs *evaluated-rejected* class (cursor leaves and never returns) carries a direction signal at AOI granularity. The OSEC paper's §5.7 decomposes the same direction axis at fixation-level cursor-gaze coupling (37/46 participants, regressive tighter, Wilcoxon p = 4.8 × 10⁻⁵). Two granularities, same direction story.

4. **Ballistic kinematic profile of return movements.** OSEC §3.5 / `findings.md` §8: backward scrolling is ballistic (ρ = 0.867 between distance-from-target and velocity), 87% of regression targets at positions 0–4. Scroll speed explains 58% of the variance in apparent position-effects between forward-only and all-inclusive dwell ratios. Pre-committed motor execution, not iterative re-scanning. Reading research has nothing analogous (regressions in reading are short-distance, not ballistic).

5. **The retreat-geometry-as-readout reframe.** Per the resteer log in attentional-foraging, the initial epistemic-action hypothesis (cursor retreat externalizes commitment) was killed by the data and replaced with a measurement-framing: retreat geometry *reads out* cognitive state (curved + close = "deliberating, will return"; straight + far = "decided, moving on"). This is a within-class continuous signal that no other lane captures.

---

## What's still open

- **Compare PSCM/CBCM parameter estimates against approach-retreat episode geometry.** Are the with-click-direction tendencies in PSCM consistent with the 87% regression-target concentration at positions 0–4? Same phenomenon, two units?
- Run PSCM/CBCM on AdSERP. No public re-analysis exists. The same eye-tracking-grounded framing as the dataset; testing whether THUIR's models can recover the four-class taxonomy from click data alone is an open empirical question.
- Test approach-retreat on RecGaze (carousel). De León Martínez et al. SIGIR '25 documents F-pattern / golden-triangle browsing in a horizontal carousel. The "swipe back" in carousels is the horizontal analog of vertical scroll regressions. Approach-retreat's per-AOI episode unit transfers cleanly; the four-class taxonomy should test out-of-the-box.
- Reading-style regressions vs commitment-style regressions. Approach-retreat's data say SERP regressions are commitment-driven re-examination. Does that hold for informational queries (longer reading, more comprehension load)? Or do informational queries produce a mixture of comprehension regressions (Rayner-style) and commitment regressions?

---

## Defensive script if asked "have you read PSCM?"

> *"Yes. Wang and Liu's group decomposed forward and non-sequential examination at click-model granularity with eye-tracking grounding. PSCM (2015) and CBCM (2021) treat direction as a feature in the click likelihood. Approach-retreat works at the AOI episode unit with internal trajectory geometry — arc length, retreat distance, post-closest-approach drift — that the click-model unit cannot represent. The two literatures are complementary: PSCM/CBCM tell you the user moved non-sequentially between rank R and rank R'; approach-retreat tells you the geometric shape of the cursor trajectory between leave-AOI and return-to-AOI, and what that shape predicts about whether the user will commit to that result."*

---

## Bib status

`wang2015pscm`, `zhang2021cbcm`, `borisov2018clicksequence` were added to `attentional-foraging/references.bib` on 2026-04-30. The approach-retreat repo's own `docs/references/references.bib` should be synced — check whether any of the click-model entries need to be mirrored locally for this repo's papers/docs.
