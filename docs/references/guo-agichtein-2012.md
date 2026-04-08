# Guo & Agichtein (2012) — Beyond Dwell Time

**Citation:** Guo, Q. & Agichtein, E. (2012). Beyond dwell time: estimating document relevance from cursor movements and other post-click searcher behavior. *WWW '12*, pp. 569-578.

**DOI:** 10.1145/2187836.2187914

## Important Clarification

Often cited as "cursor trail features predict result relevance on SERPs" but this paper is about **post-click** behavior on **landing pages**, not cursor behavior on the SERP itself. The cursor features are extracted after the user clicks a result and lands on the destination page.

## What We Know

- **Post-Click Behavior (PCB) model** — first to incorporate post-click cursor movements and scrolling for relevance estimation
- **Cursor features:** average position, speed, direction, traveled distance, horizontal/vertical range, max/min positions, scroll speed/frequency/distance, cursor position within regions of interest
- **Behavioral patterns:** "Reading" (consuming relevant content) vs. "Scanning" (still searching)
- **Key result:** PCB significantly outperforms dwell time alone for per-user relevance estimation and result re-ranking

## Related Guo & Agichtein Papers

- **(2008)** SIGIR — "Exploring mouse movements for inferring query intent" — cursor ON the SERP, navigational vs. informational classification
- **(2010)** CHI EA — "Towards predicting web searcher gaze position from mouse movements" — 77% accuracy gaze-cursor alignment, ~178 px mean distance
- **(2013)** CHI EA — "Towards estimating web search result relevance from touch interactions on mobile devices" — touch, not cursor

## Relevance to Approach-Retreat

The PCB model shows that cursor dynamics carry relevance signal even on landing pages. Our contribution extends this to the SERP evaluation phase — where the user hasn't clicked yet. The pre-click evaluation is where the four-class taxonomy operates.

Their "reading vs scanning" behavioral distinction maps loosely to our evaluate vs. survey phases in OSEC, but on a different surface (landing page vs. SERP).

## Limitations

- Full numeric results not available (paywalled)
- Post-click only — doesn't address pre-click evaluation
- Landing page behavior, not SERP behavior
