# CIKM 2026 — Approach-Retreat: A Task Model for Cursor Evaluation Behavior on SERPs

**Authors:** Andy Edmonds, Leif Azzopardi, Peter Dixon-Moses
**Target:** CIKM 2026 (abstract submission ~May 2026)

## The Gap

Fifteen years of cursor-on-SERP research treats cursor data as a feature vector to decode. Nobody has asked what cognitive operation the cursor is performing.

| Paper | What they did | What they missed |
|-------|--------------|-----------------|
| Huang, White & Buscher (2012) | Gaze-cursor alignment, 5 behavior classes, 700 ms lag | "Inactive" (59% of time) is undifferentiated — our taxonomy splits it into three classes |
| Guo & Agichtein (2012) | Post-click cursor → document relevance | Post-click only, not evaluation on the SERP itself |
| Arapakis & Leiva (2016) | 638 features → AUC 0.86 attention prediction | Brute-force feature engineering; distance-to-element dominates — retreat distance by another name |
| Leiva & Arapakis (2020) | 2,737-user cursor dataset with attention labels | Dataset, not a model. No taxonomy of cursor behavior |

**Common thread:** All treat cursor as signal. None ask why the cursor moves where it does. The IR community has the data. Cognitive psychology has the task model. This paper bridges them.

## Core Contribution: A Task Model, Not a Feature Set

The OSEC model (Orientation → Survey → Evaluate → Commit) maps cursor behavior to cognitive operations:

1. **Orientation** (first 200 ms) — layout parsing, ad identification
2. **Survey** — broad scanning, information scent estimation (wide saccades, cursor inactive or trailing)
3. **Evaluate** — per-result evaluation episodes (cursor enters AOI, dwells, exits)
4. **Commit** — click or final rejection

The evaluate phase produces the four-class taxonomy — the practical contribution:

| Class | Cursor behavior | Cognitive operation |
|-------|----------------|-------------------|
| **Clicked** | Enter → dwell → click | Evaluation → commitment |
| **Deferred** | Enter → retreat → re-approach | Evaluation → held in consideration set |
| **Evaluated-rejected** | Enter → retreat (no return) | Evaluation → priced out |
| **Not-approached** | Visible, never entered | Below information scent threshold |

### Why splitting non-clicks matters

Click models (including C/W/L) treat all non-clicks as one class. But "I looked at this and rejected it" carries different information than "I never looked at it." Splitting non-clicks:
- Improves click prediction (AUC 0.821 → 0.838 with element-type interactions)
- Reveals discrimination cost invisible to click-only models
- Recoverable from cursor telemetry alone (F1 0.70 and 0.66 for split classes)

## Retreat as Epistemic Action

The key theoretical insight: cursor retreat is not noise or failed approach. It is an epistemic action (Kirsh & Maglio, 1994).

Epistemic actions modify the external environment to reduce internal cognitive load. Georgia Tech's studies of short-order cooks at the Majestic Diner showed that cooks arranged silverware and turned plates to encode dish state — externalizing working memory into physical space.

Cursor retreat does the same thing: moving away from a result increases the motor cost of returning. The user is physically encoding their rejection confidence into motor space. The retreat distance IS the evaluation — not a byproduct of it.

- Short retreat (still near AOI) → low confidence rejection → DEFERRED
- Long retreat (far from AOI) → high confidence rejection → EVALUATED_REJECTED
- No approach at all → below scent threshold → NOT_APPROACHED

This is what a cognitive psychologist sees that the IR feature engineers missed: the cursor position is a running confidence estimate externalized into motor behavior.

## C/W/L Violation on Ads

The C/W/L click framework (Azzopardi et al.) predicts that user cost decreases with position — lower results cost less to evaluate. This holds for organic results but breaks for top ads:

- Top ads: 2x approach rate, +50px retreat distance, 2.3x dwell, highest pupil dilation (+0.41%)
- The cost isn't reading difficulty — it's **discrimination cost** ("is this an ad or a result?")
- Adding retreat × is_top_ad interaction: AUC 0.884 → 0.914
- Native ads behave as C/W/L predicts: lowest approach rate (17.5%), shortest dwell, fast dismissal

**Implication:** C/W/L needs a discrimination cost term for elements that require type identification before evaluation.

## Datasets

### Primary: AdSERP (Latifzadeh, Gwizdka & Leiva, SIGIR 2025)
- 2,776 SERP trials, 47 participants
- Simultaneous eye tracking + mouse tracking + pupil dilation
- Gaze validates cursor-as-proxy; pupil validates cognitive load

### Validation: The Attentive Cursor Dataset (Leiva & Arapakis, 2020)
- 2,737 users, cursor traces + self-reported attention (1-5 Likert) + SERP HTML
- Public: https://gitlab.com/iarapakis/the-attentive-cursor-dataset
- Validates four-class taxonomy against subjective attention at scale

## The Speed-of-Science Theme

This paper blends:
- **Pupillometry** (Duchowski's LHIPA/Butterworth LF-HF) — best cognitive load metric from eye tracking
- **Cursor dynamics** (Huang, Arapakis, Leiva) — best implicit signal from mouse telemetry
- **Cognitive task modeling** (OSEC) — the framework that explains WHY these signals work

Each discipline built excellent instruments. Nobody combined them with a task model that explains the signals. The combination is more than additive: pupil validates what cursor measures, cursor operationalizes what the task model predicts, the task model explains what pupil and cursor observe.

## Paper Structure

1. **Introduction** — the feature engineering gap (15 years of cursor-on-SERP, no task model)
2. **Related work** — Huang '12, Guo '12, Arapakis '16, Leiva '20, C/W/L, Kirsh & Maglio
3. **The OSEC task model** — orientation, survey, evaluate, commit
4. **Four-class taxonomy** — definitions, decision boundaries, epistemic action framing
5. **Method** — AdSERP dataset, episode extraction, classification
6. **Results** — taxonomy validation, C/W/L violation, discrimination cost
7. **Validation** — Attentive Cursor Dataset replication (if timeline permits)
8. **Discussion** — retreat distance as deployable signal, implications for click models
9. **Library** — approach-retreat as open-source implementation (https://github.com/andyed/approach-retreat)

## Open Questions

- [ ] Can we get Attentive Cursor validation done before submission?
- [ ] Do we need IRB for the gh-pages experiment, or is anonymous cursor tracking exempt?
- [ ] Azzopardi's role: co-author vs. acknowledged? (C/W/L violation is central)
- [ ] Dixon-Moses: practical utility framing — how does this deploy in production search?

## Key Claims to Defend

1. The four-class taxonomy is recoverable from cursor telemetry alone (no gaze needed)
2. Retreat distance is an epistemic action, not noise
3. C/W/L's cost assumption breaks for elements requiring type discrimination
4. 638 features compress to ~6 when you have the task model
5. The combination of pupil + cursor + task model is more than additive
