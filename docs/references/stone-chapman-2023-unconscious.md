# Stone & Chapman — *Unconscious Frustration: Dynamically Assessing User Experience using Eye and Mouse Tracking* (PACMHCI ETRA 2023)

[`stone2023unconscious`](references.bib) · [DOI 10.1145/3591137](https://doi.org/10.1145/3591137) · PACMHCI Vol. 7, No. ETRA, Article 168 (17 pages)

The gaze-cursor coupling lineage's *dynamic* probe. Where Huang, White & Buscher 2012 measured alignment as a scalar at-scale (~700 ms lag, 233 → 77 px alignment), Stone & Chapman read the coupling itself as a **time-resolved UX-friction signal** that neither stream carries alone. Authors at the University of Alberta (Faculty of Kinesiology, Sport, and Recreation; the same lab that publishes reach-trajectory cognitive-readout work).

## Method

A custom menu-navigation task styled after a popular video game. Two participant cohorts:

1. **Local cohort** — monitor-mounted hardware eye tracker (high-fidelity LAB instrument).
2. **Remote cohort** — webcam-based eye-tracking algorithm (low-fidelity, scalable instrument).

Concurrent mouse tracking in both cohorts. The headline question: can simultaneous gaze + cursor recovery — even with the webcam-grade tracker — detect *unconscious frustration*, defined as a UX disruption the user has poor cognitive access to and would not self-report?

## Key contribution

Frustration manifests in the *coupling residual*, not in either stream marginally. When the cursor and gaze decouple at moments where the task demands fine-grained motor-cognitive coordination, that decoupling is itself the friction signal. The authors operationalize this as a dynamic, time-resolved measurement — a *what-is-happening-now* probe rather than an at-scale alignment scalar.

The webcam-cohort replication is the load-bearing methodological move: it shows the coupling-residual signal does not require lab-grade instrumentation, opening the construct to in-the-wild deployment.

## Where this fits relative to approach-retreat

Approach-retreat extends this line in two complementary directions:

1. **From coupling to trajectory dynamics.** Stone & Chapman read the gaze-cursor coupling residual as the signal. Approach-retreat goes further: even on the *cursor-only* (no-gaze) WILD surface, the cursor's per-AOI episode geometry — `min_dist`, `retreat_dist`, `dwell`, `direction_changes` — carries enough structure to recover decision-relevant labels (the four-class taxonomy in CIKM §4.6, the 0.765 ACD WILD AUC in §4.5). The cursor's *what-it-does-next* descriptors stand in for gaze when gaze is unavailable.
2. **From per-task to per-result-AOI.** Stone & Chapman's task is single-target menu navigation. Approach-retreat's task is per-result deliberation across an entire SERP — multiple AOIs, each contributing its own approach-retreat episode. The coupling-residual construct generalizes naturally to the per-AOI grain: each AOI is a candidate locus for fine-grained motor-cognitive coordination, and the geometry of the episode against that AOI is the per-AOI residual.

## Why this paper is in §2 (and §5)

CIKM §2 cites this as the recent endpoint of the cursor-gaze coupling lineage:

> Chen, Anderson & Sohn [CHI EA '01] and Huang, White & Buscher [CHI '12] established that cursor and gaze couple where fine-grained motor-cognitive coordination is required and decouple where it is not... Stone & Chapman [PACMHCI ETRA '23] read the coordination itself as a UX signal.

The lineage thread: 2001 establishes coupling exists, 2012 quantifies coupling at scale, 2023 reads the coupling residual itself as the friction signal. Approach-retreat extends the same construct to the per-AOI episode geometry, with cursor-only deployability where Stone & Chapman still require gaze.

## Where the paper does and doesn't constrain approach-retreat

- **Does:** Validates the coupling-residual construct as a dynamic friction signal. Validates the webcam-cohort robustness — supporting the `approach-retreat` schema's WebGazer.js calibration option in CIKM §5.
- **Does not:** Ground per-result-AOI episode geometry. The task is single-target menu navigation, not SERP encounter; their notion of "trajectory" stays at the cursor-gaze coupling level rather than at the per-AOI episode shape.

## Notes for the CIKM paper

§2 cites this work as the closing reference in the cursor-gaze coupling lineage. Cite as `\cite{stone2023unconscious}`. The paper is also relevant to §5's WebGazer.js calibration framing — the webcam-cohort result demonstrates that cheap gaze instrumentation suffices for the coupling-residual construct.
