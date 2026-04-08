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
 * - Retreat distance: how far cursor moves after leaving — encodes rejection
 *   confidence (self-imposed re-acquisition cost, epistemic action)
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
};

/**
 * A single approach-retreat episode on one result.
 */
class Episode {
  constructor(resultEl, position) {
    this.resultEl = resultEl;
    this.position = position;
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
    return {
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
      entered_at: this.enteredAt,
      exited_at: this.exitedAt,
      clicked_at: this.clickedAt,
    };
  }
}

export class ApproachRetreat {
  constructor(options = {}) {
    this.config = { ...DEFAULTS, ...options };
    this._episodes = [];       // all completed episodes
    this._active = new Map();  // resultEl → current Episode
    this._visitCounts = new Map(); // resultEl → visit count
    this._lastMouse = null;    // {x, y, t}
    this._velocity = { vx: 0, vy: 0 };
    this._scrollY = window.scrollY;
    this._observer = null;
    this._visibleResults = new Set();

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

    // Compute velocity
    if (this._lastMouse) {
      const dt = now - this._lastMouse.t;
      if (dt > 0) {
        this._velocity.vx = (x - this._lastMouse.x) / dt;
        this._velocity.vy = (y - this._lastMouse.y) / dt;
      }
    }
    this._lastMouse = { x, y, t: now };

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

    // Handle state transitions
    if (hitResult) {
      if (!this._active.has(hitResult)) {
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

    const episode = new Episode(el, position);
    episode.visitNumber = visits;
    episode.approachVelocity = Math.sqrt(
      this._velocity.vx ** 2 + this._velocity.vy ** 2
    );
    episode.approachAngle = Math.atan2(this._velocity.vy, this._velocity.vx);

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

    if (episode.dwellMs >= this.config.minDwellMs) {
      // Compute retreat distance: track cursor distance from AOI center
      // over subsequent mousemove events. For now, snapshot the distance
      // at exit using the last known mouse position vs AOI center.
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      if (this._lastMouse) {
        episode.retreatDistance = Math.sqrt(
          (this._lastMouse.x - cx) ** 2 + (this._lastMouse.y - cy) ** 2
        );
      }

      this._episodes.push(episode);
      if (this.config.onEpisode) {
        this.config.onEpisode(episode.toJSON());
      }
    }
  }

  _onScroll() {
    this._scrollY = window.scrollY;
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
   * Reset all tracked state. Call after reranking.
   */
  reset() {
    this._episodes = [];
    this._active.clear();
    this._visitCounts.clear();
  }

  destroy() {
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('click', this._onClick, { capture: true });
    document.removeEventListener('scroll', this._onScroll);
    if (this._observer) this._observer.disconnect();
    this._active.clear();
  }
}
