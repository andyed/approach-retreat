# Leiva & Arapakis (2020) — The Attentive Cursor Dataset

**Citation:** Leiva, L. A. & Arapakis, I. (2020). The Attentive Cursor Dataset. *Frontiers in Human Neuroscience*, 14, 565664.

**DOI:** 10.3389/fnhum.2020.565664
**Data:** https://gitlab.com/iarapakis/the-attentive-cursor-dataset

## Dataset

| Metric | Value |
|--------|-------|
| Participants | 2,737 (1,605M, 1,118F, 14 NA) |
| Interaction data | ~2 hours total |
| Task type | Transactional web search (purchasing) |
| Query pool | 150 queries from Google Trends |
| Platform | Figure Eight (Level 3 contributors) |
| Payment | $0.20/task |
| Tracking | EvTrack (open source JS), custom proxy |

## Data Files

- **`logs/`** — Space-delimited CSVs, 8 columns (cursor ID, x, y, timestamp, event, DOM xpath, element attributes, distance to 5 control points). XML metadata per log (viewport, user agent).
- **`groundtruth.tsv`** — User ID, click behavior (binary), self-reported attention (1-5 Likert), log ID.
- **`participants.tsv`** — 12 columns: location, education, age, income, gender, ad placement, ad type, ad category, query, log ID.
- **`serps/`** — HTML snapshots of actual SERPs.

## Key Claim

> "When the mouse cursor is motionless, the user is processing information."

## Relevance to Approach-Retreat

Largest public cursor-on-SERP dataset available. Ground truth includes BOTH click behavior AND self-reported attention scores — can validate four-class taxonomy against subjective attention, not just click/no-click.

150 transactional queries with actual SERP HTML means we can compute AOI bounding boxes from the DOM and replay cursor traces as approach-retreat episodes.

**Status:** Public GitLab repo. Andy emailed Leiva (no response as of 2026-04-07). Data is freely cloneable — no access request needed.

## Validation Plan

1. Clone repo, inventory log format
2. Parse SERP HTML → extract result AOI bounding boxes
3. Map cursor events to episode model (enter/dwell/exit)
4. Classify episodes into four-class taxonomy
5. Validate against ground-truth attention (1-5 Likert) and click
6. Compare F1 against AdSERP numbers (0.70 and 0.66 for split non-click classes)
