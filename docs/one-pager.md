# Cursor Behavior on SERPs: A Task Model Beats a Bag of Features

**One-pager — Edmonds, 2026-04-08**

## The bag-of-features status quo

Fifteen years of cursor-on-SERP research has converged on a single methodological pattern: extract many features from cursor traces, train a model. The features are mostly aggregate statistics over the full trial (mean velocity, total distance, direction changes, hover counts) or fine-grained temporal embeddings fed to a neural net.

| Work | Approach | Features | Best result |
|---|---|---|---|
| Edmonds (BRMIC '03; JWE '07) [11, 12] | Instrumented browser; integrated path length ("mouse miles"), DOM-path click signature (extended to AJAX pages in '07), cursor-vector compression | 3 primitives | Usability case study — mouse miles + horizontal/vertical decomposition distinguished left vs. right nav layouts |
| Guo & Agichtein (WWW '12) [1] | Hand-crafted features over post-click cursor traces | ~12 | Improved relevance estimation over dwell time alone |
| Huang, White & Buscher (CHI '12) [2] | Cursor as gaze proxy on SERPs (700 ms lag, 59% of cursor time is "inactive") | 5 cursor behavior categories | Cursor approximates gaze poorly more than half the time |
| Arapakis & Leiva (SIGIR '16) [3] | Engagement prediction from cursor on SERP elements | **638** features | AUC 0.86 |
| Brückner, Arapakis & Leiva (SIGIR '21) [4] | Mouse movement length for choice on SERPs | Scalar feature, multiple decision states | Discriminates ad notice, abandonment, frustration |
| Villaizán-Vallelado et al., AdSight (SIGIR '25) [5] | Seq2Seq Transformer on cursor trajectory embeddings | Time-series + slot metadata | TFT MSE 2.86, NDCG 96.07 |

This trajectory has reached the modern endpoint: a Transformer that takes raw cursor sequences and predicts gaze. The implicit assumption is that more features and bigger models will keep extracting signal until the fixation budget is recovered from the cursor budget.

But none of this work has a model of the *task*. The cursor is treated as a stream of low-level kinematic events, and the question is which statistical compression best predicts which downstream label. The cognitive process generating the cursor is opaque.

## What a task model contributes

A task model says: SERP browsing is not a kinematic stream. It is a sequence of discrete cognitive episodes — the user *orients* to the page, *surveys* the candidate set, *evaluates* individual results, then *commits* to one (or abandons, or re-evaluates). Each episode has a measurable signature in cursor behavior, and the boundaries between episodes are where the interesting decisions happen.

The OSEC framework (Orientation → Survey → Evaluate → Commit) reframes the cursor not as a feature stream but as a sequence of *episodes* attached to specific results. From this reframe, six cursor features and a per-result episode segmentation recover signal that the bag-of-features approach finds with hundreds of features or with a neural net.

### What the AdSERP reanalysis [6] showed

- **Four-class taxonomy.** Where click models treat outcomes as binary (clicked / not clicked), episode segmentation reveals four behaviorally distinct cursor outcomes per result: **clicked**, **deferred** (cursor entered, retreated, returned later), **evaluated-rejected** (cursor entered and didn't return), and **not-approached** (cursor never entered the AOI). All four are recoverable from cursor telemetry alone (no eye tracker). NB22 click prediction **AUC 0.859** with no element-type features; with interactions (M3ei): organic **0.859**, top ads **0.919** (+0.010), native ads **0.817** (post coordinate-space audit 2026-04-12).
- **Discrimination cost (NB20).** Top-of-page sponsored results show a distinctive cursor signature compared to organic results at the same positions: 2× approach rate (42.9% vs 21.0%), 2.3× longer dwell in proximity for clicked results (4,586 vs 2,023 ms), and the highest pupil dilation of any element class (+0.41% over baseline). Native ads, by contrast, show *avoidance* — lowest approach rate (17.5%), lowest click rate (8.0%). The cost driving the top-ad signature is *discrimination* ("is this an ad or a real result?"), not reading difficulty. This is invisible to position-based click models.
- **C/W/L cost violation.** Azzopardi, Thomas & Craswell's economic SERP utility framework (SIGIR '18) [7] predicts ads cost less to evaluate than organic results because they have less content. The data show the opposite for top ads: they cost *more* than organic results at the same positions because they require type identification before evaluation. C/W/L is missing a discrimination cost term for elements requiring category resolution.
- **Retreat geometry as deliberation indicator (NB24 v2).** When the user evaluates a result and retreats, the geometry of the retreat trajectory predicts whether they will come back. Three features — arc ratio (path length / direct distance), max retreat distance, and Fitts' law ID at max retreat — discriminate deferred from rejected episodes (Mann-Whitney p < 10⁻³ on N = 731 retreats, AdSERP). Pattern: **curved + close = "I'll be back"; straight + far = "I'm done."** This is a continuous deliberation/commitment signal usable as a within-class feature for the deferred-vs-rejected boundary in the four-class taxonomy. (We initially proposed a Kirsh & Maglio "epistemic action / motor cost as working memory offloading" interpretation; the data did not support it and we rejected it.)

## Why the task model is doing the work

The same cursor data, the same dataset, the same instrumentation. The bag-of-features approach finds correlations and aggregate statistics; the task-model approach finds *behaviorally meaningful classes and continuous within-class signals*. Three concrete contributions:

1. **The four-class taxonomy gives ML rankers better negatives.** Click logs treat every non-clicked result as an undifferentiated negative — even when the user clearly evaluated and rejected it, and even when the user never looked at it. Both end up as 0 in the training label, and the ranker learns from the noise. Episode segmentation splits "not clicked" into three behaviorally distinct classes: **evaluated-rejected** (strong negative — the user looked, considered, said no), **deferred** (weak negative or hold-out — the user is still considering and may come back), and **not-approached** (unknown, not a negative — the user never looked, so the result could be relevant or not). A learning-to-rank model trained on this taxonomy gets cleaner gradients than one trained on binary clicks. This is the practical payoff — not adaptive reranking on the deployed page, but training-data quality for whatever ranker is consuming the click logs.
2. **Discrimination cost is invisible to position-only models.** Click models that condition on rank position assume cost is a function of position. Top ads at position 0 should be the cheapest to evaluate by that logic. The cursor signature shows they are the most expensive, because the cost is *type identification*, not *position*. C/W/L can be patched with a discrimination term once you know to look for it. You only know to look for it if you have a process model that asks "what is the user actually doing in front of this element?"
3. **Retreat geometry is invisible to scalar-length features.** Brückner et al. (SIGIR '21) used total mouse movement length as a decision signal — the same primitive that Edmonds (2003) [11] reported as "mouse miles" in the Uzilla instrumented browser, with horizontal/vertical decomposition, 18 years earlier. Length tells you the user moved a lot; it does not tell you whether the movement was straight or curved, far or close. The same 400-pixel retreat can be a confident commitment to rejection (straight, far, high Fitts ID) or unresolved deliberation (curved, close, low Fitts ID). The geometry is the within-class signal that 638 features and a Transformer both miss because neither was looking for *episode shape*.

## The deployment story

The task model is also what makes this deployable without an eye tracker. AdSight's Seq2Seq Transformer needs a Transformer at inference time and is trained against ground-truth gaze data from a 47-participant lab study. The four-class taxonomy + retreat geometry features are computed in JavaScript with two event listeners (`mousemove`, `click`) and a small ring buffer.

Two libraries split the work along architectural lines, not phase lines:

- **`approach-retreat`** [8] is *list-aware*. The host page marks vertical SERP-list items with `data-result` and `data-position` attributes; the library uses those AOIs as the unit of analysis (enter/dwell/exit episodes per result, four-class outcome per result, retreat geometry against a known result rectangle). Without the marked cells, none of the episode segmentation works.
- **`clicksense`** [9] is *element-agnostic*. It instruments any clickable target on any page. Its approach features (`approach_linearity`, `approach_max_deviation`, `approach_trajectory_type`) are geometric invariants of the cursor trajectory itself, computed against the implicit point target of the eventual mousedown. No markup, no AOIs, no list structure required.

The two are complementary because they answer different questions on the same cursor stream. ClickSense answers "how was this click made?" — the geometry of the commitment, target-agnostic. approach-retreat answers "what was the user doing across this list?" — the episode structure on a known set of candidates. Both ship as standalone JS modules with vendor-agnostic adapters.

The point is not that bigger models are wrong. The point is that bigger models tell you *what* the cursor is doing while a task model tells you *why*. When you have the why, six features are enough — and the markup is what makes the why available.

## What this is not

This is not a claim that the task model approach replaces the ML approach. The two are complementary: a Transformer trained on the four-class taxonomy as labels (instead of binary click) would likely outperform either approach alone. The four classes are a target the bag-of-features approach has not been computing because nobody framed the problem that way.

This is also not a claim that the task-model features are universally better. Arapakis & Leiva's 638 features extract real signal. AdSight's Transformer extracts more. The task model adds a *layer of interpretation* that turns the signal into actionable categories — and it does so cheaply, without ground-truth gaze.

---

## References

[1] Guo, Q. & Agichtein, E. (2012). Beyond dwell time: estimating document relevance from cursor movements and other post-click searcher behavior. *WWW '12*, 569–578. https://dl.acm.org/doi/10.1145/2187836.2187914

[2] Huang, J., White, R. W., & Buscher, G. (2012). User see, user point: gaze and cursor alignment in web search. *CHI '12*. https://dl.acm.org/doi/10.1145/2207676.2208591

[3] Arapakis, I. & Leiva, L. A. (2016). Predicting User Engagement with Direct Displays Using Mouse Cursor Information. *SIGIR '16*, 599–608. https://dl.acm.org/doi/10.1145/2911451.2911505

[4] Brückner, L., Arapakis, I., & Leiva, L. A. (2021). When Choice Happens: A Systematic Examination of Mouse Movement Length for Decision Making in Web Search. *SIGIR '21*, 1510–1514. https://dl.acm.org/doi/10.1145/3404835.3463088

[5] Villaizán-Vallelado, M., Salvatori, M., Latifzadeh, K., Penta, A., Leiva, L. A., & Arapakis, I. (2025). AdSight: Predicting Visual Attention on Sponsored Search Engine Result Pages. *SIGIR '25*. https://doi.org/10.1145/3726302.3729891

[6] Latifzadeh, K., Gwizdka, J., & Leiva, L. A. (2025). The AdSERP Dataset: Eye-Tracking, Mouse, and Pupil Data on Heterogeneous SERPs. *SIGIR '25*.

[7] Azzopardi, L., Thomas, P., & Craswell, N. (2018). Measuring the Utility of Search Engine Result Pages: An Information Foraging Based Measure. *SIGIR '18*, 605–614. https://doi.org/10.1145/3209978.3210027

[8] Edmonds, A. (2026). approach-retreat: cursor approach-retreat dynamics on search result pages. https://github.com/andyed/approach-retreat

[9] Edmonds, A. (2026). ClickSense: click confidence measurement from motor behavior. https://github.com/andyed/clicksense

[10] Leiva, L. A. & Arapakis, I. (2020). The Attentive Cursor Dataset. *Frontiers in Human Neuroscience*, 14:565664. https://doi.org/10.3389/fnhum.2020.565664

[11] Edmonds, A. (2003). Uzilla: A new tool for Web usability testing. *Behavior Research Methods, Instruments, & Computers*, 35(2), 194–201. Psychonomic Society. ISSN 0743-3808.

[12] Edmonds, A., White, R. W., Morris, D., & Drucker, S. M. (2007). Instrumenting the Dynamic Web. *Journal of Web Engineering*, 6(3), 244–260. Rinton Press.
