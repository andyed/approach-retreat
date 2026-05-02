# Forward / Regressive classification — the HWM rule

Canonical methodology reference for how AdSERP fixations and episodes are partitioned into forward-pass vs regressive movements. Consolidates documentation that was previously scattered across `data_loader.py`, `episode_classifier.py`, `docs/plans/forward-regressive-split.md` (stale status), and §5.7 of `task-model-paper.md`.

**Status.** Implemented. The plan doc at `docs/plans/forward-regressive-split.md` predates the implementation and still has its `Status: planned, not started` header — that header is wrong; the work shipped. Treat this doc as canonical.

---

## The rule, in one line

> **A fixation is *forward* iff its scroll offset is within `hwm_tolerance` pixels of the running scroll high-water-mark sampled at all prior fixations. Otherwise it is *regressive*.**

`hwm_tolerance` defaults to **50 px**. The HWM is monotonically nondecreasing across the trial — once you've scrolled to position Y, the HWM stays at Y until you scroll past it.

---

## Why this rule

We needed a definition of *direction* that:

1. **Operates on what production telemetry can see.** Scroll offset is observable from web telemetry without an eye tracker. First-visit-history and saccadic-direction need finer instrumentation.
2. **Freezes at the decision moment.** A regressive re-examination should not be relabeled "forward" later if the user eventually scrolls past the HWM. Direction is set at the moment the user enters the result, not at the moment they leave.
3. **Has a single tunable parameter** (`hwm_tolerance`) that captures the gap between strict-equality "at HWM" and slightly-back-from-HWM-due-to-scroll-snap.
4. **Lifts cleanly from per-fixation to per-episode.** The same rule applies at both granularities. The episode classifier wraps the per-fixation rule and is parity-verified against it (4,036/4,036 fixations agree).

Three definitions were considered (from the plan doc):

| Level | Definition | Verdict |
|---|---|---|
| A. Trial-level | Use `regressive_scroller` tag wholesale | Rejected. 63% of trials are tagged; most episodes inside them are forward reads. Destroys signal. |
| **B. Episode-level** | At entry time, compare scroll offset to trial HWM: forward iff `entry_scroll >= hwm_at_entry - 50px`. | **Adopted.** Matches retreat granularity. Reuses HWM machinery. Handles mixed trials. |
| C. Position-level (per-fixation) | Per-fixation `is_forward` via HWM | Adopted as the underlying primitive. Episode classifier is the wrapper. |

Definition B is the canonical episode-level form; the per-fixation rule (C) is the underlying primitive both share. The fixation-level classifier in `data_loader.py:classify_fixations` and the episode-level wrapper in `episode_classifier.py:classify_episode` use the same threshold and produce identical labels at episode granularity.

---

## Where this lives in code

| File | Function | What it does |
|---|---|---|
| `notebooks-v2/data_loader.py` | `classify_fixations(trial, hwm_tolerance=50)` | Per-fixation classification. Returns list of dicts with `is_forward` flag, scroll offset, page-y, and result position. |
| `notebooks-v2/episode_classifier.py` | `build_hwm_timeline(trial)` | Builds the running-HWM timeline for a trial, cached by `trial_id`. |
| `notebooks-v2/episode_classifier.py` | `classify_episode(entry_t, trial, tol_px=50.0)` | Per-episode classification at a given entry time. Returns direction, entry_scroll, hwm_at_entry, hwm_deficit. |
| `notebooks-v2/episode_classifier.py` | `classify_trial_episodes(trial, episodes, tol_px=50.0)` | Vectorized per-trial wrapper. |

Episodes are passed in, not re-detected — every notebook defines them differently (NB17 scroll retreats, NB20 approach features, NB24 arc extraction). The classifier only answers the direction question.

The fixation-level rule is the canonical implementation:

```python
# data_loader.py:classify_fixations (excerpt)
hwm = 0.0
for fix in fixations:
    so = scroll_offset_at(fix['t'])  # last-known-value lookup
    if so > hwm:
        hwm = so
    is_forward = (so >= hwm - hwm_tolerance)
```

The episode classifier mirrors this; the parity test at 4,036/4,036 fixations confirms equivalence.

---

## Parameters

### `hwm_tolerance` (default 50 px)

Width of the band below the HWM that still counts as forward. A user at the leading edge of their exploration is forward; a user 50 px back from that edge is also forward (accounting for scroll-snap and small backscrolls); a user >50 px back is regressive.

The 50 px default is approximately the typical scroll-snap distance and roughly 1/3 the height of a typical SERP result block (~150–200 px). The 50 px choice was deliberate: small enough to not absorb genuine regressions, large enough to not fragment forward scanning into spurious regressions during natural scroll movement.

### `tol_px` (episode-level, default 50.0)

Same parameter under a different name — the episode-level wrapper uses `tol_px` to match function-signature conventions in the wrapper, but the value should remain identical to `hwm_tolerance` to preserve fixation/episode parity.

---

## Sensitivity / robustness — what's been tested

### Tolerance sweep ✓

Tested at `hwm_tolerance` ∈ {25, 50, 100} px. The boundary is **stable across this range** — the 50 px default sits on a plateau, not a cliff. The phase boundary detected by the classifier does not flip between these tolerances.

### Fixation/episode parity ✓

`classify_fixations` (per-fixation) vs `classify_episode` (per-episode) agree at **4,036 / 4,036 fixations** when the episode classifier is lifted to fixation granularity. No edge cases where the episode classifier disagrees with the underlying primitive.

---

## Sensitivity / robustness — NOT yet tested

### HWM-based vs first-visit-based forward definition

These can disagree on a small fraction of fixations. Imagine a fixation at position 4 *after* the user has scrolled to position 6 and back to position 4: the HWM rule labels regressive (current scroll < HWM); a first-visit rule would label forward if this is the first time position 4 has been fixated. The disagreement set is small (most regression visits are *re*-visits, not first-visits with intervening deeper scroll), but it's non-zero and untested.

If first-visit is the conceptual definition we actually intend (e.g., for "is this a re-examination" semantics), we should run the comparison and report disagreement rate. Likely a one-day analysis.

### Episode boundary definition

What counts as one "first-pass visit"? If a user fixates rank 3, glances at rank 4, returns to rank 3 (still at HWM, so still forward by the rule) — is that one visit or two? The episode classifier merges by minor-saccade threshold (100 px); visit-counting in some notebooks merges differently. This affects the per-visit dwell denominator and could shift dwell-by-rank correlations.

### Intra-viewport saccadic regressions

The classifier operates on *scroll* offset. A user can fixate forward (scroll-wise) while making backward saccades within the visible viewport. Within-viewport eye regressions at the HWM are labeled "forward" by this rule. If the question is "is the user re-evaluating something they just looked at," intra-viewport eye regressions matter, and the classifier misses them. Probably small in magnitude but theoretically distinct from scroll-based regression.

### Trial filtering

Some notebooks (e.g., the panel-2 dwell-by-rank chart that shows ranks 0–8 only) filter by trial length or completion. If the filter is "trials where the user reached at least position N," the high-rank subsample is self-selected toward thorough searchers and per-visit dwell at high ranks reflects that selection.

---

## Open robustness questions worth running before paper freeze

1. **HWM vs first-visit disagreement rate.** Compute both labelings on the full corpus; report the disagreement set as a percentage and audit any large clusters.
2. **Tolerance sweep on the per-visit dwell shape.** The {25, 50, 100} stability check was on the proportion of fixations classified forward vs regressive. The same sweep should be re-run on the *per-visit dwell* shape (the panel-2 ρ ≈ −0.95 finding) to confirm the magnitude doesn't depend on the threshold.
3. **Saccadic-regression overlay.** Detect within-viewport eye regressions and compute their overlap with scroll-regressions. Report what fraction of total "regression" effort is captured by the scroll-based rule alone.
4. **Episode-merging sensitivity.** Re-run panel-2 dwell-by-rank with episode-merging at 50 px instead of 100 px. If ρ stays in [-0.99, -0.85], the result is robust. If it moves materially, we have a sensitivity story rather than a single point estimate.

---

## What's robust regardless of tweaking

- **Forward-visit count by rank (the F-shape, ρ = −1.00).** Definition-invariant — the count of trials reaching a position is mostly the same regardless of how you classify the fixation.
- **Regression target concentration at top ranks (87% to positions 0–4).** Robust because it's a target-concentration finding, not a classifier-boundary finding. Even alternative definitions of "regression entry" preserve targeting concentration.
- **The qualitative relationship F-shape >> per-visit dwell shape.** The F-shape is steeper than per-visit dwell across all tested classifier variants. Whether per-visit dwell ρ is −0.95 or −0.80 doesn't change the take-home: *count drives the position effect, per-visit effort is much flatter.*

---

## Limitations to disclose in papers

- **Scroll-based, not gaze-direction-based.** The classifier sees what the user scrolled to, not where their eyes went within a viewport. Saccadic regressions inside the visible window are invisible to it.
- **Frozen at entry, not adaptive.** A long-dwell episode that begins forward but ends after a fast scroll-up is classified "forward" because direction is locked at entry. This is a deliberate design choice (consistency over the episode duration) but it's a choice — alternative implementations could re-classify mid-episode.
- **Last-known-value scroll lookup.** Between scroll events, scroll offset is treated as constant (piecewise). Episodes in long no-scroll gaps could be mis-timed by up to ~1s. Audit log: episodes where `entry_t - last_scroll_t > 2000ms` are flagged for review (see plan doc §7).
- **The `regressive_scroller` trial-level tag is a different heuristic.** It was derived from scroll-sequence patterns before this episode-level classifier shipped. If the two strongly disagree on a trial, the episode-level result is canonical for paper claims; the trial-level tag is a coarser bucket retained for catalog continuity.

---

## Where this rule appears in published / draft work

- **OSEC paper §5.7** (task-model-paper.md) — methodology paragraph, with parity check and tolerance stability claim.
- **CIKM paper-v3 §3** — episode-level direction as a feature of the approach-retreat construct.
- **`approach-retreat/docs/validation/m5-calibration.md`** — direction as input to M5.
- **NB17, NB20, NB23, NB24** — direction as a partition for forward-only vs pooled analyses.

When updating papers or notebooks, treat the implementations in `data_loader.py` and `episode_classifier.py` as canonical. Prose claims that disagree with the code are wrong.

---

## Related docs

- `notebooks-v2/data_loader.py` — `classify_fixations` docstring (canonical per-fixation source).
- `notebooks-v2/episode_classifier.py` — module docstring + `classify_episode` (canonical per-episode source).
- `docs/plans/forward-regressive-split.md` — design rationale, alternative definitions considered, downstream notebook update plan. **Status header is stale; mark "implemented 2026-04-08–04-26" if updating.**
- `docs/findings.md` §8 — ballistic backward scrolling kinematics; uses this classifier upstream.
- `docs/methodological-threats.md` — broader robustness audit context.
