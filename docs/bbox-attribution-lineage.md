# Bbox attribution lineage

The AOI extraction method used to compute per-(trial, position) records
has gone through a sequence of revisions across the AR + upstream AF
stack. Each successive flavor reduces a different attribution
contamination mode. When citing a number from this repo, tag it with the
flavor that produced it; when consuming a number, check which flavor it
was computed under — they are **not** drop-in interchangeable.

## Flavor table

| Flavor | Source | Introduced | Status | What it adds / fixes |
|---|---|---|---|---|
| `absolute` (band) | h3-count row estimation, Y-only attribution | pre-2026-05-01 | **legacy — do not cite for new work** | Original band-based assignment; rolls right-rail (dd_right) and page-chrome clicks into adjacent organics. |
| `bbox-organic` | CV row-projection on shipped screenshots, organic only | 2026-05-01 (AF `4555cb25`) | superseded by `typed` family | Pixel-accurate organic bboxes; no ad / widget / chrome AOIs. |
| `typed` | Screenshot-anchored CV across 13 element types (organic, dd_top, dd_right, native_ad, paa, image_pack, knowledge_panel, related_searches, top_places, unknown_widget, other_widget, chrome, pagination) | 2026-04-30 → 2026-05-01 (AF) | superseded by `typed_gapfill` | Adds all non-organic element types as AOIs; still Y-only click attribution. |
| `organic_hybrid` | `bbox-organic` organics + shipped AdSERP ad rectangles, ordered into one position list with etype tags | 2026-04-30 (AF) | **active** — deployment-aware alternative | Combines pixel-accurate organics with ground-truth ad bboxes for the ad-vs-organic head-to-head used in `docs/research.md` §"LAB". |
| `typed_gapfill` | `typed` + midpoint-split organic bboxes + X+Y bbox-aware click attribution + `is_main_axis_click()` trial filter | 2026-05-05 (AF `ac92bbb4`) | **current canonical** | 91.7 % click attribution coverage (was ~64 %); eliminates the 22.7 % Y-only silent contamination of `approached & clicked` records. Replay viewer is rebuilt against this. |
| `cellsplit` | `typed_gapfill` + per-cell features inside carousels | 2026-05-17 (AF `c7dd202f`); cell bulk `16cd63a6` | **current for carousel-resolved work** | Cell-level granularity inside dd_top carousels (~10 % of carousel clicks otherwise lost to inter-card gaps). Used by `docs/dd-top-cell-promiscuity.md` and the four-class LTR with cell-aware features. |
| DOM-anchored | Direct DOM bbox readout, no CV inference | TBD | future work | The principled alternative to screenshot-CV; named as deferred future work in AF CHANGELOG 2026-05-05. Would close the residual screenshot-anchored failure modes in `typed_gapfill`. |

## What this repo's headline numbers are calibrated against

| Artifact | Flavor in force |
|---|---|
| v0.1.0 M4 nine-feature extractor (CHANGELOG 2026-04-15) | `bbox-organic` + `organic_hybrid` |
| v0.2.0 viewport bands (CHANGELOG 2026-04-19) | `bbox-organic` (NB28 / NB30 retrain, 1,000-seed bootstrap) |
| Replay viewer trials at `site/replay/` | rebuilt against `typed_gapfill` (CHANGELOG 2026-05-05) |
| `docs/dd-top-cell-promiscuity.md` carousel work | `cellsplit` |
| `docs/research.md` LAB headline AUCs | `organic_hybrid` for click prediction, `bbox-organic` for viewport bands |

## How to read flavor tags in cited claims

Numerical claims in this repo carry tags of the form
`[LAB, AdSERP, <flavor>, NB##:K##]`. The flavor token tells you which
cascade produced the number:

- `K-bbox-*` — post-2026-05-01 cascade (`bbox-organic` / `organic_hybrid` / `typed`)
- `K-bbox-y-*` — post-2026-05-05 cascade (`typed_gapfill`); the "y" prefix
  marks the Y-pixel coverage fix as the discriminator
- Legacy unprefixed K-IDs — pre-cascade `absolute` (band) attribution.
  These should be re-cited with their successor wherever possible; until
  they are, treat them as approximate.

When the LAB number for the same statistic differs by flavor, that
difference *is* a finding — `docs/findings.md` `[AR-V1:K8]` documents the
LAB-side lift from `absolute` (0.821) to `bbox-organic` / `organic_hybrid`
(0.864 / 0.870) for the M4 LOSO click target.

## When a new flavor lands

A new bbox flavor lands every few weeks while the cascade is active. The
re-derivation order is fixed by dependency:

1. **NB21 / NB22** first — anchors the four-class taxonomy labels.
2. **NB28 / NB30** next — anchors the viewport-band calibration.
3. **AR replay viewer** last — visual surface; consumes the rebuilt
   per-trial AOI map.

Stale citations get flagged in [`docs/aoi-corrections.md`](aoi-corrections.md);
the producer-side cascade is tracked in upstream
[`attentional-foraging/CHANGELOG.md`](https://github.com/andyed/attentional-foraging/blob/main/CHANGELOG.md).
A further refinement is in flight at the time of writing — readers
encountering a number with a flavor tag predating the latest entry in
that upstream CHANGELOG should treat it as the best-available estimate
under the cascade in force at the cited date, not as the current-best.
