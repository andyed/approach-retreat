/**
 * ApproachRetreat — cursor approach-retreat dynamics on search result pages.
 *
 * SERP-specific companion to ClickSense. While ClickSense captures the moment
 * of commitment (mousedown→mouseup), ApproachRetreat captures the evaluation
 * phase: how the cursor approaches, dwells over, and retreats from ranked
 * results before any click occurs.
 *
 * Core signals:
 * - Approach velocity: fast = scanning, slow = evaluating
 * - Dwell time per result: time cursor spends in a result's AOI
 * - Retreat distance: how far cursor moves after leaving — far retreats predict
 *   commitment to rejection; close retreats predict re-approach
 * - Re-approach: cursor returns to a previously visited result (reconsideration)
 * - Commitment depth: how far down the SERP before first click
 *
 * Four-class taxonomy (splits the non-click class):
 * - CLICKED: cursor entered, evaluated, committed
 * - DEFERRED: cursor entered, retreated, but re-approached (still considering)
 * - EVALUATED_REJECTED: cursor entered, evaluated, retreated — no return
 * - NOT_APPROACHED: result was visible but cursor never entered the AOI
 *
 * Each result element is an AOI (area of interest). The library tracks
 * cursor enter/dwell/exit episodes and builds an approach-retreat timeline.
 *
 * Compatible with ClickSense: use both on the same page for full
 * evaluation + commitment capture.
 *
 * Reference: Edmonds (2026), building on:
 * - Huang et al. (2012) "User see, user point" — cursor as gaze proxy on SERPs
 * - Guo & Agichtein (2012) — cursor trail features predict result relevance
 * - Arapakis & Leiva (2016) — predicting search satisfaction from cursor
 */

/**
 * Four-class outcome taxonomy.
 * The practical contribution: splitting non-clicks into actionable classes.
 */
export const Outcome = Object.freeze({
  CLICKED: 'clicked',
  DEFERRED: 'deferred',
  EVALUATED_REJECTED: 'evaluated_rejected',
  NOT_APPROACHED: 'not_approached',
});

/**
 * Classify an AOI against a viewport snapshot.
 *
 * Pure. Mirrors the semantics of `viewport_ms_for_trial` in
 * attentional-foraging/scripts/viewport_time_calibration.py — any-intersection
 * uses a strict min > max test (touching edges is NOT intersecting, matching
 * Python's `min(..., vp_bot) <= max(..., vp_top): continue`), and the three
 * thirds are [0, third), [third, 2*third), [2*third, scr_h].
 *
 * @param {number} aoiPageTop — AOI top in page-space pixels
 * @param {number} aoiPageBot — AOI bottom in page-space pixels
 * @param {number} scrollY — current document.scrollingElement.scrollY
 * @param {number} scrH — current viewport height
 * @returns {{intersecting: boolean, band: 'top'|'mid'|'bot'|'off'}}
 *   `band === 'off'` when the AOI center is outside [0, scr_h] OR the AOI
 *   doesn't intersect the viewport at all. `intersecting` is independent —
 *   a tall AOI can intersect while its center is off-viewport.
 */
export function classifyAoiInViewport(aoiPageTop, aoiPageBot, scrollY, scrH) {
  const vpTop = scrollY;
  const vpBot = scrollY + scrH;
  const intersecting =
    Math.min(aoiPageBot, vpBot) > Math.max(aoiPageTop, vpTop);
  if (!intersecting) return { intersecting: false, band: 'off' };

  const centerVpY = (aoiPageTop + aoiPageBot) / 2 - scrollY;
  const third = scrH / 3;
  let band = 'off';
  if (centerVpY >= 0 && centerVpY < third) band = 'top';
  else if (centerVpY >= third && centerVpY < 2 * third) band = 'mid';
  else if (centerVpY >= 2 * third && centerVpY <= scrH) band = 'bot';
  return { intersecting, band };
}

/**
 * Batch computation of per-AOI viewport-band dwell totals from a scroll
 * timeline. Pure helper, parity-tested against the Python reference
 * `viewport_ms_for_trial` in
 * attentional-foraging/scripts/viewport_time_calibration.py.
 *
 * Piecewise-constant semantics: the interval `[timeline[i].t, timeline[i+1].t]`
 * is attributed using the scroll position at `timeline[i]` (i.e. the
 * *start* of the interval), matching Python's `(t0, y0), (t1, _) in zip(...)`.
 *
 * Zero-duration or negative intervals are skipped.
 *
 * @param {Array<{t: number, scrollY: number}>} timeline — must be sorted by t.
 * @param {Array<{position: number, page_top: number, page_bot: number}>} aois
 * @param {number} scrH — viewport height (assumed constant across the timeline;
 *   if the page resizes, callers should segment the timeline by basis and
 *   aggregate segment totals).
 * @returns {Array<{position, any_ms, top_ms, mid_ms, bot_ms}>} sorted by position.
 */
export function computeViewportBandsPure(timeline, aois, scrH) {
  const out = aois.map((a) => ({
    position: a.position,
    any_ms: 0,
    top_ms: 0,
    mid_ms: 0,
    bot_ms: 0,
  }));
  for (let i = 0; i < timeline.length - 1; i++) {
    const dt = timeline[i + 1].t - timeline[i].t;
    if (dt <= 0) continue;
    const scrollY = timeline[i].scrollY;
    for (let j = 0; j < aois.length; j++) {
      const a = aois[j];
      const { intersecting, band } =
        classifyAoiInViewport(a.page_top, a.page_bot, scrollY, scrH);
      if (!intersecting) continue;
      out[j].any_ms += dt;
      if (band === 'top') out[j].top_ms += dt;
      else if (band === 'mid') out[j].mid_ms += dt;
      else if (band === 'bot') out[j].bot_ms += dt;
    }
  }
  out.sort((a, b) => a.position - b.position);
  return out;
}

/**
 * Pure-function computation of continuous viewport analytics + scroll-
 * trajectory features (NB30's minimal B∪C' set) + an IAB/MRC-aligned
 * viewable-impression pair. Parity-tested against the Python reference
 * in attentional-foraging/scripts/nb30_scroll_trajectory.py.
 *
 * For each AOI: compute vt_any_ms, vt_center_ms, avg_viewport_y_px,
 * max_overlap_frac, min_abs_velocity_px_per_s, n_reversals,
 * ms_at_50pct_or_more, iab_viewable from a pre-built scroll timeline.
 * Piecewise-constant: each interval [timeline[i], timeline[i+1]) is
 * attributed using the scrollY at timeline[i].
 *
 * IAB viewability rule (MRC/IAB Viewable Impression Measurement
 * Guidelines): a display AOI is "viewable" if ≥ 50 % of its pixels
 * are in view for ≥ 1 continuous second. `ms_at_50pct_or_more` is the
 * continuous-valued analogue (no time-continuity constraint);
 * `iab_viewable` is the boolean that implements the full rule. Video
 * AOIs requiring a 2 s threshold should override via the caller
 * rather than the library.
 *
 * @param {Array<{t: number, scrollY: number}>} timeline — sorted by t.
 * @param {Array<{position: number, page_top: number, page_bot: number}>} aois
 * @param {number} scrH — viewport height (assumed constant).
 * @param {number} [centerTolPx=100] — ±px from viewport center defining
 *   "near center" for vt_center_ms.
 * @param {number} [iabViewableThresholdMs=1000] — continuous-duration
 *   threshold for the IAB viewable-impression rule (default: 1000 ms
 *   per MRC display guideline; set 2000 for video).
 * @returns {Array<{position, vt_any_ms, vt_center_ms, avg_viewport_y_px,
 *   max_overlap_frac, min_abs_velocity_px_per_s, n_reversals,
 *   ms_at_50pct_or_more, iab_viewable}>} sorted by position.
 */
export function computeViewportAnalyticsPure(
  timeline,
  aois,
  scrH,
  centerTolPx = 100,
  iabViewableThresholdMs = 1000
) {
  const centerY = scrH / 2;
  const accum = aois.map((a) => ({
    position: a.position,
    any_ms: 0,
    center_ms: 0,
    sum_center_y_ms: 0,
    max_overlap_frac: 0,
    min_abs_v: Infinity,
    n_reversals: 0,
    last_v_sign: 0,
    // IAB/MRC impression tracking
    ms_at_50pct_or_more: 0,
    current_50pct_stretch_ms: 0,
    iab_viewable: false,
  }));
  for (let i = 0; i < timeline.length - 1; i++) {
    const dt = timeline[i + 1].t - timeline[i].t;
    if (dt <= 0) continue;
    const dtS = dt / 1000;
    const scrollY = timeline[i].scrollY;
    const v = dtS > 0 ? (timeline[i + 1].scrollY - scrollY) / dtS : 0;
    const absV = Math.abs(v);
    const sign = absV < 1e-6 ? 0 : v > 0 ? 1 : -1;
    for (let j = 0; j < aois.length; j++) {
      const a = aois[j];
      const vpTop = scrollY;
      const vpBot = scrollY + scrH;
      const overlap = Math.min(a.page_bot, vpBot) - Math.max(a.page_top, vpTop);
      const ac = accum[j];
      if (overlap <= 0) {
        // Dropping out of view resets the current IAB continuity stretch.
        ac.current_50pct_stretch_ms = 0;
        continue;
      }
      const centerVpY = (a.page_top + a.page_bot) / 2 - scrollY;
      const aoiH = a.page_bot - a.page_top;
      const overlapFrac = aoiH > 0 ? overlap / aoiH : 0;
      ac.any_ms += dt;
      ac.sum_center_y_ms += centerVpY * dt;
      if (overlapFrac > ac.max_overlap_frac) ac.max_overlap_frac = overlapFrac;
      if (Math.abs(centerVpY - centerY) <= centerTolPx) ac.center_ms += dt;
      if (absV < ac.min_abs_v) ac.min_abs_v = absV;
      if (ac.last_v_sign !== 0 && sign !== 0 && sign !== ac.last_v_sign) {
        ac.n_reversals += 1;
      }
      if (sign !== 0) ac.last_v_sign = sign;
      // IAB: accumulate ms-above-50% and track the current continuous stretch.
      if (overlapFrac >= 0.5) {
        ac.ms_at_50pct_or_more += dt;
        ac.current_50pct_stretch_ms += dt;
        if (ac.current_50pct_stretch_ms >= iabViewableThresholdMs) {
          ac.iab_viewable = true;
        }
      } else {
        ac.current_50pct_stretch_ms = 0;
      }
    }
  }
  const out = accum.map((a) => ({
    position: a.position,
    vt_any_ms: a.any_ms,
    vt_center_ms: a.center_ms,
    avg_viewport_y_px: a.any_ms > 0 ? a.sum_center_y_ms / a.any_ms : 0,
    max_overlap_frac: a.max_overlap_frac,
    min_abs_velocity_px_per_s: a.min_abs_v === Infinity ? 0 : a.min_abs_v,
    n_reversals: a.n_reversals,
    ms_at_50pct_or_more: a.ms_at_50pct_or_more,
    iab_viewable: a.iab_viewable,
  }));
  out.sort((a, b) => a.position - b.position);
  return out;
}

const DEFAULTS = {
  // AOI selector: which elements are SERP results?
  resultSelector: '[data-result]',

  // Minimum dwell to count as a visit (filters drive-by crossings)
  minDwellMs: 100,

  // Approach tracking: how far before the AOI boundary to start recording
  approachMarginPx: 40,

  // Re-approach: if cursor returns within this window, it's a reconsideration
  reapproachWindowMs: 5000,

  // Scroll tracking: compensate for scroll-induced cursor-AOI changes
  trackScroll: true,

  // Viewport intersection: only track results currently visible
  trackVisibility: true,

  // Position attribute: data attribute holding the rank position
  positionAttr: 'data-position',

  // Callback for each completed episode (enter → dwell → exit)
  onEpisode: null,

  // Callback for clicks (augments ClickSense if both present)
  onClick: null,

  // Callback for reranking signals (batch of episodes → relevance scores)
  onSignal: null,

  // Forward vs regressive classification tolerance. An episode is classified
  // at entry time: forward iff scrollY >= scrollHwm - directionTolPx. This
  // mirrors data_loader.classify_fixations in the attentional-foraging
  // notebooks (tol=50 px, parity-verified at 4,036/4,036 fixations).
  directionTolPx: 50,

  // When true, Episode.toJSON() includes the raw samples[] array. Off by
  // default to preserve the small JSON payload contract for existing users.
  // Turn on to let adapters (e.g. PostHog) downsample and ship trajectory
  // data as research material.
  includeSamplesInEpisodeJson: false,

  // Proximity threshold for the M4 `dwell_in_proximity_ms` feature, in
  // page-space pixels. 100 px matches the canonical AdSERP extractor
  // (attentional-foraging/scripts/m4_nb21_hybrid_rerun.py).
  approachFeatureProximityPx: 100,

  // Per-AOI viewport-band dwell tracking. When enabled, each observed
  // AOI accumulates cumulative ms in each of {any, top, mid, bot} bands
  // via piecewise-constant snapshots on scroll/resize/reflow/intersect.
  // Emitted on ar_session_summary (per-position) and ar_episode (scoped
  // to the entered_at → exited_at window).
  //
  // Calibration (LAB n=2,351, deferred-vs-eval-rejected): bands-alone AUC
  // 0.799, continuous viewport analytics (see below) 0.798, minimal 6-
  // feature B∪C' recovers the K13 lift. K14 at n=47 (paired Δ = +0.003,
  // p = 0.22 ns) cannot rule in or out a small additional contribution
  // from bands beyond B∪C; default-on is retained for backward
  // compatibility, but consumers favoring parsimony can flip off.
  trackViewportBands: true,

  // Per-AOI continuous viewport analytics + scroll trajectory. Four B
  // features (vt_any_ms duplicates the band emission; vt_center_ms,
  // avg_viewport_y_px, max_overlap_frac) and two C features
  // (min_abs_velocity_px_per_s, n_reversals) — see NB30 K18 for the
  // forward-selection that picked this minimal set. Emitted alongside
  // the bands on ar_episode / ar_session_summary when enabled.
  trackViewportAnalytics: true,

  // ±px from viewport center defining "near center" for vt_center_ms.
  // NB30 K22 sweep shows the feature is flat across {25, 50, 100, 200,
  // 400} px (pooled AUC spread 0.001); 100 px is the defensible default.
  viewportCenterTolPx: 100,

  // IAB/MRC Viewable Impression continuity threshold (ms). The
  // `iab_viewable` flag goes true when an AOI sustains ≥ 50 % pixel
  // overlap with the viewport for ≥ this many ms continuously.
  // 1000 ms is the MRC display-ad rule; set 2000 for video AOIs per
  // the MRC video rule.
  iabViewableThresholdMs: 1000,

  // Observe layout reflow via ResizeObserver on documentElement. When
  // available, reflow invalidates cached page-Y centers and schedules a
  // fresh band snapshot. Feature-detected; absence degrades to
  // scroll + window.resize coverage only (safe for non-reflowing pages).
  trackViewportReflow: true,
};

/**
 * Per-result running aggregates of the nine M4 approach features
 * (Edmonds 2026, CIKM). One tracker per SERP result element, updated on
 * every mousemove with the cursor's page-space Y coordinate. O(1) memory
 * per tracked result; 13 floats of live state regardless of sample count.
 *
 * The nine features mirror the canonical extractor in
 * attentional-foraging/scripts/m4_nb21_hybrid_rerun.py:
 *
 *   1. min_dist              — min |Δy| cursor to result center over whole trial
 *   2. mean_dist             — mean |Δy|
 *   3. final_dist            — last seen |Δy|
 *   4. retreat_dist          — final_dist − min_dist (post-closest drift)
 *   5. dwell_in_proximity_ms — total time cursor was within proximityPx of center
 *   6. mean_approach_velocity — mean −Δdist/Δt (directed toward result, px/s)
 *   7. max_approach_velocity  — max −Δdist/Δt
 *   8. direction_changes     — count of velocity sign flips
 *   9. frac_decreasing       — fraction of sample transitions with decreasing dist
 *
 * Coordinates are page-space (pageY = clientY + scrollY) so the result
 * center is scroll-invariant and can be cached at first observation.
 */
export class ResultFeatureTracker {
  constructor(pageYCenter, proximityPx = 100) {
    this.pageYCenter = pageYCenter;
    this.proximityPx = proximityPx;

    this.sampleCount = 0;
    this.sumDist = 0;
    this.minDist = Infinity;
    this.finalDist = 0;
    this.lastT = null;

    // Velocity running state. lastVelSign === null means "no prior
    // velocity seen" so the first velocity establishes the baseline
    // without being counted as a direction change. Matches the paper's
    // `np.diff(np.sign(vels)) != 0` length-(n-2) semantics.
    this.lastVelSign = null;
    this.sumVel = 0;
    this.maxVel = -Infinity;
    this.nTransitions = 0;
    this.nDecreasing = 0;
    this.directionChanges = 0;

    this.dwellInProximityMs = 0;
  }

  /**
   * Update with one mousemove sample. pageY is the cursor's page-space Y,
   * t is a performance.now() timestamp in milliseconds.
   */
  update(pageY, t) {
    const dist = Math.abs(pageY - this.pageYCenter);

    if (this.sampleCount === 0) {
      this.sampleCount = 1;
      this.sumDist = dist;
      this.minDist = dist;
      this.finalDist = dist;
      this.lastT = t;
      return;
    }

    const dt = t - this.lastT;
    // Skip samples with zero or negative time delta — can happen with
    // duplicate events or clock skew. Don't count them as transitions.
    if (dt <= 0) {
      this.finalDist = dist;
      if (dist < this.minDist) this.minDist = dist;
      return;
    }

    // Directed velocity: positive = approaching result (dist decreasing)
    // Matches the paper's `vels = -np.diff(dist) / dts * 1000` (px/s).
    const vel = (-(dist - this.finalDist) / dt) * 1000;

    this.nTransitions += 1;
    this.sumVel += vel;
    if (vel > this.maxVel) this.maxVel = vel;
    if (dist < this.finalDist) this.nDecreasing += 1;

    // Direction-change counter: mirrors the paper's
    // `int(np.sum(np.diff(np.sign(vels)) != 0))` exactly. Every sign
    // transition counts, including through zero (+1 → 0 → +1 counts as
    // two changes). The first velocity establishes the baseline without
    // being counted.
    const velSign = vel > 0 ? 1 : vel < 0 ? -1 : 0;
    if (this.lastVelSign !== null && velSign !== this.lastVelSign) {
      this.directionChanges += 1;
    }
    this.lastVelSign = velSign;

    // Dwell-in-proximity accumulator: integrate Δt where the cursor ENDED
    // the interval inside the proximity band. Matches the paper's
    // `if in_prox[i]: dwell_ms += dt`, with the 2000ms gap filter that
    // protects against tab-switch / away-from-keyboard intervals.
    if (dist < this.proximityPx && dt < 2000) {
      this.dwellInProximityMs += dt;
    }

    this.sampleCount += 1;
    this.sumDist += dist;
    if (dist < this.minDist) this.minDist = dist;
    this.finalDist = dist;
    this.lastT = t;
  }

  /**
   * Return the nine approach features as a plain object. Safe to call
   * at any point; returns zeros / sentinels on fewer than two samples.
   */
  getFeatures() {
    const n = this.sampleCount;
    const t = this.nTransitions;
    return {
      min_dist: n > 0 ? this.minDist : 0,
      mean_dist: n > 0 ? this.sumDist / n : 0,
      final_dist: n > 0 ? this.finalDist : 0,
      retreat_dist: n > 0 ? this.finalDist - this.minDist : 0,
      dwell_in_proximity_ms: this.dwellInProximityMs,
      mean_approach_velocity: t > 0 ? this.sumVel / t : 0,
      max_approach_velocity: this.maxVel === -Infinity ? 0 : this.maxVel,
      direction_changes: this.directionChanges,
      frac_decreasing: t > 0 ? this.nDecreasing / t : 0,
      sample_count: n,
    };
  }
}

/**
 * A single approach-retreat episode on one result.
 */
class Episode {
  constructor(resultEl, position, { includeSamples = false } = {}) {
    this.resultEl = resultEl;
    this.position = position;
    this._includeSamples = includeSamples;
    this.enteredAt = performance.now();
    this.exitedAt = null;
    this.clicked = false;
    this.clickedAt = null;

    // Cursor dynamics within the AOI
    this.samples = []; // [{x, y, t, vx, vy}]
    this.peakVelocity = 0;
    this.minVelocity = Infinity;

    // Approach phase (before entry)
    this.approachVelocity = null;
    this.approachAngle = null;

    // Retreat tracking
    this.retreatDistance = 0;  // px from AOI center at max retreat

    // Visit count (1 = first visit, 2+ = re-approach)
    this.visitNumber = 1;

    // Whether this result was later re-approached after this episode
    this.reapproached = false;

    // Forward vs regressive at entry time. 'forward' = user was at or near
    // the scroll high-water mark when entering. 'regressive' = user scrolled
    // back up to re-examine. Null until classified in _enterResult.
    this.direction = null;
    this.entryScroll = null;
    this.hwmAtEntry = null;
  }

  get dwellMs() {
    const end = this.exitedAt || performance.now();
    return end - this.enteredAt;
  }

  get retreated() {
    return this.exitedAt !== null && !this.clicked;
  }

  /**
   * Classify this episode into the four-class taxonomy.
   * Call after the session is complete (or after reapproach window expires)
   * so that deferred vs rejected is resolved.
   */
  get outcome() {
    if (this.clicked) return Outcome.CLICKED;
    if (this.reapproached) return Outcome.DEFERRED;
    if (this.exitedAt !== null) return Outcome.EVALUATED_REJECTED;
    // Still active — no classification yet
    return null;
  }

  addSample(x, y, t, vx, vy) {
    this.samples.push({ x, y, t, vx, vy });
    const v = Math.sqrt(vx * vx + vy * vy);
    if (v > this.peakVelocity) this.peakVelocity = v;
    if (v < this.minVelocity && v > 0) this.minVelocity = v;
  }

  toJSON() {
    const json = {
      position: this.position,
      outcome: this.outcome,
      dwell_ms: Math.round(this.dwellMs),
      visited: true,
      clicked: this.clicked,
      retreated: this.retreated,
      retreat_distance: Math.round(this.retreatDistance),
      visit_number: this.visitNumber,
      approach_velocity: this.approachVelocity,
      approach_angle: this.approachAngle,
      peak_velocity: this.peakVelocity,
      min_velocity: this.minVelocity === Infinity ? 0 : this.minVelocity,
      sample_count: this.samples.length,
      direction: this.direction,
      entry_scroll: this.entryScroll,
      hwm_at_entry: this.hwmAtEntry,
      entered_at: this.enteredAt,
      exited_at: this.exitedAt,
      clicked_at: this.clickedAt,
      // Episode-scoped viewport-band dwell, restricted to
      // [entered_at, exited_at]. Null when the library was initialized with
      // trackViewportBands: false or the AOI was never band-observed.
      vp_any_ms: this.viewportBands ? this.viewportBands.any_ms : null,
      vp_top_ms: this.viewportBands ? this.viewportBands.top_ms : null,
      vp_mid_ms: this.viewportBands ? this.viewportBands.mid_ms : null,
      vp_bot_ms: this.viewportBands ? this.viewportBands.bot_ms : null,
    };
    // Continuous viewport analytics + scroll-trajectory (NB30 minimal set)
    // are emitted at session-summary granularity, not per-episode — the
    // features are aggregates over the whole scroll timeline and some
    // (max_overlap_frac, min_abs_velocity) are non-subtractable. See
    // getViewportAnalytics() on the tracker.
    if (this._includeSamples) {
      json.samples = this.samples;
    }
    return json;
  }
}

export class ApproachRetreat {
  constructor(options = {}) {
    this.config = { ...DEFAULTS, ...options };
    this._episodes = [];       // all completed episodes
    this._active = new Map();  // resultEl → current Episode
    this._retreating = [];     // recently exited episodes still tracking retreat distance
    this._visitCounts = new Map(); // resultEl → visit count
    this._lastMouse = null;    // {x, y, t}
    this._velocity = { vx: 0, vy: 0 };
    this._scrollY = window.scrollY;
    // Scroll high-water mark — running max of scrollY. Used to classify
    // each entry as forward (at/near HWM) or regressive (below HWM).
    this._scrollHwm = window.scrollY;
    this._observer = null;
    this._visibleResults = new Set();

    // Per-result running aggregates for the nine M4 paper features.
    // resultEl → ResultFeatureTracker. Initialized on first mousemove
    // after the result is visible, so pageY centers are cached from a
    // known scroll position. See ResultFeatureTracker docstring.
    this._approachFeatures = new Map();
    this._resultPageYCenter = new Map(); // resultEl → cached pageY center
    this._resultHalfHeight = new Map();  // resultEl → cached AOI half-height

    // Per-AOI viewport-band accumulators. Piecewise-constant: each snapshot
    // closes the interval since lastSnapshotT into the band current *at the
    // start* of that interval, then records the new band. Matches the
    // reference batch helper `computeViewportBandsPure` (parity-tested) which
    // in turn mirrors `viewport_ms_for_trial` in the attentional-foraging
    // calibration script.
    //
    // resultEl → {
    //   any_ms, top_ms, mid_ms, bot_ms: accumulated durations (ms)
    //   lastSnapshotT: performance.now() at last snapshot
    //   currentBand:    'top'|'mid'|'bot'|'off' — band during the pending interval
    //   lastIntersecting: boolean — any-band membership during pending interval
    // }
    this._viewportBandTimes = new Map();

    // rAF scheduling guard so scroll bursts coalesce to one snapshot per frame.
    this._viewportSnapshotRafId = null;
    // Last observed viewport height; surfaced on summary for basis disclosure.
    this._viewportH = typeof window !== 'undefined' ? window.innerHeight : 0;
    this._resizeObserver = null;

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onScroll = this._onScroll.bind(this);
    this._onClick = this._onClick.bind(this);
    this._onResize = this._onResize.bind(this);
    this._runViewportSnapshotRaf = this._runViewportSnapshotRaf.bind(this);

    this._init();
  }

  _init() {
    document.addEventListener('mousemove', this._onMouseMove, { passive: true });
    document.addEventListener('click', this._onClick, { capture: true });

    if (this.config.trackScroll) {
      document.addEventListener('scroll', this._onScroll, { passive: true });
    }

    if (this.config.trackVisibility && typeof IntersectionObserver !== 'undefined') {
      this._observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              this._visibleResults.add(entry.target);
            } else {
              this._visibleResults.delete(entry.target);
            }
          }
          // IntersectionObserver only fires on threshold transitions; an AOI
          // that appears mid-band (long scroll jump) still needs an immediate
          // band snapshot so the pending interval is attributed correctly.
          if (this.config.trackViewportBands) {
            this._scheduleViewportSnapshot();
          }
        },
        { threshold: 0.3 }
      );
      this._observeResults();
    }

    if (this.config.trackViewportBands && typeof window !== 'undefined') {
      window.addEventListener('resize', this._onResize, { passive: true });
      if (
        this.config.trackViewportReflow &&
        typeof ResizeObserver !== 'undefined' &&
        typeof document !== 'undefined' &&
        document.documentElement
      ) {
        this._resizeObserver = new ResizeObserver(() => {
          // Reflow invalidates cached page-Y centers. Clear both caches,
          // then schedule a snapshot so the next interval uses fresh geometry.
          this._resultPageYCenter.clear();
          this._resultHalfHeight.clear();
          this._scheduleViewportSnapshot();
        });
        this._resizeObserver.observe(document.documentElement);
      }
      // Seed pass — establishes lastSnapshotT + currentBand for every AOI
      // currently present so the first real snapshot has a well-defined
      // "previous" band to attribute its interval to.
      this._updateViewportBands(
        typeof performance !== 'undefined' ? performance.now() : 0,
        /* seed */ true
      );
    }
  }

  _observeResults() {
    const results = document.querySelectorAll(this.config.resultSelector);
    for (const el of results) {
      if (this._observer) this._observer.observe(el);
    }
    // Newly-observed AOIs should pick up their initial band state before the
    // next scroll/resize so the first attributable interval is well-defined.
    if (this.config.trackViewportBands) {
      this._scheduleViewportSnapshot();
    }
  }

  /**
   * Call after dynamically adding results (e.g., after reranking).
   */
  refresh() {
    this._observeResults();
  }

  _onMouseMove(e) {
    const now = performance.now();
    const x = e.clientX;
    const y = e.clientY;
    const pageY = y + this._scrollY;

    // Compute velocity
    if (this._lastMouse) {
      const dt = now - this._lastMouse.t;
      if (dt > 0) {
        this._velocity.vx = (x - this._lastMouse.x) / dt;
        this._velocity.vy = (y - this._lastMouse.y) / dt;
      }
    }
    this._lastMouse = { x, y, t: now };

    // Update per-result approach-feature trackers (the nine M4 paper
    // features, aggregated over the whole-trial cursor stream against
    // each result's cached page-space center). Lazy-initialize on first
    // mousemove after the result becomes visible.
    this._updateApproachFeatures(pageY, now);

    // Check which result the cursor is over
    const results = document.querySelectorAll(this.config.resultSelector);
    let hitResult = null;

    for (const el of results) {
      if (this._observer && !this._visibleResults.has(el)) continue;
      const rect = el.getBoundingClientRect();
      const margin = this.config.approachMarginPx;
      if (
        x >= rect.left - margin &&
        x <= rect.right + margin &&
        y >= rect.top - margin &&
        y <= rect.bottom + margin
      ) {
        // Inside margin — check if inside actual bounds
        if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
          hitResult = el;
        }
        break;
      }
    }

    // Update retreat distances for recently exited episodes
    this._updateRetreating(x, y, now);

    // Handle state transitions
    if (hitResult) {
      if (!this._active.has(hitResult)) {
        // Entering a new result — graduate any retreating episodes for
        // OTHER results (cursor committed to evaluating something new).
        // Retreating episodes for THIS result are handled in _enterResult
        // (they become reapproaches).
        this._graduateRetreating(hitResult, now);

        // Enter new result
        this._enterResult(hitResult, now);
      }
      // Add sample to active episode
      const episode = this._active.get(hitResult);
      if (episode) {
        episode.addSample(x, y, now, this._velocity.vx, this._velocity.vy);
      }
    }

    // Check for exits
    for (const [el, episode] of this._active) {
      if (el !== hitResult) {
        this._exitResult(el, episode, now);
      }
    }
  }

  _enterResult(el, now) {
    const position = parseInt(el.getAttribute(this.config.positionAttr) || '0', 10);
    const visits = (this._visitCounts.get(el) || 0) + 1;
    this._visitCounts.set(el, visits);

    const episode = new Episode(el, position, {
      includeSamples: this.config.includeSamplesInEpisodeJson,
    });
    episode.visitNumber = visits;
    episode.approachVelocity = Math.sqrt(
      this._velocity.vx ** 2 + this._velocity.vy ** 2
    );
    episode.approachAngle = Math.atan2(this._velocity.vy, this._velocity.vx);

    // Forward vs regressive classification at entry time. Mirrors the
    // Python episode_classifier.classify_episode rule: forward iff the
    // current scrollY sits at or within directionTolPx of the running
    // scroll HWM. Include the entry scroll in the HWM comparison so that
    // an entry at a fresh peak is always classified forward.
    const entryScroll = this._scrollY;
    const hwmAtEntry = Math.max(this._scrollHwm, entryScroll);
    const tolPx = this.config.directionTolPx;
    episode.entryScroll = entryScroll;
    episode.hwmAtEntry = hwmAtEntry;
    episode.direction = entryScroll >= hwmAtEntry - tolPx ? 'forward' : 'regressive';

    // Mark prior episodes on this element as deferred (re-approached)
    if (visits > 1) {
      for (const prev of this._episodes) {
        if (prev.resultEl === el && prev.retreated && !prev.reapproached) {
          prev.reapproached = true;
        }
      }
    }

    // Episode-scoped viewport-band baseline. Close the pending session-level
    // interval up to `now` before reading, so the baseline is accurate to
    // the entry instant. At finalize we subtract this from the then-current
    // cumulative band totals to get bands restricted to [enteredAt, exitedAt].
    if (this.config.trackViewportBands) {
      episode._viewportBandsAtEntry = this._snapshotViewportBandsFor(el);
    }

    this._active.set(el, episode);
  }

  _exitResult(el, episode, now) {
    episode.exitedAt = now;
    this._active.delete(el);

    if (episode.dwellMs < this.config.minDwellMs) return;

    if (episode.clicked) {
      // Clicked episodes don't retreat — finalize immediately
      this._finalizeEpisode(episode);
      return;
    }

    // Start tracking retreat distance: cache the AOI center at exit time
    // (before scroll changes invalidate getBoundingClientRect)
    const rect = el.getBoundingClientRect();
    episode._aoiCenter = {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    };
    episode._retreatStart = now;
    episode.retreatDistance = 0;

    this._retreating.push(episode);
  }

  /**
   * Update retreat distances for recently exited episodes.
   * Called on every mousemove. Tracks max distance from AOI center
   * after exit — the actual retreat signal.
   *
   * Episodes graduate out of retreating state when:
   * - The cursor re-enters the same result (→ reapproach, handled in _enterResult)
   * - reapproachWindowMs expires
   * - The cursor enters a different result (commit to new evaluation)
   */
  _updateRetreating(x, y, now) {
    const windowMs = this.config.reapproachWindowMs;
    let i = this._retreating.length;

    while (i--) {
      const ep = this._retreating[i];
      const elapsed = now - ep._retreatStart;

      // Compute distance from AOI center
      const dx = x - ep._aoiCenter.x;
      const dy = y - ep._aoiCenter.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Track maximum retreat distance
      if (dist > ep.retreatDistance) {
        ep.retreatDistance = dist;
      }

      // Graduate when window expires
      if (elapsed >= windowMs) {
        this._retreating.splice(i, 1);
        this._finalizeEpisode(ep);
      }
    }
  }

  /**
   * Graduate retreating episodes when cursor enters a new result.
   * Episodes for the entered result stay (they'll become reapproaches).
   * All others finalize — the user has moved on.
   */
  _graduateRetreating(enteredEl, now) {
    let i = this._retreating.length;
    while (i--) {
      const ep = this._retreating[i];
      if (ep.resultEl !== enteredEl) {
        this._retreating.splice(i, 1);
        this._finalizeEpisode(ep);
      }
    }
  }

  _finalizeEpisode(episode) {
    // Episode-scoped viewport-band deltas. Subtract the entry-time snapshot
    // from the current cumulative totals to get ms restricted to
    // [enteredAt, exitedAt]. Nullable — missing when bands are disabled or
    // the AOI was never observed by the band accumulator.
    if (this.config.trackViewportBands && episode._viewportBandsAtEntry) {
      const cur = this._snapshotViewportBandsFor(episode.resultEl);
      const base = episode._viewportBandsAtEntry;
      episode.viewportBands = {
        any_ms: Math.round(cur.any_ms - base.any_ms),
        top_ms: Math.round(cur.top_ms - base.top_ms),
        mid_ms: Math.round(cur.mid_ms - base.mid_ms),
        bot_ms: Math.round(cur.bot_ms - base.bot_ms),
      };
    }

    // Clean up transient tracking state
    delete episode._aoiCenter;
    delete episode._retreatStart;
    delete episode._viewportBandsAtEntry;

    this._episodes.push(episode);
    if (this.config.onEpisode) {
      this.config.onEpisode(episode.toJSON());
    }
  }

  _onScroll() {
    this._scrollY = window.scrollY;
    if (this._scrollY > this._scrollHwm) {
      this._scrollHwm = this._scrollY;
    }
    if (this.config.trackViewportBands) {
      this._scheduleViewportSnapshot();
    }
  }

  _onResize() {
    this._viewportH = window.innerHeight;
    // Layout may have reflowed. Clear cached geometry so the next snapshot
    // picks up fresh page-space centers and half-heights.
    this._resultPageYCenter.clear();
    this._resultHalfHeight.clear();
    this._scheduleViewportSnapshot();
  }

  /**
   * rAF-throttled scroll/resize/reflow handler for band snapshots. Multiple
   * scroll events within one frame coalesce into a single snapshot, which is
   * enough resolution — band boundaries are defined against scr_h/3, a much
   * coarser scale than per-event scroll deltas.
   */
  _scheduleViewportSnapshot() {
    if (this._viewportSnapshotRafId != null) return;
    if (typeof requestAnimationFrame === 'undefined') {
      // No rAF available (tests, unusual hosts). Fall back to sync snapshot —
      // still correct, just not coalesced.
      this._updateViewportBands(
        typeof performance !== 'undefined' ? performance.now() : Date.now()
      );
      return;
    }
    this._viewportSnapshotRafId = requestAnimationFrame(
      this._runViewportSnapshotRaf
    );
  }

  _runViewportSnapshotRaf() {
    this._viewportSnapshotRafId = null;
    this._updateViewportBands(performance.now());
  }

  /**
   * Update per-AOI viewport-band accumulators.
   *
   * Semantics (mirrors `computeViewportBandsPure` and
   * `viewport_ms_for_trial` in
   * attentional-foraging/scripts/viewport_time_calibration.py):
   *
   * For each observed AOI, close the interval `(lastSnapshotT, now)` using
   * the band that was current *at the start* of the interval (piecewise-
   * constant attribution), then record the new band + intersection state.
   *
   * When `seed` is true, skip the accumulation step — used at init so the
   * first real interval is well-defined. AOIs encountered for the first
   * time are always seeded (regardless of the flag).
   *
   * Band definitions (with `third = scr_h / 3`):
   *   top  iff 0        <= center_vp_y < third
   *   mid  iff third    <= center_vp_y < 2*third
   *   bot  iff 2*third  <= center_vp_y <= scr_h
   *   off  otherwise (includes tall-AOI case where AOI intersects viewport
   *                   but its center sits outside [0, scr_h])
   *
   * `any_ms` accumulates for any viewport intersection (min(a_bot, vp_bot)
   * > max(a_top, vp_top)), including the off-band case.
   */
  _updateViewportBands(now, seed = false) {
    if (!this.config.trackViewportBands && !this.config.trackViewportAnalytics) return;
    const scrH = typeof window !== 'undefined' ? window.innerHeight : this._viewportH;
    if (!scrH || scrH <= 0) return;
    this._viewportH = scrH;
    const third = scrH / 3;
    const scrollY = this._scrollY;
    const centerY = scrH / 2;
    const centerTol = this.config.viewportCenterTolPx;

    // Scroll velocity for this just-closed interval: px/s. Global since the
    // scroll timeline is shared across AOIs. Zero on seed or when dt is 0.
    const globalDt = now - (this._vbLastSnapshotT ?? now);
    const scrollDelta = scrollY - (this._vbLastScrollY ?? scrollY);
    const intervalV =
      globalDt > 0 ? (scrollDelta / globalDt) * 1000 : 0; // px/s
    this._vbLastSnapshotT = now;
    this._vbLastScrollY = scrollY;

    // Union the full tracked-AOI set: visible, feature-tracker-touched, and
    // every currently-matching selector element (covers first-snapshot
    // before the observer has fired).
    const elements = new Set();
    for (const el of this._visibleResults) elements.add(el);
    for (const el of this._approachFeatures.keys()) elements.add(el);
    if (typeof document !== 'undefined') {
      const nodes = document.querySelectorAll(this.config.resultSelector);
      for (const el of nodes) elements.add(el);
    }

    for (const el of elements) {
      // Geometry cache. _resultPageYCenter is shared with the approach-
      // feature path; _resultHalfHeight is this module's sibling cache.
      let pageYCenter = this._resultPageYCenter.get(el);
      let halfH = this._resultHalfHeight.get(el);
      if (pageYCenter === undefined || halfH === undefined) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue; // not laid out yet
        pageYCenter = rect.top + rect.height / 2 + scrollY;
        halfH = rect.height / 2;
        this._resultPageYCenter.set(el, pageYCenter);
        this._resultHalfHeight.set(el, halfH);
      }

      const aoiTop = pageYCenter - halfH;
      const aoiBot = pageYCenter + halfH;
      const aoiH = aoiBot - aoiTop;
      const vpTop = scrollY;
      const vpBot = scrollY + scrH;
      const overlap = Math.min(aoiBot, vpBot) - Math.max(aoiTop, vpTop);
      const intersecting = overlap > 0;
      const overlapFrac = intersecting && aoiH > 0 ? overlap / aoiH : 0;
      const centerVpY = pageYCenter - scrollY;
      const nearCenter =
        intersecting && Math.abs(centerVpY - centerY) <= centerTol;
      let band = 'off';
      if (intersecting) {
        if (centerVpY >= 0 && centerVpY < third) band = 'top';
        else if (centerVpY >= third && centerVpY < 2 * third) band = 'mid';
        else if (centerVpY >= 2 * third && centerVpY <= scrH) band = 'bot';
      }

      let rec = this._viewportBandTimes.get(el);
      if (!rec) {
        this._viewportBandTimes.set(el, {
          // A — banded decomposition (existing; kept for backward compat)
          any_ms: 0,
          top_ms: 0,
          mid_ms: 0,
          bot_ms: 0,
          // B — continuous viewport analytics
          center_ms: 0,
          sum_center_y_ms: 0,
          max_overlap_frac: 0,
          // C — scroll trajectory (minimal NB30 set: min_abs_velocity, n_reversals)
          min_abs_velocity: Infinity,
          n_reversals: 0,
          last_v_sign: 0,
          // D — IAB/MRC Viewable Impression (≥ 50 % pixels in view for
          // ≥ iabViewableThresholdMs continuously)
          ms_at_50pct_or_more: 0,
          current_50pct_stretch_ms: 0,
          iab_viewable: false,
          // State carried into the next interval (the geometry IS the
          // state during the closing interval, piecewise-constant)
          lastSnapshotT: now,
          currentBand: band,
          lastIntersecting: intersecting,
          lastCenterVpY: centerVpY,
          lastOverlapFrac: overlapFrac,
          lastNearCenter: nearCenter,
        });
        continue;
      }

      if (!seed) {
        const dt = now - rec.lastSnapshotT;
        if (dt > 0) {
          // A — banded accumulators (existing)
          if (rec.lastIntersecting) rec.any_ms += dt;
          if (rec.currentBand === 'top') rec.top_ms += dt;
          else if (rec.currentBand === 'mid') rec.mid_ms += dt;
          else if (rec.currentBand === 'bot') rec.bot_ms += dt;

          // B — continuous viewport analytics: attribute interval using the
          // geometry recorded at the START of the interval (lastCenterVpY /
          // lastOverlapFrac / lastNearCenter), matching the piecewise-
          // constant convention used by viewport_time_calibration.py.
          if (rec.lastIntersecting) {
            rec.sum_center_y_ms += rec.lastCenterVpY * dt;
            if (rec.lastOverlapFrac > rec.max_overlap_frac) {
              rec.max_overlap_frac = rec.lastOverlapFrac;
            }
            if (rec.lastNearCenter) rec.center_ms += dt;

            // C — scroll trajectory: min |v| and reversal count, attributed
            // only over intervals the AOI was visible.
            const absV = Math.abs(intervalV);
            if (absV < rec.min_abs_velocity) rec.min_abs_velocity = absV;
            const sign =
              absV < 1e-6 ? 0 : intervalV > 0 ? 1 : -1;
            if (rec.last_v_sign !== 0 && sign !== 0 && sign !== rec.last_v_sign) {
              rec.n_reversals += 1;
            }
            if (sign !== 0) rec.last_v_sign = sign;

            // D — IAB/MRC Viewable Impression: ≥ 50 % pixel overlap
            // maintained for ≥ iabViewableThresholdMs continuously.
            if (rec.lastOverlapFrac >= 0.5) {
              rec.ms_at_50pct_or_more += dt;
              rec.current_50pct_stretch_ms += dt;
              if (
                rec.current_50pct_stretch_ms >=
                this.config.iabViewableThresholdMs
              ) {
                rec.iab_viewable = true;
              }
            } else {
              rec.current_50pct_stretch_ms = 0;
            }
          } else {
            // AOI was not intersecting during the closing interval —
            // any IAB continuity stretch is broken.
            rec.current_50pct_stretch_ms = 0;
          }
        }
      }
      rec.lastSnapshotT = now;
      rec.currentBand = band;
      rec.lastIntersecting = intersecting;
      rec.lastCenterVpY = centerVpY;
      rec.lastOverlapFrac = overlapFrac;
      rec.lastNearCenter = nearCenter;
    }
  }

  /**
   * Force a snapshot up to `now` and return a band record snapshot for `el`.
   * Returns zeros if the element has not yet been seeded — the caller is
   * expected to treat an absent record as "no accumulation yet."
   */
  _snapshotViewportBandsFor(el) {
    if (!this.config.trackViewportBands) {
      return { any_ms: 0, top_ms: 0, mid_ms: 0, bot_ms: 0 };
    }
    const now =
      typeof performance !== 'undefined' ? performance.now() : Date.now();
    this._updateViewportBands(now);
    const rec = this._viewportBandTimes.get(el);
    if (!rec) return { any_ms: 0, top_ms: 0, mid_ms: 0, bot_ms: 0 };
    return {
      any_ms: rec.any_ms,
      top_ms: rec.top_ms,
      mid_ms: rec.mid_ms,
      bot_ms: rec.bot_ms,
    };
  }

  /**
   * Per-position viewport-band dwell totals. Mirrors `getApproachFeatures`
   * in shape: an array of `{ position, vp_any_ms, vp_top_ms, vp_mid_ms,
   * vp_bot_ms }` sorted by position. Values are rounded to integer ms.
   *
   * Forces a snapshot up to now() so callers see fresh totals. Downstream
   * scoring should apply per-rank interaction weights — the vt_top
   * coefficient in the calibration is rank-dependent (+1.96 at P0, +0.46
   * at P4, ~0.2 at P5+; see docs/validation/viewport-bands-calibration.md).
   */
  getViewportBands() {
    if (!this.config.trackViewportBands) return [];
    this._updateViewportBands(
      typeof performance !== 'undefined' ? performance.now() : Date.now()
    );
    const out = [];
    for (const [el, rec] of this._viewportBandTimes) {
      const position = parseInt(
        el.getAttribute(this.config.positionAttr) || '0',
        10
      );
      out.push({
        position,
        vp_any_ms: Math.round(rec.any_ms),
        vp_top_ms: Math.round(rec.top_ms),
        vp_mid_ms: Math.round(rec.mid_ms),
        vp_bot_ms: Math.round(rec.bot_ms),
      });
    }
    return out.sort((a, b) => a.position - b.position);
  }

  /**
   * Metadata describing how band totals were computed — current viewport
   * height and schema tag. The calibration is only basis-stable within a
   * session; mid-session resize shifts the basis for subsequent intervals.
   */
  getViewportBandContext() {
    return {
      viewport_h: this._viewportH,
      schema: 'edmonds-2026-vpbands-v1',
    };
  }

  /**
   * Per-position continuous viewport analytics + scroll trajectory.
   * Mirrors `getViewportBands` in shape: an array of
   * `{ position, vt_any_ms, vt_center_ms, avg_viewport_y_px,
   *    max_overlap_frac, min_abs_velocity_px_per_s, n_reversals }`
   * sorted by position. Values are accumulators over the full scroll
   * timeline for each AOI (matches NB30's per-(trial, position) feature
   * extraction).
   *
   * Minimal feature set (NB30 K18 forward-selection): this is the
   * parsimonious B∪C' that recovers the K13 deferred-vs-rejected lift.
   * pause_ms is NOT emitted (collinear with vt_any_ms at r=0.995, K17).
   * Bands (vt_top_ms / vt_mid_ms / vt_bot_ms) remain on
   * `getViewportBands` for callers who want the banded decomposition.
   */
  getViewportAnalytics() {
    if (!this.config.trackViewportAnalytics) return [];
    this._updateViewportBands(
      typeof performance !== 'undefined' ? performance.now() : Date.now()
    );
    const out = [];
    for (const [el, rec] of this._viewportBandTimes) {
      const position = parseInt(
        el.getAttribute(this.config.positionAttr) || '0',
        10
      );
      const avgVpY = rec.any_ms > 0 ? rec.sum_center_y_ms / rec.any_ms : 0;
      const minAbsV =
        rec.min_abs_velocity === Infinity ? 0 : rec.min_abs_velocity;
      out.push({
        position,
        vt_any_ms: Math.round(rec.any_ms),
        vt_center_ms: Math.round(rec.center_ms),
        avg_viewport_y_px: Math.round(avgVpY),
        max_overlap_frac: Number(rec.max_overlap_frac.toFixed(4)),
        min_abs_velocity_px_per_s: Number(minAbsV.toFixed(2)),
        n_reversals: rec.n_reversals,
        ms_at_50pct_or_more: Math.round(rec.ms_at_50pct_or_more),
        iab_viewable: rec.iab_viewable,
      });
    }
    return out.sort((a, b) => a.position - b.position);
  }

  /**
   * Metadata describing how analytics totals were computed — schema tag,
   * the threshold used for vt_center_ms, and the IAB viewability
   * continuity threshold.
   */
  getViewportAnalyticsContext() {
    return {
      viewport_h: this._viewportH,
      viewport_center_tol_px: this.config.viewportCenterTolPx,
      iab_viewable_threshold_ms: this.config.iabViewableThresholdMs,
      schema: 'edmonds-2026-vpanalytics-v1',
    };
  }

  /**
   * Update the nine M4 approach-feature running aggregates for every
   * visible result. Lazy-initializes a tracker the first time a result
   * is seen, caching its page-space Y center (scroll-invariant).
   *
   * Matches the whole-trial aggregation window used by the paper's
   * canonical extractor: features are computed against each result's
   * center using ALL mousemove samples, not restricted to approach
   * episodes. The §4.4 phase-restriction ablation in the paper
   * empirically validates that the Survey-phase cursor contributes
   * no signal, so whole-trial aggregation and Evaluate-phase aggregation
   * give essentially the same feature vector.
   */
  _updateApproachFeatures(pageY, t) {
    const proximityPx = this.config.approachFeatureProximityPx;
    const results = document.querySelectorAll(this.config.resultSelector);

    for (const el of results) {
      // Respect visibility filter if IntersectionObserver is enabled —
      // results that never entered the viewport aren't meaningfully
      // available to the cursor and shouldn't receive feature aggregates.
      if (this._observer && !this._visibleResults.has(el)) continue;

      // Lazy cache the result's page-space Y center. getBoundingClientRect
      // is viewport-relative; adding scrollY converts to page coordinates,
      // which are stable across subsequent scrolls.
      let tracker = this._approachFeatures.get(el);
      if (!tracker) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue; // not laid out yet
        const pageYCenter = rect.top + rect.height / 2 + this._scrollY;
        this._resultPageYCenter.set(el, pageYCenter);
        // Shared geometry cache with the band accumulator path. Populating
        // here avoids a second getBoundingClientRect when bands are enabled.
        this._resultHalfHeight.set(el, rect.height / 2);
        tracker = new ResultFeatureTracker(pageYCenter, proximityPx);
        this._approachFeatures.set(el, tracker);
      }
      tracker.update(pageY, t);
    }
  }

  /**
   * Return the nine M4 approach features per result as a plain array
   * sorted by rank position. Each entry contains `position` plus the
   * nine feature values, reproducing the per-(trial, result) record
   * schema in attentional-foraging/scripts/m4_nb21_hybrid_rerun.py.
   *
   * This is the canonical feature vector referenced throughout the
   * CIKM 2026 paper (§3.3, §4.1). Feed these directly into a trained
   * M4 click-predictor or M5 deferred-class detector.
   */
  getApproachFeatures() {
    const out = [];
    for (const [el, tracker] of this._approachFeatures) {
      const position = parseInt(
        el.getAttribute(this.config.positionAttr) || '0', 10);
      out.push({ position, ...tracker.getFeatures() });
    }
    return out.sort((a, b) => a.position - b.position);
  }

  _onClick(e) {
    const resultEl = e.target.closest(this.config.resultSelector);
    if (!resultEl) return;

    const episode = this._active.get(resultEl);
    if (episode) {
      episode.clicked = true;
      episode.clickedAt = performance.now();
    }

    if (this.config.onClick) {
      const position = parseInt(resultEl.getAttribute(this.config.positionAttr) || '0', 10);
      this.config.onClick({
        position,
        episode: episode ? episode.toJSON() : null,
        target: resultEl,        // the SERP result container (kept for demo callers)
        element: e.target,       // the specific DOM node that was clicked —
                                 // lets adapters identify the link/button that
                                 // got the click, aligned with clicksense target_* fields
      });
    }
  }

  /**
   * Get approach-retreat summary for all results.
   * Returns an array of relevance signals suitable for reranking.
   * Includes four-class taxonomy counts per position.
   */
  getSignals() {
    const byPosition = new Map();

    for (const ep of this._episodes) {
      if (!byPosition.has(ep.position)) {
        byPosition.set(ep.position, {
          position: ep.position,
          outcome: null,  // resolved below
          total_dwell_ms: 0,
          mean_retreat_distance: 0,
          visit_count: 0,
          retreat_count: 0,
          reapproach_count: 0,
          clicked: false,
          max_visit_number: 0,
          _retreat_distances: [],
        });
      }
      const s = byPosition.get(ep.position);
      s.total_dwell_ms += ep.dwellMs;
      s.visit_count++;
      if (ep.retreated) {
        s.retreat_count++;
        s._retreat_distances.push(ep.retreatDistance);
      }
      if (ep.visitNumber > 1) s.reapproach_count++;
      if (ep.clicked) s.clicked = true;
      if (ep.visitNumber > s.max_visit_number) s.max_visit_number = ep.visitNumber;
    }

    const results = Array.from(byPosition.values()).map((s) => {
      // Resolve outcome: use the latest episode's outcome for this position
      s.outcome = s.clicked
        ? Outcome.CLICKED
        : s.reapproach_count > 0
          ? Outcome.DEFERRED
          : Outcome.EVALUATED_REJECTED;

      // Mean retreat distance
      if (s._retreat_distances.length > 0) {
        s.mean_retreat_distance = Math.round(
          s._retreat_distances.reduce((a, b) => a + b, 0) / s._retreat_distances.length
        );
      }
      delete s._retreat_distances;
      return s;
    });

    // Add NOT_APPROACHED for visible results with no episodes
    const allResults = document.querySelectorAll(this.config.resultSelector);
    const approachedPositions = new Set(results.map((r) => r.position));
    for (const el of allResults) {
      const pos = parseInt(el.getAttribute(this.config.positionAttr) || '0', 10);
      if (!approachedPositions.has(pos) && this._visibleResults.has(el)) {
        results.push({
          position: pos,
          outcome: Outcome.NOT_APPROACHED,
          total_dwell_ms: 0,
          mean_retreat_distance: 0,
          visit_count: 0,
          retreat_count: 0,
          reapproach_count: 0,
          clicked: false,
          max_visit_number: 0,
        });
      }
    }

    return results.sort((a, b) => a.position - b.position);
  }

  /**
   * Classify all results into the four-class taxonomy.
   * Returns { clicked: [], deferred: [], evaluated_rejected: [], not_approached: [] }
   */
  classify() {
    const signals = this.getSignals();
    const classes = {
      [Outcome.CLICKED]: [],
      [Outcome.DEFERRED]: [],
      [Outcome.EVALUATED_REJECTED]: [],
      [Outcome.NOT_APPROACHED]: [],
    };
    for (const s of signals) {
      if (s.outcome && classes[s.outcome]) {
        classes[s.outcome].push(s);
      }
    }
    return classes;
  }

  /**
   * Compute a simple relevance score from approach-retreat signals.
   * Higher = more engagement. Used for adaptive reranking.
   *
   * Weights:
   * - Dwell time (normalized): primary signal
   * - Re-approaches: strong reconsideration signal
   * - Retreats: negative signal (but less weight — retreats are normal)
   * - Click: strong positive
   */
  computeRelevance() {
    const signals = this.getSignals();
    if (signals.length === 0) return [];

    const maxDwell = Math.max(...signals.map((s) => s.total_dwell_ms), 1);

    return signals.map((s) => ({
      position: s.position,
      score:
        (s.total_dwell_ms / maxDwell) * 0.4 +
        Math.min(s.reapproach_count / 3, 1) * 0.3 +
        (s.clicked ? 0.3 : 0) -
        (s.retreat_count > 2 ? 0.1 : 0),
      signals: s,
    }));
  }

  /**
   * Get all completed episodes as JSON.
   */
  getEpisodes() {
    return this._episodes.map((ep) => ep.toJSON());
  }

  /**
   * Finalize all in-flight episodes without clearing history.
   * Graduates active (under-cursor) and retreating episodes to the finalized
   * list so getEpisodes / classify / getSignals reflect everything so far.
   * Call before capturing a session summary (e.g. on pagehide / visibilitychange).
   */
  flush() {
    const now = performance.now();
    // Close the pending band interval up to now so session-level totals are
    // fresh before any consumer reads them.
    if (this.config.trackViewportBands) {
      this._updateViewportBands(now);
    }
    // Exit and finalize active episodes
    for (const [el, episode] of this._active) {
      this._exitResult(el, episode, now);
    }
    this._active.clear();
    // Finalize any still-retreating episodes
    for (const ep of this._retreating) {
      this._finalizeEpisode(ep);
    }
    this._retreating = [];
  }

  /**
   * Reset all tracked state. Call after reranking.
   */
  reset() {
    // Flush any retreating episodes before reset
    for (const ep of this._retreating) {
      this._finalizeEpisode(ep);
    }
    this._retreating = [];
    this._episodes = [];
    this._active.clear();
    this._visitCounts.clear();
    this._approachFeatures.clear();
    this._resultPageYCenter.clear();
    this._resultHalfHeight.clear();
    this._viewportBandTimes.clear();
  }

  destroy() {
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('click', this._onClick, { capture: true });
    document.removeEventListener('scroll', this._onScroll);
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', this._onResize);
    }
    if (this._observer) this._observer.disconnect();
    if (this._resizeObserver) this._resizeObserver.disconnect();
    if (
      this._viewportSnapshotRafId != null &&
      typeof cancelAnimationFrame !== 'undefined'
    ) {
      cancelAnimationFrame(this._viewportSnapshotRafId);
    }
    this._viewportSnapshotRafId = null;
    this._active.clear();
    this._retreating = [];
    this._approachFeatures.clear();
    this._resultPageYCenter.clear();
    this._resultHalfHeight.clear();
    this._viewportBandTimes.clear();
  }
}
