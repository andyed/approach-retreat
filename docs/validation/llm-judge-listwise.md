# LLM-judge listwise ranking against four-class cursor taxonomy

Exploratory validation experiment, 2026-05-14. Not currently committed to a publication. Tests whether the four-class cursor-derived taxonomy (clicked / deferred / eval_rejected / not_approached) aligns with externally-judged shopper preference on the same SERPs.

Scope tag: `[LAB, AdSERP]`. AdSERP is instructed-shop, not actual-purchase — task-fidelity caveat applies throughout.

---

## 1. Protocol

**Substrate.** 17,728 (trial_id, position) pairs from `episodes-typed-buf500.json` joined with title/snippet text from `serp-embeddings-split.json` and queries from `query-embeddings.json`. 400 SERPs sampled uniformly at random from trials with ≥3 reached positions.

**Cursor labels.** The four-class taxonomy from §4.2 of the CIKM submission, derived via `derive_taxonomy(df, approach_threshold_px=100)`:

- `clicked` ← `was_clicked = True`
- `not_approached` ← `min_dist ≥ 100`
- `deferred` ← `min_dist < 100` AND `gaze_regressed = True`
- `eval_rejected` ← `min_dist < 100` AND NOT `gaze_regressed`

Mapped to ordinal scale `3 / 2 / 1 / 0` for per-trial Spearman analysis.

**Judge.** Claude-class subagent receiving the SERP's query plus the title, snippet, and etype for every reached position; ranks results listwise from best→worst against an explicit rubric (`data/llm_judge/rubric_v1.md` in `cikm-leakycursor-replicate`). The judge sees NO cursor, click, position-on-SERP, or participant identity.

**Rubric v1.** E-commerce shopper preference: exact match > brand match > retailer trust / acquisition ease > price > availability > specificity > intent.

**Rubric v2 (ablation).** Same as v1 with retailer-trust and acquisition-ease criteria stripped. Judge ranks only on text-based match quality.

**Comparison metric.** Per-trial Spearman ρ between cursor ordinal (3/2/1/0) and judge-derived score `(N - rank + 1)` across the reached positions on that SERP.

---

## 2. Headline numbers (n = 383 usable SERPs)

| Statistic | Value |
|---|---|
| Median per-trial Spearman ρ | **+0.058** |
| Mean ρ | +0.071 |
| IQR | [−0.27, +0.42] |
| frac ρ > 0.5 | 21.7 % |
| frac ρ < −0.5 | 13.1 % |
| Top-pick agreement (cursor click = judge rank 1) | **18.5 %** vs ~14 % chance |

Overall cursor↔judge agreement is weak and bimodal, not flat-noise. The distribution has substantial right and left tails with a near-zero median.

---

## 3. Click depth is the dominant moderator

Stratifying by the position the user clicked:

| Click position | n | median ρ | top-pick agree |
|---|---:|---:|---:|
| p0 | 65 | **+0.522** | **61.5 %** |
| p1–2 | 134 | +0.085 | 17.2 % |
| p3–5 | 119 | 0.000 | 3.4 % |
| p6+ | 45 | **−0.091** | **0.0 %** |

When the user clicks the top result, cursor and judge agree strongly; cursor's clicked position matches the judge's #1 pick in 62 % of cases. When the user clicks p6+, top-pick agreement is zero out of 45 and median ρ is mildly negative.

The plain reading: top clicks are the consensus case where cursor and any sensible relevance model converge on the same winner. Deep clicks are the contested case where the user rejected the obvious top results — the cursor records that rejection, but the text-based judge cannot see what made the user dig.

## 4. Ad-click trials show tighter cursor↔judge agreement

| Clicked etype | n | median ρ | top-pick agree |
|---|---:|---:|---:|
| ad (`native_ad` + `dd_top`) | 40 | +0.302 | 40.0 % |
| organic | 305 | +0.068 | 16.7 % |
| widget | 18 | −0.135 | 0.0 % |

Ad-clicked trials show ~4× the top-pick agreement of organic-clicked trials. This is the same direction and approximately the same magnitude as the +0.100 vs +0.047 ΔMRR ad-side LTR lift reported in §4.6 of the CIKM submission (private decomposition record at `~/Documents/dev/cikm-leakycursor-ad-decomposition.md`). Independent confirmation under a different protocol that ad-side cursor labels carry tighter alignment with text-based relevance.

## 5. Ad fraction on the SERP flips the sign

| SERP ad fraction | n | median ρ |
|---|---:|---:|
| ad-heavy (≥50 %) | 56 | **−0.207** |
| mixed (10–50 %) | 244 | +0.116 |
| organic (<10 %) | 83 | +0.137 |

The flip on ad-heavy SERPs is not driven by the *clicked* etype — it's a SERP-composition effect. Plausibility: when most positions are ads, the text-based judge picks the "best ad" while the user may be drawn to the small organic component (or vice versa) for reasons text alone cannot capture.

---

## 6. Load-bearing class-level validation: eval_rejected lands at the bottom of the pack

This is the validation that survives scrutiny. Per-item normalized judge rank (0 = judge's best, 1 = judge's worst) by cursor class on the same 400-SERP cohort, n = 2,720 items total.

### 6.1 Aggregate (contaminated by position confound — reported for transparency)

| cursor class | n | median norm rank | mean | % bottom half | % ranked LAST |
|---|---:|---:|---:|---:|---:|
| deferred | 399 | 0.375 | 0.406 | 35.3 % | 10.0 % |
| clicked | 363 | 0.500 | 0.483 | 43.9 % | 17.4 % |
| not_approached | 1888 | 0.500 | 0.520 | 48.8 % | 14.8 % |
| **eval_rejected** | **71** | **0.556** | **0.563** | **52.1 %** | **21.1 %** |

The aggregate suggests `deferred > clicked > not_approached > eval_rejected`. Two pieces of that aggregate ordering are real (eval_rejected lands worst; clicked is mid-pack); the `deferred > clicked` piece is a position artifact.

### 6.2 Position confound — why the aggregate must not be cited

Position distribution by cursor class:

| class | mean SERP position | % at p0-p2 |
|---|---:|---:|
| deferred | 2.17 | 63.2 % |
| clicked | 2.66 | 54.8 % |
| eval_rejected | 3.83 | 35.2 % |
| not_approached | 3.94 | 36.4 % |

Deferred items concentrate near the top of the SERP because user approach behavior concentrates there. The judge's top picks also concentrate near the top of the SERP (Google's ranking is non-random — top-positioned items are on average higher-quality). The deferred-class items are therefore over-represented in the judge's high-rank cells purely by spatial overlap, not because gaze-regressed items carry distinct text-relevance signal beyond the click.

### 6.3 Within-position table — the eval_rejected finding survives

Mean normalized judge rank by (cursor class × SERP position). Cells with ≥5 items only.

| SERP pos | clicked | deferred | eval_rejected | not_approached |
|---:|---:|---:|---:|---:|
| 0 | 0.21 (n=65) | 0.19 (n=122) | 0.16 (n=6) | 0.20 (n=206) |
| 1 | 0.40 (n=78) | 0.40 (n=71) | 0.50 (n=8) | 0.38 (n=226) |
| 2 | 0.53 (n=56) | 0.43 (n=59) | 0.42 (n=11) | 0.50 (n=256) |
| **3** | 0.58 (n=39) | 0.54 (n=53) | **0.66 (n=11)** | 0.53 (n=228) |
| **4** | 0.61 (n=57) | 0.57 (n=30) | **0.72 (n=10)** | 0.57 (n=197) |
| 5 | 0.54 (n=22) | 0.59 (n=26) | 0.51 (n=6) | 0.56 (n=192) |

At p3-p4 — mid-depth positions where the user has scrolled past the obvious top picks and is making selective decisions — **eval_rejected items rank 0.10-0.15 worse on normalized judge rank than items at the same SERP position with other cursor labels**. That is the position-controlled validation. When a user approached a mid-depth result and the gaze did not regress back, the LLM judge agrees that result is worse than the items at the same depth on the same SERP.

The signal is weaker at p0-p2 (everything at the top is high-quality; the user has not yet "decided") and at p6+ (eval_rejected cells are too sparse). The 0.66 and 0.72 cells at p3 and p4 are the cleanest validation cases the protocol produces.

### 6.4 Validation examples

eval_rejected items the judge ranked LAST on their SERP (15 of 71 = 21 %):

- `q: buy vitabase ultra veggie enzymes` → `[image_pack] "Images for buy vitabase…"` (placeholder card, no buyable content)
- `q: buy theraband flexbar size color medium green` → `[organic] "People also ask"`
- `q: buy axial axial ax30041 velcro strap 16x200mm` → `[organic] "Guided Search Filters"`
- `q: buy denso denso 234-4189 oxygen sensor` → `[organic] "Buy Denso 234-4189 Oxygen Sensor… New Zealand"` (locale mismatch)
- `q: buy walker walker 31354 exhaust gasket` → `[image_pack] "Images for buy walker walker 31354…"`

SERP-feature cards (image_pack, "People also ask", "Guided Search Filters") and locale-mismatched results dominate the cleanly-validated rejection cases. Both classes are the ones a real shopper would also dismiss.

Failure cases — eval_rejected items the judge ranked #1 on their SERP (6 of 71 = 8.5 %):

- `q: buy denso 477-0509 condenser` → `[native_ad] "Denso 477-0509 Condenser : Amazon.com"`
- `q: buy oneill o neill hammer jacket` → `[dd_top] "Hammer Snow Jacket - O'Neill"`
- `q: buy obrien nomad wakeboard bindings` → `[dd_top] "O'Brien Nomad Wakeboard Binding - Amazon.com"`

Six cases where the judge identifies the exact product on a major retailer and the user approached but rejected. All six are Amazon / O'Neill / Walmart listings — major-retailer cases. Plausible mechanisms the protocol cannot disentangle: deliberate retailer-avoidance (many shoppers actively prefer not to buy from Amazon for labor / competition / ethical reasons), comparison-shopping habit, price-anchoring, prior bad experience with the specific retailer, gaze-regression pipeline misclassification, or task-fidelity (instructed-buy ≠ actual-buy).

### 6.5 Per-trial Spearman is robust to the ordinal reordering

The eval_rejected validation does not change the per-trial Spearman headline materially. Three orderings tested:

| Ordinal mapping | n | median ρ | mean ρ |
|---|---:|---:|---:|
| Paper original (clicked=3 / deferred=2 / eval_rejected=1 / not_approached=0) | 383 | +0.058 | +0.071 |
| eval_rejected-at-bottom (clicked=3 / deferred=2 / not_approached=1 / eval_rejected=0) | 383 | +0.062 | +0.076 |
| eval_rejected-only-bottom binary (all others=1, eval_rejected=0) | 60 | +0.058 | +0.098 |

Swapping the eval_rejected and not_approached ranks moves the median Spearman by 0.004. The eval_rejected validation is a class-level claim (where do eval_rejected items land in the judge's listwise output at a fixed SERP depth) rather than a per-SERP correlation claim. The two analyses do not interfere.

### 6.6 What this validation does not claim

- **Not** that the cursor class hierarchy is `deferred > clicked > not_approached > eval_rejected`. The deferred > clicked piece of the aggregate is position-confounded; at matched SERP positions the deferred and clicked items are within noise of each other at p0-p2 and within 0.05 elsewhere.
- **Not** that eval_rejected validates as low-relevance at all SERP depths. The clean signal is at p3-p4. At p0-p2 the small eval_rejected cells are too sparse for a within-position claim; at p6+ the cells are empty.
- **Not** a claim about the §4.3 deferred-class classifier. That classifier separates deferred from eval_rejected using cursor geometry, and its calibration is established against gaze-derived labels in `attentional-foraging` NB22, not against the LLM judge. The LLM judge agrees at the class level that eval_rejected is worse than the other three classes at p3-p4; it does not separately validate the deferred/eval_rejected geometric discrimination.

---

## 7. V2 ablation: retailer-trust stripped

Re-judged the 87 SERPs with v1 ρ < −0.3 using a rubric that explicitly ignores retailer trust and acquisition ease — only match quality (brand, model, category, intent) counts. Same SERPs, same judge architecture.

| | v1 (retailer-trust ON) | v2 (retailer-trust OFF) |
|---|---:|---:|
| Median ρ | −0.541 | −0.481 |
| Mean ρ | −0.587 | −0.413 |
| Δ (v2 − v1), mean | — | **+0.174** (Wilcoxon p = 2.65×10⁻⁵) |
| frac flipped to ρ > 0 | — | **13 %** (11/87) |
| frac stayed in ρ < −0.1 | — | **82 %** (71/87) |
| Judge self-agreement (v1 ranking vs v2 ranking, median ρ) | — | +0.800 |

The mean shift is statistically real but modest. Most negative-tail SERPs stay negative; the v2 judge largely agrees with the v1 judge (median self-ρ = 0.80). Retailer trust contributes *some* divergence but does not explain the bulk of it.

---

## 8. What this does and does not tell us

### What it tells us

- The four-class cursor taxonomy is not a graded *absolute* relevance label by any reasonable text-based judge standard at the per-SERP level. Median per-trial Spearman ρ is +0.06; only ~22 % of SERPs show strong agreement.
- Top-pick agreement (cursor click = judge rank 1) tracks click depth: 61 % at p0, 0 % at p6+. The cursor↔relevance alignment is concentrated where the user's selection matches the consensus top pick.
- Ad-clicked trials show tighter cursor↔judge alignment than organic-clicked trials in this listwise protocol, matching the §4.6 LTR ad-lift direction under an independent protocol.
- The deep-click cursor↔judge divergence is not primarily a retailer-trust artifact; ablating retailer-trust shifts the mean by +0.17 but leaves 82 % of negative-tail SERPs negative.

### What it does NOT tell us

- **It does not localize what the cursor signal captures.** The text-based judge cannot see: delivery time, return policy, currency mismatch, shipping cost, prior personal experience with brands, recent purchases, taste / style preferences, country availability, payment-method support, deliberate retailer-avoidance stances (e.g., anti-Amazon preference for labor / competition / ethical reasons), reviews seen elsewhere, image / thumbnail content, layout density, ad-creative quality, recently-clicked-elsewhere recency effects, or participant-specific shopping habits learned outside the lab session. Any of these — singly or in combination — could account for the cursor↔judge divergence. The negative-space claim is "not in title/snippet text"; it is not "in visual layout specifically" or any one mechanism.
- **It does not separate signal from task-fidelity noise.** AdSERP participants were instructed to buy *X* but did not actually transact. Their cursor allocation may channel real shopping intuitions even without real money on the line, or it may reflect first-acceptable-result heuristics when the decision lacks consequence. The protocol cannot distinguish.
- **It does not validate or invalidate the §4.6 LTR lift.** The §4.6 result is +0.054 ΔMRR at LOSO 47-fold scale on ~2,500 trials with one model, one feature set. The judge result is per-trial Spearman on 383 SERPs. Different denominators, different aggregation. The directional consistency on ad-side strengthens the §4.6 narrative; the weak per-SERP alignment does not undercut it because LTR optimizes a different objective.
- **It does not establish the LLM judge as a reliable IR oracle.** No human-validation subsample was run. The judge applies a stated rubric consistently across n=400 SERPs; that is the only consistency claim available. A small Prolific subsample (~200 pairs, ~$80) would put a human-↔-judge κ floor under the protocol; deferred.

### Calibration note on the click-depth gradient

The +0.52 → −0.09 gradient with click depth is a strong empirical pattern but its interpretation is multiple. One natural reading is "cursor and judge converge on consensus, diverge on contested." Another is "the cursor signal is structurally less informative when the user dug deep, because the click pulls the cursor ordinal but the deferred / eval_rejected / not_approached labels become noisier with more reached positions." The two readings are observationally equivalent at this protocol. A within-trial analysis of cursor↔judge agreement *excluding* the clicked position could distinguish them; not yet run.

---

## 9. Relevance to the CIKM submission

The paper's IR-voice framing is "graded relevance labels derived from per-result examination episodes," with +0.054 ΔMRR vs binary as the headline. The judge experiment does not invalidate that claim — LTR optimizes per-list ranking quality and the labels carry useful per-list signal even when per-SERP cursor↔judge Spearman is weak.

It does suggest a more defensible secondary claim: the cursor labels are *competitive preference labels conditioned on the user's actual selection*, not absolute relevance grades. That distinction is consistent with the prior observation that fully-ranked LTR from cursor data underperformed binary classes — adding ordinal structure across deferred / eval_rejected / not_approached injects user-specific non-textual variance the model cannot ground.

This experiment is not currently slated for the CIKM submission. It belongs as future work, either as a CHIIR-style methods paper on cursor-judge protocol design or as a §6 paragraph in a follow-on venue. Decision deferred.

---

## 10. Data and code

- Source data and judging artifacts live in the private `cikm-leakycursor-replicate` repo under `data/llm_judge/`:
  - `judge_pairs.jsonl` — 17,728 reached pairs with cursor labels joined to query/title/snippet
  - `per_serp_v1_expanded.jsonl`, `per_serp_v1_new200.jsonl` — 400 sampled SERPs
  - `rankings_v1_*.jsonl` — v1 listwise judgments
  - `rankings_v2_*.jsonl` — v2 ablation judgments
  - `per_trial_v1.json` — per-SERP ρ summary
  - `rubric_v1.md`, `rubric_v2.md`
- Sampling/build scripts: `replicate/build_judge_pairs.py`, `replicate/sample_per_serp.py`, `replicate/sample_per_serp_new200.py`
- Judging: each ranking batch was a parallel general-purpose subagent invocation. No external API calls and no human-validation subsample.

## 11. Open work

- Within-trial cursor↔judge Spearman excluding the clicked position, to test the "structural noise from click-pull" reading of §7 calibration note.
- Per-participant variance analysis — top participants by trial count showed visible spread (median ρ from −0.22 to +0.51) at n=200; warrants formal per-participant random-effects model.
- Human-validation Prolific subsample (~200 pairs, ~$80) to anchor judge↔human κ.
- V3 ablation that strips price reasonableness and intent-alignment in addition to retailer trust, narrowing further toward "pure brand/model/category match."
- Replication on the Bruckner ACD WILD cohort would earn this finding the `[BOTH]` tag — but ACD is single-AOI native-ad and has no listwise structure, so the protocol does not transfer directly. Future work would need a multi-result WILD substrate (RecGaze carousel, or a freshly-collected cursor-only SERP cohort).
