# Theory of Approach/Retreat

## What this library measures

A user evaluates a SERP result through a sequence of cursor episodes — entering an area of interest (AOI), dwelling, and either committing (click) or leaving. The leaving is the *retreat*, and its geometry carries signal about whether the user is finished with that result or might come back.

This library captures three things per result, episode by episode:

- **Approach.** The cursor enters the AOI; how fast and at what angle.
- **Dwell.** Time spent inside the AOI; the cognitive evaluation phase.
- **Retreat.** What happens after the cursor leaves: arc length, max distance from the AOI, lateral displacement, and the Fitts' law index of difficulty for returning.

These episodes resolve into a four-class outcome per result: **clicked**, **deferred** (the user came back), **evaluated-rejected** (entered but didn't return), or **not-approached**.

## The signal we're after

The cursor doesn't just navigate; it narrates the evaluation. Three patterns:

1. **Approach velocity tracks information scent.** Fast scanning approaches mean the user is looking; slow deliberate approaches mean the user is reading.
2. **Dwell tracks evaluation effort.** Long dwells with no click are evaluation followed by rejection. Long dwells with clicks are deliberation followed by commitment. ClickSense [1] captures the deliberation signal at the moment of commitment; this library captures it during evaluation.
3. **Retreat geometry tracks the deliberation/commitment boundary.** This is the signal that motivated this library. When the user leaves a result without clicking, the *shape* of the leaving trajectory predicts whether they will come back. Curved + close retreats predict re-approach (deliberation continues). Straight + far retreats predict that the rejection sticks (decision committed).

The third pattern was tested on the AdSERP dataset (2,776 trials, 47 participants, simultaneous eye + mouse + pupil tracking) with these features per retreat episode:

| Feature | Re-approached (median) | Rejected (median) | Mann-Whitney |
|---|---|---|---|
| Arc ratio (path / direct distance) | 2.35 | 1.35 | p = 8.4 × 10⁻⁴ |
| Max retreat distance (px) | 369 | 415 | p = 0.022 |
| Fitts' law ID (bits) at max retreat | 1.32 | 1.72 | p = 3.5 × 10⁻⁴ |

N = 731 retreats, 7.8% re-approach rate. **Pattern: curved + close + low ID = "I'll be back"; straight + far + high ID = "I'm done."** Caveat: pooled-arc statistics; mixed-effects model needed for reportable inference.

## What we're not claiming

We initially proposed an "epistemic action" interpretation (Kirsh & Maglio, 1994) — that retreat distance was a self-imposed motor cost the user was using to encode rejection confidence into physical space, like short-order cooks turning plates to encode dish state. **The data did not support this**, and we rejected it. Specifically:

- Top-of-page sponsored ads do *not* produce dramatically curvier retreats than organic results once participant-level variance is accounted for (Mann-Whitney p = 0.26 participant-clustered, vs the artifactual p = 1.4 × 10⁻⁹ from a coordinate-system bug in our first analysis).
- Dwell time is *not* correlated with retreat curvature (rho = -0.06, ns).
- Top ads have *lower* Fitts ID than organic at max retreat — but only because they are taller targets, which is a geometric property of the page, not a behavioral signal.

What survives: retreat geometry as a *correlate* of the deliberation/commitment state, not as a *mechanism* of it. The cursor narrates the decision; it does not implement it.

## Why this matters: better negatives for ML ranking

The practical payoff is training-data quality for learning-to-rank models. Click logs treat every non-clicked result as an undifferentiated negative — both the result the user looked at and rejected, and the result the user never even saw. A binary `clicked / not_clicked` label sends both to 0, and the ranker learns from the noise.

Episode segmentation gives a four-class label that distinguishes them:

| Class | Cursor signature | Use as label |
|---|---|---|
| **clicked** | enter → dwell → click | positive |
| **evaluated-rejected** | enter → dwell → straight-far retreat → no return | strong negative (the user looked and said no) |
| **deferred** | enter → dwell → curved-close retreat → re-approach | weak negative or hold-out (the user is still considering) |
| **not-approached** | cursor never entered the AOI | unknown (not a negative — the user never looked) |

A learning-to-rank model trained on this taxonomy gets cleaner gradients than one trained on binary clicks. Retreat geometry is what splits *evaluated-rejected* from *deferred* when the user has not yet committed to either: arc ratio, max retreat distance, and Fitts ID at max retreat are continuous within-class signals at that boundary.

This is not about adaptive reranking on the deployed page. The library does not ship a ranker. The contribution is the labels — what the upstream training pipeline gets to consume.

Discrimination cost is also invisible to position-only models. Top-of-page sponsored results have a distinctive cursor signature — 2× approach rate, 2.3× longer dwell, highest pupil dilation — driven by the user spending cognitive effort on type identification ("is this an ad?"), not on reading. The economic SERP utility framework C/W/L (Azzopardi, Thomas & Craswell, SIGIR '18) [2] predicts ads cost less than organic results; the data show top ads cost more, by every cursor and pupil metric. A discrimination cost term is needed for elements requiring category resolution before evaluation.

## How this differs from ClickSense

ClickSense [1] is the companion library for click commitment. The two are deliberately complementary, but the architectural difference is the unit of analysis, not the timing:

- **ClickSense is element-agnostic.** It instruments any clickable target on any page. Its approach features (`approach_linearity`, `approach_max_deviation`, `approach_trajectory_type`) are geometric invariants of the cursor trajectory itself, computed against the implicit point target of the eventual mousedown. It works in a vacuum: no markup, no AOIs, no list structure required.
- **approach-retreat is list-aware.** It requires the host page to mark vertical SERP-list items with `data-result` and `data-position` attributes. The library uses those AOIs as the unit of analysis: enter/dwell/exit episodes per result, four-class outcome per result, retreat geometry against a known result rectangle.

Without the marked cells you cannot do episode segmentation, you cannot identify the deferred class, and you cannot compute retreat geometry against a meaningful AOI. The list structure is what gives this library its leverage. ClickSense answers "how was this click made?" approach-retreat answers "what was the user doing across this list?"

The two libraries can run on the same page. ClickSense captures the moment of commitment; approach-retreat captures the episode structure that led there.

## Theoretical lineage

This library is the deployable form of a research program that combines three traditions:

1. **Cursor as implicit signal for relevance** — Guo & Agichtein (WWW '12) [3], Huang, White & Buscher (CHI '12) [4], Arapakis & Leiva (SIGIR '16) [5], Brückner et al. (SIGIR '21) [6], Villaizán-Vallelado et al. AdSight (SIGIR '25) [7]. The progression: hand-crafted features → cursor as gaze proxy → 638 features → mouse length → Seq2Seq Transformer. Each iteration adds modeling power but stays within the bag-of-features paradigm.
2. **Information foraging on SERPs** — Pirolli & Card (1999) on information foraging theory, Azzopardi & colleagues' economic SERP utility framework (SIGIR '14, '18, ECIR '18) [2,8], Liu et al. CIKM '14 two-stage examination model [9]. The foraging tradition models *when* users stop and *whether* they switch patches; it does not model the within-result micro-behavior.
3. **Cognitive process models for SERP evaluation** — what the OSEC framework (orientation → survey → evaluate → commit) tries to add. This is the contribution: a process model that predicts which cursor features will be informative, and at what segmentation level (per-trial, per-result, per-episode).

The relationship between bag-of-features and task-model approaches is complementary, not competitive. A neural net trained on the four-class taxonomy as labels would likely outperform either alone. The four classes are a target the bag-of-features approach has not been computing because nobody framed the problem that way.

## What the library does and does not do

It captures cursor-AOI episodes and computes their geometry. It does *not* require an eye tracker, server-side processing, or a trained model at inference time. The classification is rule-based (using the geometry features above) and runs in the browser.

A `computeRelevance()` method is exposed for host applications that want to use the collected episode data — for example, to feed a downstream ranker. No ranker ships with the library.

---

## References

[1] Edmonds, A. (2026). ClickSense: click confidence measurement from motor behavior. https://github.com/andyed/clicksense

[2] Azzopardi, L., Thomas, P., & Craswell, N. (2018). Measuring the Utility of Search Engine Result Pages. *SIGIR '18*, 605–614. https://doi.org/10.1145/3209978.3210027

[3] Guo, Q. & Agichtein, E. (2012). Beyond dwell time. *WWW '12*, 569–578. https://dl.acm.org/doi/10.1145/2187836.2187914

[4] Huang, J., White, R. W., & Buscher, G. (2012). User see, user point. *CHI '12*. https://dl.acm.org/doi/10.1145/2207676.2208591

[5] Arapakis, I. & Leiva, L. A. (2016). Predicting User Engagement with Direct Displays Using Mouse Cursor Information. *SIGIR '16*, 599–608. https://dl.acm.org/doi/10.1145/2911451.2911505

[6] Brückner, L., Arapakis, I., & Leiva, L. A. (2021). When Choice Happens. *SIGIR '21*, 1510–1514. https://dl.acm.org/doi/10.1145/3404835.3463088

[7] Villaizán-Vallelado, M., Salvatori, M., Latifzadeh, K., Penta, A., Leiva, L. A., & Arapakis, I. (2025). AdSight. *SIGIR '25*. https://doi.org/10.1145/3726302.3729891

[8] Maxwell, D. & Azzopardi, L. (2018). Information Scent, Searching and Stopping. *ECIR '18*, LNCS 10772, 210–222.

[9] Liu, Y. et al. (2014). From Skimming to Reading: A Two-stage Examination Model for Web Search. *CIKM '14*.

[10] Latifzadeh, K., Gwizdka, J., & Leiva, L. A. (2025). The AdSERP Dataset. *SIGIR '25*.

[11] Pirolli, P. & Card, S. (1999). Information foraging. *Psychological Review*, 106(4), 643–675.
