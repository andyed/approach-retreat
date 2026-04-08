# Huang, White & Buscher (2012) — User See, User Point

**Citation:** Huang, J., White, R. W., & Buscher, G. (2012). User see, user point: Gaze and cursor alignment in web search. *CHI '12*, pp. 1341-1350.

**DOI:** 10.1145/2207676.2208591
**PDF:** https://jeffhuang.com/papers/GazeCursor_CHI12.pdf

## Key Numbers

| Metric | Value |
|--------|-------|
| Participants | 36 (38 recruited, 2 dropped) |
| Tasks per subject | 32 (16 navigational, 16 informational) |
| Total query sessions | 1,210 |
| Gaze positions | 1,336,647 |
| Cursor positions | 87,227 |
| Eye tracker | Tobii x50, 50 Hz |
| Cursor sampling | ~10 Hz (100 ms) |

## Core Findings

**Temporal lag:** Cursor lags gaze by **~700 ms** on average. Range 250 ms to >1 second across individuals. Cursor ALWAYS lagged gaze (never inverse).

**Five cursor behaviors and gaze alignment:**

| Behavior | % of Time | Median Gaze-Cursor Distance |
|----------|-----------|---------------------------|
| Inactive (idle >1s) | 58.8% | 233 px |
| Examining (scanning) | 32.9% | 167 px |
| Reading (tracing text) | 2.5% | 150 px |
| Action (within 1s of click) | 5.7% | 77 px |
| Click | — | 74 px |

**Gaze prediction from cursor:**

| Model | RMSE (distance) |
|-------|----------------|
| Cursor alone (baseline) | 236.6 px |
| + Behavior + Dwell | 186.3 px (−21.3%) |
| + Future cursor | 181.1 px (−23.5%) |

**Individual differences dominate task differences** (Levene's F = 4.529, p = 0.037).

## Relevance to Approach-Retreat

> "Claiming that the cursor approximates the gaze is misguided" — alignment is situational.

Their "inactive" category (59% of time, 233 px distance) collapses our NOT_APPROACHED and EVALUATED_REJECTED into one undifferentiated class. The four-class taxonomy splits exactly what they left unresolved.

The 700 ms lag means cursor episodes are trailing indicators of attention decisions already made — the approach-retreat timeline is the *motor trace* of a cognitive evaluation that happened ~700 ms earlier.

Their top predictive feature is `log(dwell_time)` — dwell is the strongest cursor-based gaze predictor. We use dwell as the primary signal in episode classification.

## Limitations

- Lab setting (36 subjects, artificial tasks)
- SERP-only (may not generalize beyond search)
- Linear model (conservative, tends toward center)
- No cursor fixation analysis
