# Bbox attribution lineage

Updated 2026-09-04. The late-August AllSERP audit found substantial gaps in
page parsing and in matching parsed elements to screenshot boxes. Those
gaps changed result identity and rank, not just rectangle precision.
Collaborator review helped expose them and made independent fidelity
checks part of the measurement pipeline.

The current typed substrate is **AllSERP v1.1.0 after the card-collision
fix**: map hash `2cb789eb8febd234`, 2,776 stored trial maps, **12 alignment
exclusions**, and 2,764 eligible trials before analysis-specific filters.
The [substrate stamp][stamp] and [exclusion list][exclusions] define that
identity. The research journey is in [history.md](history.md); model
evidence and remaining reruns are in [current-evidence.md](current-evidence.md).

## Attribution definitions and evidence status

| Flavor | What it represents | Status and boundary |
|---|---|---|
| `absolute` | Estimated horizontal result bands; Y-only attribution | Legacy reference, unsuitable as the default for new claims. |
| `organic` / `bbox-organic` | Screenshot-CV boxes treated as organic results | A distinct analytical view; the unresolved phantom-local-pack slot caveat below applies. |
| `organic_hybrid` | Organic CV boxes plus the dataset's ad rectangles | Distinct from typed display order. Later mouse-coordinate conversion changed its features and click labels. |
| `typed` | HTML element identities joined to screenshot geometry, including widgets | Rebuilt with rendered geometry, identity checks, node ownership, and exclusions. Widget blocks are first-class display-order slots. |
| `typed_gapfill` | Typed AOIs with gap coverage and X+Y click attribution | Shares the corrected typed identity substrate; its definition does not make historical attribution percentages current. |
| `typed_gapfill_cellsplit` / `cellsplit` | Per-cell subdivision inside top-ad carousels | **Unrepaired cell source.** Quantitative per-cell claims remain pending a reproducible DOM-derived producer and validation. |
| Live DOM instrumentation | Bounding boxes read from the host page | The library can measure actual elements directly; this does not retroactively validate the reconstruction of archived SERPs. |

The August fixes retain the existing flavor names. A flavor describes an
attribution definition; a commit, map hash, exclusion set, coordinate
space, and producer version identify the particular measurement.

## What the page-parsing audit found

**Missing local packs, August 28.** The HTML walker covered `#rso`,
`#botstuff`, and `#rhs`, but some Google local-results blocks were sibling
subtrees outside `#rso`. The screenshot extractor detected their boxes;
the HTML extractor emitted no corresponding card. Index-based matching
then paired each following HTML card with the preceding screenshot box.
This affected **268 / 2,776 trials**, putting **1,930 organic AOIs one
slot early** in the affected typed maps. Explicit local-pack detection
removed that particular shift. [Audit and extent][packs]

**HTML/CV count mismatches.** Adding the missing pack did not repair
ordinary over-segmentation or merged HTML wrappers. Card and box counts
differed in 1,909 trials; that was an exposure upper bound, not a count of
confirmed corrupt trials. The replacement measures rendered card geometry
and aligns cards to boxes in vertical order, permitting unmatched entries
and joining split segments where supported. A low geometric residual alone
is insufficient: an evenly spaced result list can still align one slot
wrong. The exclusion gate also checks height mismatch. [Resolution][packs]

**Parser and browser trees differ.** Python's HTML parser kept some
right-rail panels inside `#rso`; Chromium reparented them. Positional CSS
selectors could consequently resolve a neighboring card while appearing
to succeed. The first verification pass found **2,606 cards across 745
trials** carrying a neighbor's geometry. Measurement now verifies card
identity and routes rendered off-column elements outside the main-column
alignment. Unverifiable cards remain unresolved. [Geometry verification][packs]

**Two cards claiming one node, August 30.** Independent selector repair
still allowed adjacent cards with similar text lengths to claim the same
DOM node. The audit observed **508 duplicate cards across 454 trials**.
The fix reserves verified original-node matches first, then awards repair
candidates by identity evidence; a node cannot be owned twice and tied
candidates remain unresolved. Observed duplicate cards fell to **0**;
trials with orphaned main-column results fell **480 → 167**. This repaired
result ownership, while leaving real unresolved cases visible.
[Producer fix][collision] · [Rebuilt substrate][rebuild]

The final exclusion count is **12**, superseding the earlier 14-trial
list. Membership also changed: `p034-b6-t5`, `p041-b1-t9`, and `p046-b6-t5`
left; `p018-b3-t1` entered. Consumers must read the [current list][exclusions],
not merely subtract a remembered count.

## The audit also had to audit itself

The first fidelity harness reused an unreliable `css_path` and reported
a severe low-IoU tail. Independent class-and-heading resolution showed
that much of that apparent tail was the checker measuring the wrong node.
The corrected full-corpus baseline had **2,593 / 2,776 trials (93.4%)**
at trial-median AOI IoU ≥ 0.5; p10 IoU changed **0.428 → 0.853** because
the measurement was corrected. This is not a corresponding improvement
in the underlying data. Ambiguous identities and orphaned AOIs are not
fully represented by that score. [Corrected baseline][fidelity]

The subsequent **120-trial** post-collision sample is a separate check:
click containment **110/119 (92.4%)**, trial-median AOI IoU ≥ 0.5
**112/120 (93.3%)**, and cell-count agreement **18/58 (31.0%)** among
comparable carousel records. These were rechecked from the locally retained
`scripts/output/aoi_fidelity_postCollisionFix.json`, using the public
[fidelity harness][harness]; they are sample results, not full-corpus rates.

## What remains unresolved

**Carousel cells.** The full-corpus baseline agrees with visible DOM cell
counts on only **451 / 1,551 comparable trials (29.1%)**. Exports are short
on 902 trials, with a median shortfall of one cell. This is distinct from
the 31.0% sample above and was not repaired by the card-collision fix.
The frozen May 24 cell snapshot lacks an in-repository producer. Re-running
ranking analyses against it would repeat the faulty subdivision. A new
DOM-derived cell producer must pass fidelity checks before per-cell rank,
click-gradient, or graded-ranking claims can be refreshed. Historical
within-carousel monotonicity is not current evidence. [Baseline][fidelity]
· [Cell-source gate][rerun]

**Organic-flavor local packs.** The typed map now names the pack, but the
CV `organic_result` list can still contain its box as a phantom organic
slot in those 268 trials. Thus `organic` rank sequences retain inflation
below the pack. Typed display order intentionally includes widget slots;
typed `organic_rank` counts organics only. These semantics and the
unresolved organic-only extraction caveat must not be conflated. [Caveat][packs]

**Mouse-coordinate conversion is a separate correction.** Converting
document-space cursor/click coordinates to screenshot space is not page
parsing. The August 31 producer rerun changed `organic_hybrid` features
and reattributed clicks, even though the typed parsing fixes had left
the organic flavors' source boxes alone. Earlier statements that their
numbers were "unmoved" are therefore obsolete. [Conversion evidence][environment]

A downstream result is current only when its own producer has rerun with
the appropriate inputs and exclusions. A corrected viewer, a low alignment
residual, and a successful model execution answer different questions.

[stamp]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/data/aoi-typed/substrate.json
[exclusions]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/data/aoi-typed/alignment-exclusions.json
[packs]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/docs/local-pack-aoi-shift.md
[collision]: https://github.com/andyed/attentional-foraging/commit/86f800a351485af200929e8679ac35ea14377968
[rebuild]: https://github.com/andyed/attentional-foraging/commit/2da0544d331a6a2a4db39d4ea14c3de1f289b4bf
[fidelity]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/docs/aoi-fidelity-baseline-2026-08-30.md
[harness]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/scripts/aoi_fidelity.py
[rerun]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/docs/rerun-spec-2026-08-30.md
[environment]: https://github.com/andyed/attentional-foraging/blob/b5d669593290d91331fad9d12692b3fbd118f717/docs/canonical-environment.md
