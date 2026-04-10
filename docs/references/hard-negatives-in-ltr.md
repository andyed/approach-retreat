# Hard negatives in learning-to-rank — and why approach-retreat is a new source of them

**Topic:** behavioral hard-negative mining for dense retrieval and learning-to-rank
**Last updated:** 2026-04-09
**Audience:** anyone evaluating whether the four-class approach-retreat taxonomy (clicked / deferred / evaluated-rejected / not-approached) belongs in an IR pipeline

## Why this note exists

The IR literature since ~2020 has been explicit and consistent that **the quality of negative training examples is the bottleneck on dense-retrieval performance**, and the last five years of research has been a progression of increasingly sophisticated ways to mine them. Random negatives leave most of the gradient signal on the table. BM25-based "hard" negatives improve on random but can hurt recall if used statically. Iteratively refreshed hard negatives (ANCE) improve further but require periodic corpus re-indexing. Cross-encoder-denoised hard negatives (RocketQA) improve again but introduce a separate filtering stage to catch false negatives.

The `approach-retreat` library extracts a behaviorally-verified hard-negative label from cursor telemetry — the **evaluated-rejected** class. This note maps the four-class taxonomy onto the modern hard-negative mining literature and argues that the behavioral signal sidesteps two of the literature's worst failure modes by construction.

## The four load-bearing findings from the literature

### 1. Random negatives leave most of the signal on the table

ANCE — Xiong et al., ICLR 2021 — frames the problem in theoretical terms: *"the bottleneck of dense retrieval is the domination of uninformative negatives sampled in mini-batch training, which yield diminishing gradient norms, large gradient variances, and slow convergence."* Random negatives are almost always trivially non-relevant; once the model has learned basic topicality, additional random negatives contribute almost nothing to gradients. ANCE's fix is to globally re-mine hard negatives from the entire corpus every ~10k training steps using the current model's index. Their theoretical claim is that this approximates an oracle importance-sampling procedure that random sampling cannot match.

**Takeaway for approach-retreat:** the value of a hard negative is not that it is non-relevant, but that the model is currently *uncertain* about whether it is relevant. The model needs negative training signal at its current decision boundary. Whether you get those negatives from BM25, from the model's own embeddings, or from cursor telemetry, the gradient story is the same.

### 2. "Just pick the BM25 top results" is not enough — and can hurt recall

This is the finding that makes the approach-retreat contribution non-trivial, and it is not the textbook version of "hard negatives good."

Zhan et al., SIGIR 2021 — *"Optimizing Dense Retrieval Model Training with Hard Negatives"* (the ADORE / STAR paper) — explicitly shows that **static BM25 hard negatives almost underperform random negatives on every metric** in their experimental setup. From their analysis: *"static hard negative sampling does not necessarily lead to performance improvements compared with random negative sampling. It improves the top-ranking performance but may harm the recall capability."* The value comes from dynamically updating the hard-negative set as the model improves — not from the mere "hardness" of the training candidates.

**The implication is uncomfortable for naive hard-negative mining:** the *quality of the labeling procedure* matters more than the *hardness of the candidates*. A source of hard negatives that systematically misses true-positive items can actively harm a dense retriever. Hardness is necessary but nowhere near sufficient.

### 3. False negatives are a real failure mode, not a theoretical one

RocketQA — Qu et al., NAACL 2021 — directly addresses the false-negative problem with **denoised hard negatives**: filter the mined hard-negative pool using a stronger cross-encoder to remove candidates the cross-encoder scores as plausibly relevant. The denoising is load-bearing — RocketQA's contribution depends on the filter, not just on the mining of hard candidates. This empirically validates the concern that items which look like hard negatives in BM25 or in the current retriever's embedding space can be latent positives, and training on them pushes the model in the wrong direction.

The failure mode is concrete: the user's true relevance label is unobserved, the mining procedure picks candidates the model is currently uncertain about, and uncertainty correlates with the model not yet having seen evidence of relevance — which is exactly what you would expect for a latent positive. Denoising tries to correct for this.

### 4. DPR (Karpukhin et al., EMNLP 2020) — the baseline everyone compares against

The dense-retrieval workhorse paper. Used **in-batch negatives + BM25 hard negatives** as its canonical training scheme, and the ablation table showed both contribute. DPR became state-of-the-art on open-domain QA at the time and is the baseline every subsequent hard-negative paper is benchmarked against. Historically the paper that established "hard negative mining + in-batch = the recipe" as the default.

### The behavioral-data precedent: Joachims et al. 2005

**Joachims et al., CIKM 2005 — *Accurately Interpreting Clickthrough Data as Implicit Feedback*** — established the foundational behavioral move: **skipped results above a click are implicit negatives.** If the user clicked position 4, positions 1–3 are inferred to have been seen, evaluated, and rejected. This skip-above heuristic has been the dominant way to extract hard negatives from query logs for two decades.

**The limitation of skip-above:** it infers "evaluated and rejected" from click position, not from observable behavior. A result the user skipped might have been genuinely considered and declined, or it might have been a total fly-by that never reached any depth of evaluation. Skip-above cannot distinguish those two cases. The approach-retreat motor signature can.

## What this means for the four-class taxonomy

The four classes — *clicked / deferred / evaluated-rejected / not-approached* — are not just a convenient post-hoc partition of non-click outcomes. They are a **behaviorally-verified hard-negative labeling scheme**, and they sidestep two of the modern hard-negative mining literature's worst failure modes by construction:

### Failure mode 1: false-negative risk (the RocketQA problem)

**Standard mining:** items that look like hard negatives in BM25 or in the current retriever's embedding space can be latent positives. RocketQA introduced cross-encoder-based denoising as a separate filtering stage to catch these.

**Approach-retreat:** an episode classified as `evaluated_rejected` requires the cursor to have measurably approached the result, dwelled in proximity, *and then retreated*. This is behavioral evidence of active rejection — not a model-inferred guess. A user who actively pulled the cursor away from a result is much less likely to be a latent positive than a candidate the current model is merely uncertain about. The behavioral signal does denoising-by-construction.

### Failure mode 2: mining-procedure dependence (the ANCE / Zhan et al. problem)

**Standard mining:** hard-negative quality depends on the mining procedure being kept current. ANCE re-mines globally every ~10k steps; without re-mining, the negatives go stale as the model improves and the static set drops back toward random. This is expensive (full corpus re-indexing) and has tunable parameters that affect recall.

**Approach-retreat:** the labels come from the user, not the model. They do not go stale as the retriever improves. There is no re-indexing loop. The hard-negative set is collected at inference time (user visits SERP, cursor leaves a signature, episode is emitted) and scales with deployment traffic rather than with training compute. Each labeled episode is also paired with the trial's full evaluation context (which other results were considered, what the deferred set looked like), so the training data is richer than a flat list of (query, negative) pairs.

### What the literature is missing that approach-retreat supplies

A behaviorally-verified, deployment-scalable, denoising-by-construction source of hard negatives that does not require iterative model updates or cross-encoder filtering. The IR literature has not had this — the closest precedent is Joachims 2005's skip-above heuristic, which infers rejection from click position rather than observing rejection from cursor behavior.

The CIKM 2026 contribution is therefore not just *"we introduce a four-class taxonomy of non-click outcomes"* but *"we introduce a behaviorally-verified source of hard negatives for dense retrieval and learning-to-rank, complementary to BM25-based and model-based mining, addressing the false-negative and re-indexing failure modes by construction."* The first framing is interesting to HCI researchers; the second is a contribution the IR field has an established literature to receive.

## Citations

| Paper | Venue | Why cite |
|---|---|---|
| Karpukhin, V., Oğuz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D. & Yih, W.-t. **Dense Passage Retrieval for Open-Domain Question Answering.** | EMNLP 2020 | Baseline every subsequent hard-negative paper is compared against. Established "in-batch + BM25 hard" as the default recipe. |
| Xiong, L., Xiong, C., Li, Y., Tang, K.-F., Liu, J., Bennett, P., Ahmed, J. & Overwijk, A. **Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval (ANCE).** | ICLR 2021 | Theoretical argument that uninformative negatives dominate mini-batch gradients. The "hard negatives matter" headline. |
| Zhan, J., Mao, J., Liu, Y., Guo, J., Zhang, M. & Ma, S. **Optimizing Dense Retrieval Model Training with Hard Negatives.** | SIGIR 2021 | Crucial nuance: static hard negatives ≠ automatically better. Mining procedure matters. The finding that makes a behavioral hard-negative source genuinely valuable. |
| Qu, Y., Ding, Y., Liu, J., Liu, K., Ren, R., Zhao, W. X., Dong, D., Wu, H. & Wang, H. **RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering.** | NAACL 2021 | False negatives in mined hard-negative pools are a real failure mode. Cross-encoder denoising is the standard fix. Approach-retreat addresses by construction. |
| Joachims, T., Granka, L., Pan, B., Hembrooke, H. & Gay, G. **Accurately Interpreting Clickthrough Data as Implicit Feedback.** | SIGIR 2005 | Foundational behavioral hard-negative extraction (skip-above). Closest precedent to approach-retreat's evaluated-rejected class — but from click position, not cursor behavior. |

### Links

- ANCE — [ICLR 2021 poster](https://iclr.cc/virtual/2021/poster/2673) · [OpenReview](https://openreview.net/forum?id=zeFrfgyZln)
- DPR — [ACL Anthology](https://aclanthology.org/2020.emnlp-main.550.pdf) · [arXiv 2004.04906](https://arxiv.org/abs/2004.04906)
- Zhan et al. — [arXiv 2104.08051](https://arxiv.org/abs/2104.08051)
- RocketQA — [ACL Anthology](https://aclanthology.org/2021.naacl-main.466/) · [arXiv 2010.08191](https://arxiv.org/abs/2010.08191)
- Joachims et al. — already in the sister `attentional-foraging/references.bib` as `joachims2005clickthrough`

### Related but not chased here

- Hofstätter et al. SIGIR 2021 — TAS-B (balanced topic-aware sampling)
- Lin, Nogueira & Yates 2021 — *Pretrained Transformers for Text Ranking* (comprehensive survey)
- Ren et al. EMNLP 2021 — RocketQAv2 joint training
- Negative Sampling Techniques in Information Retrieval: A Survey (2026, [arXiv 2603.18005](https://arxiv.org/html/2603.18005)) — recent survey covering the post-2021 literature
- Rajapakse 2024 — Negative Sampling Techniques for Dense Passage Retrieval ([UvA preprint](https://staff.fnwi.uva.nl/m.derijke/wp-content/papercite-data/pdf/rajapakse-2024-study.pdf))
