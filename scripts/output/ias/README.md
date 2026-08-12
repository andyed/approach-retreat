# AdSERP AOIs in EyeLink .ias format — for the PAI demo

Three AdSERP trials from the approach-retreat replay set
(https://andyed.github.io/approach-retreat/replay/), exported for
`glias2poly_1920x1080.py`.

## Contents

- `fold/<trial>.ias` — above-the-fold crop, canvas **1280 x 1080**. Runs
  directly:

      python3 glias2poly_1920x1080.py --ias fold/p047-b6-t1.ias --width 1280 --height 1080

- `full/<trial>.ias` — full-page canvas (1280 wide; height = screenshot
  height, see below). Every AOI on the page.
- `full/<trial>.jpg` — the matching SERP screenshot (what the participant
  saw), same pixel space as the AOI coordinates, in case you want to texture
  the background.
- `pai_proof_<trial>.png` — sanity render: your parser + your PAI alpha
  (CGD/OGD, w_A = (A_max/area)^0.236) applied to these files, overlaid on the
  screenshot with a simulated gaze point.

## Trials

| trial | story | full-page height |
|---|---|---|
| p047-b6-t1 | multi-AOI drama: 5-cell ad carousel + 10 organics + 3 text ads | 2749 px |
| p006-b4-t7 | canonical evaluated-rejected trial | 2703 px |
| p019-b1-t8 | canonical deferred trial | 3054 px |

## Conventions

- Coordinates are screenshot pixel space, y=0 at top (matches your glOrtho).
- Labels are single tokens (your regex takes `\S+`) and unique per file:
  `organic_<rank>`, `dd_top_cell_<n>` (ad-carousel cells), `native_ad_<n>`,
  widget types (`image_pack_1`, `paa_1`, `related_searches_1`, ...).
- Rectangle perimeters are densified to ~4 px vertex spacing so your
  vertex-based OGD approximates true boundary distance (same reason your
  freehand files have ~1 px spacing). Exact-boundary vs nearest-vertex OGD
  therefore differs by <= 2 px here.
- Parent carousel containers are omitted when their cells are present, so
  nested polygons don't double-count in the per-AOI display.

## Provenance

AOI geometry: AllSERP (arXiv:2605.04949) on AdSERP (Latifzadeh, Gwizdka &
Leiva, SIGIR 2025; Zenodo 15236546). Exporter:
`approach-retreat/scripts/export_ias.py` — can emit all 86 curated replay
trials with `--all` if you want more.
