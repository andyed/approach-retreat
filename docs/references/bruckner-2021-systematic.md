# Brückner, Arapakis & Leiva — *When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search* (SIGIR '21)

[`bruckner2021systematic`](references.bib) · [DOI 10.1145/3404835.3463055](https://doi.org/10.1145/3404835.3463055)

The direct comparator for `approach-retreat` on cursor-only signal. Same dataset (Attentive Cursor Dataset, Leiva & Arapakis 2020), same target population (the native-ad subset), same outcome variables. The BiLSTM-over-`(x,y,t)` family vs the per-AOI episode-geometry family on identical inputs.

## Method

Three target variables on the ACD:
1. **Ad noticeability** — self-report Likert (was the ad noticed?)
2. **Result-page abandonment** — did the user click any result on the SERP?
3. **Frustration** — composite UX self-report

Cursor-only inputs. The headline cursor primitive is **total mouse movement length** (a scalar that sums the per-step Euclidean displacement across the session). BiLSTMs over the raw sequence are presented as the more sophisticated model class. The systematic comparison is the paper's contribution — different model classes on identical inputs.

## Key results

- **Mouse-length scalar baseline reaches AUC ~0.69** on the ad-clicked target on the native-ad subset. Per-figure AUC reads in the paper; reproduced at AUC 0.696 ± 0.031 in `analysis/attcur-validation/run_analysis.py` and 0.653 ± 0.031 under the matched 500 ms click-buffer.
- **BiLSTM beats the scalar baseline by a few AUC points** on noticeability and abandonment, but margins are modest. The paper's framing is that *cursor signal exists* but its predictive ceiling against self-report is bounded.

## Where approach-retreat extends the result

The Brückner paper's primitive is *per-session*: total mouse path summed across the whole encounter. That choice is exactly the unit-of-feature-aggregation gap `approach-retreat` targets. On the same ACD subset:

- Scalar mouse-length baseline (Brückner): AUC 0.696 (no buffer); 0.653 (with 500 ms click-buffer leakage control).
- 11-feature approach-retreat (per-AOI episode geometry): AUC 0.821 (no buffer); 0.781 (with click-buffer); 0.765 (10-feature leakage-screened).

The relative claim (approach-retreat beats Brückner by +12 AUC points on identical data) survives leakage controls in both directions. See `analysis/attcur-validation/results.txt` for the full grid.

## Why this paper is the right comparator (not, say, BiLSTM-over-everything)

Brückner *et al.* explicitly framed mouse-length as the natural cursor-only baseline: a single scalar capturing how much cursor activity occurred over the encounter. Per-AOI episode geometry adds a different abstraction — *which AOI* the cursor approached and what the trajectory looked like on each — without changing the underlying signal source. Comparing those two abstractions on identical inputs is what the SIGIR '21 paper enables, which is why ACD is a useful WILD validation surface for `approach-retreat`.

## What the paper does not address

- No per-result attribution: the cursor stream is treated as a session-level signal.
- No four-class taxonomy: the targets are session-outcome variables, not within-session AOI states.
- No leakage screen / click-buffer protocol: the single ad-click ends the session, so terminal-cursor lock-on contaminates feature aggregation in the same way that motivates the `approach-retreat` click-buffer in CIKM §4.4.

## Notes for the CIKM paper

§4.5 cites this work as the **scalar mouse-length baseline** (0.653 ± 0.031 under the matched click-buffer). The 11-feature and 10-feature approach-retreat numbers in the same table are head-to-head against this baseline on identical data. Cite as `\cite{bruckner2021systematic}`.
