# approach-retreat — TODO

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
output `scripts/output/cikm-2026/sampling_rate_ablation.json`, commit
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
