# Where approach-retreat sits in the literature

The contribution of `approach-retreat` is the *unit of feature aggregation*: the per-result-AOI deliberation episode. The methods paper (submitted) makes that explicit; this doc is the map readers reach for when they want to verify a positioning claim against the cited literatures.

## The four lanes

The literatures that have something to say about cursor / gaze on SERPs do not fully cite each other. Approach-retreat sits between them. The full anatomy of where each lane stops is in `references/regressions-lit-review.md`. The summary, by *unit of feature aggregation*:

| Lane                        | Unit of aggregation              | Representative work | Where the lane stops |
|-----------------------------|----------------------------------|---------------------|----------------------|
| **Click models**            | per-rank Markov chain            | Craswell et al. WSDM '08; Chapelle & Zhang WWW '09; Dupret & Piwowarski SIGIR '08 | Non-clicks collapsed to a single class; rank as a proxy for examination. |
| **THUIR direction primitives** | per-rank with eye-tracking-grounded direction features | Wang et al. SIGIR '15 (PSCM); Zhang et al. WWW '21 (CBCM) | Non-sequential examination as click-likelihood feature; no within-episode geometry. |
| **Cursor-feature classifiers** | per-session bag-of-statistics    | Arapakis & Leiva 2020; Brückner et al. SIGIR '21 (`bruckner-2021-systematic.md`) | Hundreds of `mousemove` features over the whole session — no per-result commitment. |
| **Sequence models**         | per-trajectory-token             | Brückner et al. CIKM '20 (`bruckner-2020-abandonment`) | End-to-end mappings from `(x, y, t)` tuples; no explicit direction or revisit construct. |

The closest per-result-AOI precedent is **Liu et al. CIKM '14** (skim/read two-stage model) — per-result summary statistics (dwell, hover, presence) but no internal episode geometry. Approach-retreat sits in that gap: the per-result-AOI grain *plus* internal trajectory descriptors (`min_dist`, retreat arc, frac-decreasing, direction-changes).

## Adjacent traditions the paper draws from

### Cursor as cognitive instrument

- **Chen, Anderson & Sohn CHI EA '01** — first establishment of cursor-gaze coupling on the web.
- **Huang, White & Buscher CHI '12** (`huang-white-buscher-2012.md`) — the canonical at-scale Bing measurement: ~700 ms cursor-gaze lag, alignment from 233 px (cursor inactive) to 77 px (action-cursor about to click).
- **Stone & Chapman PACMHCI ETRA '23** (`stone-chapman-2023-unconscious.md`) — gaze-mouse coupling residual as a *dynamic* UX-friction signal; webcam-cohort replication validates the construct without lab-grade instrumentation.
- **Boi et al. ETRA '16** (`boi2016attention` in bib) — saliency-of-cursor follow-up to Huang.

What this lineage establishes: cursor and gaze couple where the task demands fine-grained motor-cognitive coordination, and decouple where it does not. Approach-retreat extends the construct from a *where* measurement (scalar attention estimator) to a *what-it-does-next* measurement (trajectory dynamics) without changing the underlying coupling claim.

### Bounded-rationality lineage

- **Simon `simon1956rational`** — the original bounded-rationality formulation.
- **Anderson 1990 — rational-analysis program** (entry pending in bib).
- **Gray 2000 — *Milliseconds Matter*** (entry pending).
- **Gray, Sims, Fu & Schoelles 2006 — soft constraints hypothesis** (`gray-bounded-rationality.md`).
- **Azzopardi et al.** — IR-side bounded-rationality at the strategic-interaction grain (CWL, economic models). Citations live in `azzopardi2016two` and the `azzopardi-thomas-craswell-2018-sigir` entry.

The methods paper extends Azzopardi's strategic-interaction grain *one level deeper* to the motor-execution grain where Gray's microstrategies operate. Approach-retreat geometry is the kinematic shadow of the marginal-rate calculation IFT × microeconomics requires.

### Behavioral relevance signals for IR training

- **Joachims et al. SIGIR '05** (`joachims2005clickthrough` in bib) — skip-above rule. Behavioral inference of "examined and rejected" from rank position. The construct approach-retreat refines into a four-class taxonomy.
- **Dumais, Buscher & Cutrell IIiX '10** (`dumais-2010-individual.md`) — participant-level taxonomy via gaze-pattern clustering. The 2D structure approach-retreat operationalizes is a per-(trial, position) version of this.
- **Hard-negatives** (`hard-negatives-in-ltr.md`) — DPR / ANCE relies primarily on synthetic negatives; behavioral mining is niche.

## Three claims that depend on this positioning

Each is in the paper's §2 prose and verifiable from the lit-notes:

1. **"The closest per-result-AOI precedent is Liu et al. [CIKM '14]"** — `liu2014skimming` in bib; lit-note pending.
2. **"Cursor and gaze couple where the task demands fine-grained motor-cognitive coordination"** — `huang-white-buscher-2012.md` carries the empirical numbers.
3. **"Joachims's skip-above rule infers 'examined and rejected' from rank position, not observable behavior"** — `joachims2005clickthrough` in bib; lit-note pending.

Lit-notes are in `references/` for every citation in the paper's §2:
- `bruckner-2021-systematic.md` — anchors the 0.653 ACD baseline cited in §4.5.
- `joachims-2005-clickthrough.md` — anchors the four-class taxonomy's skip-above framing.
- `liu-2014-skimming.md` — anchors "closest per-result-AOI precedent."
- `stone-chapman-2023-unconscious.md` — gaze-mouse coupling residual as a dynamic UX signal.
- `dumais-2010-individual.md` — gaze-pattern participant-level taxonomy precedent.

## What this repo's empirical work substantiates against the lineage

| Claim in §4 / §5 | What in this repo backs it up |
|------------------------|------------------------------|
| Approach-retreat episode geometry exists in WILD telemetry | `analysis/attcur-validation/` (954 ACD sessions, leakage-screened AUC 0.765 vs Brückner 0.653) |
| Episode geometry generalizes beyond search to any ranked-list UI | `findings.md` + the `viewport-bands` calibration (`docs/validation/`) |
| The four-class taxonomy is `[LAB]`-only by construction (gaze-derived) | `CLAUDE.md` "What fits where" + the upstream `attentional-foraging` Key Claims |
| `retreat_dist` carries WILD signal even though the LAB analog is leakage-prone | `analysis/attcur-validation/results.txt` (ρ = −0.065, p ≈ 0.04, joint coef −0.723 → skip) |
