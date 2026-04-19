# Approach-Retreat

Cursor episode decomposition library for SERP evaluation. Parses raw cursor telemetry into approach/dwell/retreat episodes per result, extracts geometric features (arc ratio, Fitts ID, max retreat distance), and predicts click outcomes.

## Role in the CIKM paper: the LAB ↔ WILD bridge

This repo is the portable cursor substrate. It runs the same four-class taxonomy (clicked / deferred / evaluated-rejected / not-approached) in both regimes — that's what makes the paper's central claim tractable.

- **LAB (AdSERP)** — 47 participants, Gazepoint 150 Hz gaze + pupil + cursor. Library features are validated against the upstream Key Claims (`attentional-foraging` notebooks NB20–NB24). When prose or figures cite LAB numbers from this repo, use `[LAB, NB##:K##]` so the tag threads back to the canonical source.
- **WILD (ACD)** — Leiva & Arapakis, *Frontiers in Human Neuroscience* 2020, ~2,909 crowdsourced sessions, **cursor and click only, no eye tracker, no pupil.** The self-contained replication lives at `analysis/attcur-validation/`. Tag WILD numbers `[WILD, attcur]`.

**The point of the convention.** Any LAB finding that requires gaze or pupil is LAB-only by construction. Everything else must be rebuilt from cursor alone and re-tested on ACD to earn the `[BOTH]` tag. The library is the instrument that makes that rebuilding mechanical — `attcur-validation` exercises the same feature extractor on a gaze-free cursor stream and reports which LAB results survive.

**Never call ACD "deployment" or "production."** It is crowdsourced; `WILD` is honest. `deployed` is not.

**What fits where:**
- Four-class taxonomy discrimination → **`[LAB]`-only until further notice.** The deferred/eval-rejected split requires the gaze-fixation sequence revisiting earlier result positions (see `attentional-foraging/notebooks-v2/22_four_class_taxonomy.ipynb`). The feature commonly called `scroll_regressed_back` is actually **gaze-regression** — it reads `fix['y']`, not scroll events. A scroll-only detector is future work that would earn `[BOTH]` for the taxonomy if validated.
- retreat_dist / min_dist / total_dwell / direction_changes → `[BOTH]` (these are pure cursor features, no gaze dependency)
- LOSO LR on M4 feature set predicting **click vs no-click** → `[BOTH]` (this is the cross-dataset AUC comparison: AdSERP LAB AUC 0.861 vs ACD WILD AUC 0.821 on the analogous binary click target)
- LOSO LR on M4 feature set predicting **deferred vs eval-rejected** → `[LAB]`-only (labels are gaze-derived)
- Gaze-cursor coupling median (306/283/197 px) → `[LAB]` only (ACD has no gaze stream to measure against)
- Pupil-derived cognitive load (LHIPA, Butterworth LF/HF) → `[LAB]` only (ACD has no pupil)
- Element-type discrimination cost → `[LAB]` only (requires pupil + proximity dwell)

When the LAB and WILD numbers for the same statistic diverge, that is itself a finding — report the divergence, don't paper over it.

## Notebook Conventions

This repo cites quantitative claims from the upstream `attentional-foraging` repo using `[NB##:K##]` notation. When updating numbers in README.md or docs/:

- Always check that cited values match the current `attentional-foraging/docs/notebook-key-claims.md`
- Mark values with their source: "(NB21:K3, post coordinate-space audit 2026-04-12)" — two audits have landed so far, cursor-side 2026-04-09 and fixation-side 2026-04-12
- If upstream Key Claims change, update all downstream references here

Full convention spec: https://github.com/andyed/science-agent/blob/main/docs/notebook-conventions.md

## Validation

- AdSERP validation lives in `attentional-foraging` notebooks (NB20, NB21, NB22, NB24)
- Bruckner ACD validation is self-contained: `analysis/attcur-validation/`
- Run `science-agent notebook-audit ./docs --cross-repo=.` to check for stale values

## Clicksense Alignment

Approach-retreat's schema is intentionally distinct — the analytical unit is
the *episode* (approach/dwell/retreat against a SERP position), not the click.
`ar_episode`, `ar_click`, `ar_session_summary` stay prefixed and schema-
independent.

**Where alignment is worth it:** the DOM-target vocabulary on `ar_click`
events. As of 2026-04-17, `ar_click` emits the clicksense v0.2 target fields —
`target_tag`, `target_id`, `target_label`, `target_href`, `target_text`,
`target_aria_label`, `target_title`, `target_name` (computed accessible name),
`target_path` (short CSS selector), and `target_data_<key>` for every data-*
attribute. Shared vocabulary, not shared code — the extractor is inlined in
`src/adapters/posthog.js` to preserve schema independence.

This lets you JOIN click_confidence ↔ ar_click on `target_href` or
`target_name` when both instruments are running on the same page.

The AR library also passes `click.element` (the actual DOM node) alongside
the existing `click.target` (the result container) to `onClick` handlers, so
adapters can identify the specific clicked link/button.

## Key Decisions

- **Four-class taxonomy:** clicked / deferred / evaluated-rejected / not-approached
- **Coordinate space:** cursor Y is page-space (same as attentional-foraging)
- **NB24 v2 (2026-04-08):** original had fatal bugs. The element-type arc ratio signal is ns under participant clustering; the surviving signal is re-approach prediction
- **direction_changes:** was a scroll artifact pre-2026-04-09 (coefficient +0.20 → −0.005 after cursor fix). After the 2026-04-12 fixation-side fix the coefficient is +0.061 — a small but non-trivial positive contribution. The feature is still weak relative to dwell and distance features; retaining or dropping it is a design call, not a correctness issue.
- **Viewport bands (2026-04-19, v0.2.0):** per-AOI cumulative ms in `{any, top, mid, bot}` viewport bands, piecewise-constant over scroll/resize/reflow. JS `computeViewportBandsPure` parity-tested against `viewport_ms_for_trial` in the calibration script (Δ = 0). Calibration (LAB, n = 2,351, bootstrap 95 % CIs): retreat-alone 0.796 [0.759, 0.830], bands-alone 0.800 [0.774, 0.828], combined **0.842 [0.818, 0.864]**. Fully-contextual viewport (all 10 AOIs × rank dummies) is worse — the signal is local per-AOI. `vt_top` coefficient is rank-dependent: +2.02 at P0, crosses 0 at P5, weak-but-CI-clean +0.75 in the P6+ bucket (n = 201). Per-position estimates past P5 are pooled into P6+ because sparsity and class-balance inversion make them noise. Consumers apply per-rank weights, library emits raw ms. Tag: `edmonds-2026-vpbands-v1`. See `docs/validation/viewport-bands-calibration.md`.
