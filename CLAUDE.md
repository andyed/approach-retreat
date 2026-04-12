# Approach-Retreat

Cursor episode decomposition library for SERP evaluation. Parses raw cursor telemetry into approach/dwell/retreat episodes per result, extracts geometric features (arc ratio, Fitts ID, max retreat distance), and predicts click outcomes.

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

## Key Decisions

- **Four-class taxonomy:** clicked / deferred / evaluated-rejected / not-approached
- **Coordinate space:** cursor Y is page-space (same as attentional-foraging)
- **NB24 v2 (2026-04-08):** original had fatal bugs. The element-type arc ratio signal is ns under participant clustering; the surviving signal is re-approach prediction
- **direction_changes:** was a scroll artifact pre-2026-04-09 (coefficient +0.20 → −0.005 after cursor fix). After the 2026-04-12 fixation-side fix the coefficient is +0.061 — a small but non-trivial positive contribution. The feature is still weak relative to dwell and distance features; retaining or dropping it is a design call, not a correctness issue.
