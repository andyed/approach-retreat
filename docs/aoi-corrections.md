# AOI corrections (audit-layer overrides)

Human-adjudicated AOI reclassifications applied **on top of** the upstream `attentional-foraging/scripts/extract_organic_bboxes.py` output, only at the audit-surface layer.

## Why a separate layer

The replay testbed exists to surface AOI extraction bugs. When an audit finds one (e.g. an inline "Images for…" carousel slipping through as an organic result on `p048-b1-t6`), the question is *where* to fix it.

Two layers, two contracts:

- **Upstream extractor (`attentional-foraging`)** — canonical algorithm. Every quantitative AdSERP claim and every K-ID in `notebook-key-claims.md` quotes its output. Silently rewriting it would drift the published numbers.
- **Audit-surface (`approach-retreat/site/replay/data/aoi_corrections.json`)** — overrides applied at viewer-build time. Lets reviewers see the corrected ground truth without disturbing upstream stats.

Corrections live in the audit layer until a deliberate re-extraction pass pulls validated overrides upstream. Until then, the audit JSON is also the eventual ground-truth set for an AOI-accuracy metric (corrections / total).

## File format

`site/replay/data/aoi_corrections.json` — keyed by trial_id.

```json
{
  "p048-b1-t6": {
    "demote_to_widget": [11],
    "note": "Position 11 is Google 'Images for...' inline image carousel; extractor's widget detector only catches bottom-of-page refinement widgets."
  }
}
```

Supported keys per trial:

- `demote_to_widget: [int, ...]` — organic positions reclassified as widget. Remaining organics are renumbered contiguously. The demoted bbox is appended to `widget` with `reason: "manual_correction"`.
- `note: str` — required for every entry; one sentence on why.

Future-supported (add when first needed; don't pre-build):
- `promote_to_organic` — for false negatives in the extractor (extractor missed a real organic).
- `merge` / `split` — for cards that should be one bbox but are two, or vice versa.
- `rebbox` — explicit `{x, y, w, h}` replacement.

## How a correction flows through

1. Reviewer spots a misclassification on `andyed.github.io/approach-retreat/replay/trials/<trial>.html`.
2. Add an entry to `site/replay/data/aoi_corrections.json` with the trial_id, demotion list, and a note.
3. Re-run `python3 scripts/build_replay_pages.py` (or the targeted `brt.build_trial(trial_id)` path); `apply_aoi_corrections` in `scripts/build_replay_trial.py` reads the JSON, edits the bundle, and renumbers organic positions.
4. Commit + push. The viewer renders demoted widgets as gray dashed bboxes with the `W` tag, so the correction is visible — not silent.

## What this does NOT touch

- Upstream `attentional-foraging/AdSERP/data/organic-boundary-data/<trial>.json` — unchanged.
- Any `[NB##:K##]` claim or rank-type-tagged number — unchanged.
- The CIKM paper's quantitative content — unchanged.

If a critical mass of corrections accumulates (or one identifies a patternable extractor gap, e.g. "all inline image-pack carousels"), the right move is either:

- **Patch the extractor** in `attentional-foraging/scripts/extract_organic_bboxes.py` so the upstream output catches the case, then drop the corresponding override(s) from `aoi_corrections.json`. Re-run K-claim retrains since organic counts/positions can shift.
- **Or quantify the audit layer as a metric** — report `n_corrections / n_aois` per composition cluster as the AOI-accuracy headline number. Useful when corrections are too scattered to admit a single extractor patch.

Either path is a deliberate decision, not a default. The default is: corrections sit in the audit layer.
