# Changelog

All notable changes to `approach-retreat` are documented here. Versioning
follows SemVer; breaking changes bump MAJOR, additive changes bump MINOR.

## [0.1.0] — 2026-04-15

First tagged release. Ships the cursor episode decomposition library, the
four-class outcome taxonomy, the PostHog adapter, the gh-pages Quora-SERP
demo, and the canonical M4 nine-feature extractor used by the Edmonds 2026
CIKM paper.

### Added

- **`ResultFeatureTracker`** — per-result running aggregates of the nine M4
  approach features from the Edmonds 2026 CIKM paper. Computed against each
  result's page-space Y center (scroll-invariant) with O(1) memory per
  tracked result regardless of sample count.
- **`ApproachRetreat.getApproachFeatures()`** — returns the nine features
  per result position, ranked by position. Fully parity-tested against the
  AdSERP canonical extractor in
  `attentional-foraging/scripts/m4_nb21_hybrid_rerun.py` (all nine features
  match within 1e-6).
- **Parity test suite** — `scripts/test_feature_tracker_parity.{js,py}` run
  a synthetic trajectory through both the JS library and the Python paper
  extractor and diff the outputs.
- **PostHog adapter extension** — `ar_session_summary` now ships
  `ar_approach_features` alongside the existing four-class taxonomy fields,
  so downstream pipelines can train M4 click predictors or M5 deferred-class
  detectors directly on captured data.
- **`docs/validation/m5-calibration.md`** — methodology doc for deploying a
  cursor-only deferred-class detector calibrated from behavioral labels.
- **Four-class outcome taxonomy** — `clicked` / `deferred` /
  `evaluated_rejected` / `not_approached`. Library heuristic (cursor
  re-entry within `reapproachWindowMs`) is a lower-fidelity approximation
  of NB22 gaze-regression labels; deployments needing gaze-grounded labels
  should follow the M5 calibration methodology above.
- **`approachFeatureProximityPx`** config option (default 100 px) matching
  the canonical AdSERP extractor's `dwell_in_proximity_ms` threshold.

### Validated

- Cross-dataset replication on the Attentive Cursor Dataset
  [Leiva & Arapakis 2020]: 11-feature LR reaches AUC 0.821 on `ad_clicked`
  vs. scalar mouse-length baseline 0.696, no eye tracker. See
  `analysis/attcur-validation/`.
- AdSERP validation lives in the companion `attentional-foraging` repo
  (NB20–NB22, and the gaze-clean Option D hybrid extractor rerun at
  `scripts/m4_nb21_hybrid_rerun.py`).

### Notes

- Not yet on npm. Install from the GitHub repo URL or clone and
  `node build.js` yourself. The `dist/` bundle is gitignored; rebuild
  before every tagged release.
- Coordinate convention: cursor Y is page-space throughout, matching
  `attentional-foraging`.
