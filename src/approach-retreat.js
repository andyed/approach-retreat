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
    };
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

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onScroll = this._onScroll.bind(this);
    this._onClick = this._onClick.bind(this);

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
        },
        { threshold: 0.3 }
      );
      this._observeResults();
    }
  }

  _observeResults() {
    const results = document.querySelectorAll(this.config.resultSelector);
    for (const el of results) {
      if (this._observer) this._observer.observe(el);
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
    // Clean up transient tracking state
    delete episode._aoiCenter;
    delete episode._retreatStart;

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
        target: resultEl,
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
  }

  destroy() {
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('click', this._onClick, { capture: true });
    document.removeEventListener('scroll', this._onScroll);
    if (this._observer) this._observer.disconnect();
    this._active.clear();
    this._retreating = [];
    this._approachFeatures.clear();
    this._resultPageYCenter.clear();
  }
}
