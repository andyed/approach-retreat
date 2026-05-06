# AdSight (Villaizán-Vallelado et al., SIGIR '25)

**Paper:** Villaizán-Vallelado, Salvatori, Latifzadeh, Penta, Leiva & Arapakis. "AdSight: Scalable and Accurate Quantification of User Attention in Multi-Slot Sponsored Search."
**DOI:** [10.1145/3726302.3729891](https://doi.org/10.1145/3726302.3729891)
**arxiv:** 2505.01451v2

## Local copies (do not re-download)

- `~/Documents/dev/attentional-foraging/docs/lit-notes/adsight-2505.01451v2.pdf` — canonical, alongside the lit-note
- `~/Documents/dev/clicksense/docs/2505.01451v2.pdf`
- `~/Downloads/2505.01451v2.pdf`

## Detailed key claims

See `~/Documents/dev/attentional-foraging/docs/lit-notes/adsight-key-claims.md` for the full claim-by-claim breakdown (architecture, performance numbers, ablations, what they don't model).

## Relevance to approach-retreat

AdSight uses the same AdSERP corpus (47 × 2,776) we work on. They predict per-slot fixation time/count from cursor trajectories with a Transformer Seq2Seq + cursor-trajectory embeddings + N=3 auxiliary slots. AR's per-AOI episode geometry is a complementary, lightweight feature primitive on the same data. Their slot taxonomy is 4-bucket (direct-top, direct-right, organic-top, organic-bottom); ours is per-element via `typed_gapfill`.
