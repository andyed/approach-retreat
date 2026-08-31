# approach-retreat — TODO

## PAI proof images — stale after 2026-08-30 `.ias` regeneration (external: Duchowski)

`p006-b4-t7` and `p019-b1-t8` proof images are stale — their `.ias` exports
changed in the 2026-08-30 collision-fix rebuild. Regeneration needs
Duchowski's `glias2poly`; external dependency, cannot be closed locally.
`p047-b6-t1` is current. Re-check after the next glias2poly hand-off.

## Throttle the `mousemove` feature path — user-CPU cost

`ApproachRetreatTracker` binds `mousemove` and runs `_onMouseMove` on
**every** event (~60 Hz while the cursor moves, more on high-refresh
displays). Per event it does two things (`src/approach-retreat.js`
~L722–790):

- `_updateApproachFeatures()` — O(N) feature accumulation against each
  result's *cached* page-space center. Cheap-ish.
- an over-result hit-test that calls `document.querySelectorAll(...)`
  **and `el.getBoundingClientRect()` on every result** (~L745–761).
  `getBoundingClientRect()` forces a synchronous layout read.

So a SERP tracking N results runs one `querySelectorAll` + N forced
layout reads ~60×/s, on a real user's browser, for as long as the page
is open. Scroll and resize are *already* rAF-throttled
(`_scheduleViewportSnapshot`) — the cursor feature path is the one hot
path that never got the same treatment.

**This is over-sampling, and it costs user CPU.** The §5.1 cursor
sampling-rate ablation (`attentional-foraging/scripts/sampling_rate_ablation.py`,
output `scripts/output/ablations/sampling_rate_ablation.json`, commit
`7be3d345`) downsamples the AdSERP cursor stream from its native
~59 Hz down to 1 Hz and re-runs the M4 LOSO click-prediction: **M4 AUC
is flat at 0.847 ± 0.001 across the whole range — no floor, no
degradation.** The seven approach features are per-episode aggregates
(closest approach, integrated proximity dwell, monotonicity counts)
and rate-invariant by construction. A WILD-deployed telemetry library
has no accuracy reason to sample above ~15 Hz — and 60 Hz of
`getBoundingClientRect` for zero accuracy gain is an avoidable
CPU/battery cost we are imposing on the user.

### Proposed change

The ablation licenses one specific thing: **uniform time-decimation**
is safe to 1 Hz. A fixed-rate throttle *is* uniform time-decimation, so
it is directly evidence-backed. Schemes that change the sampling
*distribution* change what the aggregate features numerically are
(`mean_dist` shifts from a time-weighted to a path-weighted mean;
`direction_changes` / `frac_decreasing` undercount sub-threshold
wiggles) — a train/deploy mismatch against the native-rate-trained M4.

So the design is three plain pieces, not one adaptive scheme:

- **Feature path — fixed-rate throttle. DONE.** Shipped as the
  `maxSampleHz` config option (default 15 Hz). `_onMouseMove`
  early-returns before any state is touched if the event arrives
  within `1000 / maxSampleHz` ms of the last kept event — exactly the
  uniform time-decimation the ablation tested. `maxSampleHz: 0` /
  `Infinity` disables it for native-rate replication. The hit-test
  still does a live `querySelectorAll` + `getBoundingClientRect` per
  *kept* event; reusing cached result rects would shave more, but at
  15 Hz the cost is already ~4× down and that refactor is a separate,
  lower-priority pass.
- **Scroll-triggered feature sampling — a coverage fix.** Feature
  samples currently come only from `_onMouseMove`; a
  scroll-without-mousemove changes page-space `d_i(t)` invisibly
  (`_updateViewportBands` does episode lifecycle, not feature
  sampling). Worth closing — but it is also a regime change, so pair
  it with a cheap re-validation: re-run the §5.1 ablation logic with
  scroll-samples included and confirm M4 still lands at 0.847.
- **Distance-triggered decimation — trajectory shipping only.** Right
  for the adapter `samples[]` path (`includeSamplesInEpisodeJson` →
  PostHog): uniform-in-space points describe the path better per byte.
  Do **not** use it for the feature computation — it redefines
  `mean_dist` and would reopen validation for a marginal CPU gain over
  the fixed throttle.

### Keep correct under throttling
- `dwell_in_proximity_ms` integrates Δt between samples; a larger Δt
  per kept sample still integrates correctly, but verify Δt is measured
  between *kept* samples, not raw events.
- `min_dist` and the velocity terms get coarser estimates with sparser
  sampling. The ablation shows AUC holds regardless, and the §5.1 LOFO
  shows the velocity terms contribute ~nothing — spot-check after.

### Status
Fixed-rate throttle **shipped** (`maxSampleHz`, default 15 Hz). The
remaining two pieces — scroll-triggered feature sampling and
distance-triggered decimation for the trajectory `samples[]` path — are
still open; each needs its own re-validation before shipping, as noted
above. The paper's §7 deployment claim was reframed from a Nyquist
"~15 Hz floor" to the measured rate-robustness result; the library now
follows.

## Close the naming-drift bug class — guard 6 + CI wiring

`scripts/gen_feature_glossary.py` moved feature *names* out of human
memory and into an executable check: five guards, exit 1 with a diff on
any mismatch, no table emitted on failure. Two gaps remain, both small,
both closing the same class.

**The class.** Feature vocabulary lives on three surfaces that evolve
independently — the JS library (`ResultFeatureTracker`), the Python
extractor (`m4_nb21_hybrid_rerun.py::M4_FEATURES`), and paper prose.
The parity tests guarantee the *values* match at 1e-6; nothing
guaranteed the *names* did. On 2026-08-12 that gap produced three
separate failures in one day: an external reader could not distinguish
`total_dwell_ms` (LAB gaze-fixation dwell) from `dwell_in_target_ms`
(WILD cursor-in-target analog) because neither was defined in-paper; the
canonical script's LOSO row prints `M4 (9 approach)` while the paper's
M4 is the seven buffer-robust features (`final_dist` / `retreat_dist`
excluded by the §5.2 leakage screen); and mid-analysis the grid's M2
was misread as cursor hover when it is gaze dwell, which briefly
inverted a robustness conclusion until the isolating run corrected it.
Same root cause each time: a name maintained by vigilance across
surfaces.

### Guard 6 — model-set composition, not just feature names

Guards 1–2 pin the *nine-feature vector's* names and order across JS and
Python. They do not pin what a **model set** is composed of, which is
where the M4-9/M4-7 drift actually lived — in a row label, not a feature
name. Rename nothing and the drift recurs.

Add to `run_guards()`:

- Parse the canonical extractor for its model-set definitions (the
  `loso_auc(...)` call sites and their printed labels).
- Assert the row labeled M4 is built from exactly
  `M4_FEATURES − {final_dist, retreat_dist}` (seven), and that M2's dwell
  term names which dwell it is (gaze `total_dwell_ms` vs cursor
  `dwell_in_proximity_ms`).
- Fail with the same diff format when a label and its feature slice
  disagree.

Blocked on the upstream fix landing first: `m4_nb21_hybrid_rerun.py`
currently *prints* `M4 (9 approach)` for the nine-feature vector. Fix
the label there (or emit both M4-7 and M4-9 rows, as the post-CIKM
ablations do), then add the guard so it can't drift back. Note the
paper's published 0.847 was verified as M4-7 @ buf500 — the mislabel is
a code/reporting bug, not a published-number error.

### CI wiring — make the guards run without being remembered

The guards only fire when someone runs the generator. Wire them into the
existing test path so a drifting rename fails the push, not the next
manual regeneration:

- Preferred: a vitest case (`tests/unit/glossary-drift.test.js`) that
  shells out to `python3 scripts/gen_feature_glossary.py --check` and
  asserts exit 0. **Depends on the vitest harness (`tests/`,
  `vitest.config.js`) being committed — it is currently untracked
  in-flight work from a concurrent session. Do not commit that harness
  as a side effect of this item.**
- Needs a `--check` flag on the generator: run guards, emit nothing,
  exit 0/1. Today the script always rewrites its outputs, which is wrong
  for CI (dirty tree) and wrong for a pre-commit hook.
- Add the same call to `.github/workflows/deploy.yml` before
  `npm run build`, so a drift breaks the deploy rather than shipping a
  stale README table. Requires `python3` on the runner (ubuntu-latest
  has it; no extra deps — the generator is stdlib-only).

### Known limits (do not over-claim the fix)

The guards cover *names* and *coverage*, not *usage*: prose can still
say "dwell" and mean the wrong dwell. That was the M2 misread, and no
guard catches it — the mitigation is that the definition is now one
lookup away in both README and paper. Guard 6 narrows this by forcing
model-set labels to name their dwell term, but the residual risk is
editorial, not mechanical.

### Status
Guards 1–5 shipped (`scripts/gen_feature_glossary.py`, 2026-08-12).
Guard 6 and CI wiring specced here, unstarted; guard 6 blocked on the
upstream label fix, CI wiring blocked on the vitest harness landing.
