/**
 * PostHog adapter for ApproachRetreat — full capture.
 *
 * Captures every field in Episode.toJSON() plus page-level session context,
 * plus a session summary event on page unload with four-class taxonomy counts
 * and time-to-first-click.
 *
 * Usage:
 *   import posthog from 'posthog-js';
 *   import { createPostHogAdapter, buildSessionContext, isPostHogDisabled }
 *     from '../src/adapters/posthog.js';
 *
 *   const adapter = createPostHogAdapter(posthog, {
 *     context: buildSessionContext({ ar_layout: 'narrow-vertical' }),
 *     disabled: isPostHogDisabled(),
 *   });
 *   const ar = new ApproachRetreat({
 *     onEpisode: adapter.onEpisode,
 *     onClick: adapter.onClick,
 *   });
 *   adapter.bind(ar);
 */

/**
 * Build a static session-level context object suitable for merging into
 * every captured event. Call once at page load.
 *
 * @param {object} extra — additional static context (e.g. { ar_layout, ar_query_id })
 */
export function buildSessionContext(extra = {}) {
  const url = new URL(window.location.href);
  const sid =
    (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `ar-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  return {
    ar_session_id: sid,
    ar_page_path: url.pathname,
    ar_query_param: url.searchParams.get('q') || null,
    ar_viewport_w: window.innerWidth,
    ar_viewport_h: window.innerHeight,
    ar_dpr: window.devicePixelRatio || 1,
    ar_ua: navigator.userAgent,
    ar_referrer: document.referrer || null,
    ar_loaded_at: Date.now(),
    ...extra,
  };
}

/**
 * ?ph=0 dev kill-switch. When the URL carries ?ph=0 the adapter is a no-op
 * so local development doesn't pollute the real PostHog project.
 */
export function isPostHogDisabled() {
  try {
    return new URL(window.location.href).searchParams.get('ph') === '0';
  } catch {
    return false;
  }
}

/**
 * Downsample an episode's raw samples[] to a compact flat trajectory array
 * suitable for shipping as a PostHog event property. Format "xytvxvy/1":
 *   [x, y, t_rel_ms, vx, vy, x, y, t_rel_ms, vx, vy, ...]
 *
 * Coordinates are rounded to integers, time is relative to the first kept
 * sample in ms, velocities are clipped to 3 decimals. Keeps every `stride`-th
 * sample (stride=10 → 10% sample rate from a ~60Hz mousemove stream).
 *
 * Returns null if no samples available or stride invalid.
 */
function buildTrajectory(samples, stride) {
  if (!samples || samples.length === 0 || !stride || stride < 1) return null;
  const flat = [];
  const entryT = samples[0].t;
  for (let i = 0; i < samples.length; i += stride) {
    const s = samples[i];
    flat.push(
      Math.round(s.x),
      Math.round(s.y),
      Math.round(s.t - entryT),
      Math.round(s.vx * 1000) / 1000,
      Math.round(s.vy * 1000) / 1000
    );
  }
  return flat;
}

/**
 * Extract DOM target metadata using the clicksense v0.2 vocabulary so
 * ar_click events can be joined against click_confidence on a shared key
 * (target_href, target_name, target_path). Kept inline rather than imported
 * to preserve approach-retreat's intentional schema independence.
 */
function extractTargetFields(el, pathDepth = 3) {
  if (!el || !el.tagName) return {};
  // Walk up to nearest meaningful element, same as clicksense
  const meaningful = el.closest('a, button, [role="button"], input, select, label, [data-clicksense]');
  const use = meaningful || el;

  const out = { target_tag: use.tagName.toLowerCase() };

  if (use.id) out.target_id = use.id;
  const label = use.getAttribute('data-clicksense');
  if (label) out.target_label = label;
  if (use.tagName === 'A' && use.href) out.target_href = use.href;

  const text = (use.innerText || use.textContent || '').trim();
  if (text.length > 0) out.target_text = text.substring(0, 80);

  const aria = use.getAttribute('aria-label');
  if (aria) out.target_aria_label = aria.substring(0, 80);
  const title = use.getAttribute('title');
  if (title) out.target_title = title.substring(0, 80);

  // data-* attributes flattened as target_data_<key>
  const attrs = use.attributes;
  for (let i = 0; i < attrs.length; i++) {
    const a = attrs[i];
    if (a.name.startsWith('data-') && a.name !== 'data-clicksense') {
      const key = a.name.slice(5).replace(/[^a-zA-Z0-9_-]/g, '_');
      out['target_data_' + key] = String(a.value).substring(0, 80);
    }
  }

  // Computed accessible name
  out.target_name =
    out.target_label ||
    out.target_aria_label ||
    out.target_id ||
    out.target_text ||
    out.target_title ||
    out.target_tag;

  // Short CSS path
  out.target_path = computePath(use, pathDepth);
  return out;
}

function computePath(el, depth) {
  const parts = [];
  let cur = el;
  let steps = 0;
  const max = Math.max(0, depth | 0);
  while (cur && cur.tagName && cur.tagName !== 'BODY' && cur.tagName !== 'HTML' && steps <= max) {
    parts.unshift(selectorFor(cur));
    cur = cur.parentElement;
    steps++;
  }
  return parts.join(' > ');
}

function selectorFor(el) {
  let sel = el.tagName.toLowerCase();
  if (el.id) return sel + '#' + el.id;
  const classList = (el.className && typeof el.className === 'string')
    ? el.className.trim().split(/\s+/)
    : [];
  const useful = classList
    .filter((c) => c && /^[a-zA-Z_][\w-]*$/.test(c))
    .slice(0, 2);
  if (useful.length > 0) sel += '.' + useful.join('.');
  const parent = el.parentElement;
  if (parent) {
    let idx = 1;
    let sawSibling = false;
    for (let i = 0; i < parent.children.length; i++) {
      const sib = parent.children[i];
      if (sib === el) break;
      if (sib.tagName === el.tagName) { idx++; sawSibling = true; }
    }
    if (!sawSibling) {
      for (let i = 0; i < parent.children.length; i++) {
        const sib = parent.children[i];
        if (sib !== el && sib.tagName === el.tagName) { sawSibling = true; break; }
      }
    }
    if (sawSibling) sel += ':nth-of-type(' + idx + ')';
  }
  return sel;
}

/**
 * Flatten an Episode.toJSON() payload to PostHog-friendly properties.
 * Prefixed with ar_ so they co-exist cleanly with other event properties.
 */
function flattenEpisode(episode) {
  return {
    ar_position: episode.position,
    ar_outcome: episode.outcome,
    ar_dwell_ms: episode.dwell_ms,
    ar_visited: episode.visited,
    ar_clicked: episode.clicked,
    ar_retreated: episode.retreated,
    ar_retreat_distance: episode.retreat_distance,
    ar_visit_number: episode.visit_number,
    ar_approach_velocity: episode.approach_velocity,
    ar_approach_angle: episode.approach_angle,
    ar_peak_velocity: episode.peak_velocity,
    ar_min_velocity: episode.min_velocity,
    ar_sample_count: episode.sample_count,
    ar_direction: episode.direction,
    ar_entry_scroll: episode.entry_scroll,
    ar_hwm_at_entry: episode.hwm_at_entry,
    ar_entered_at: episode.entered_at,
    ar_exited_at: episode.exited_at,
    ar_clicked_at: episode.clicked_at,
    // Per-episode viewport-band dwell, scoped to [entered_at, exited_at].
    // Null when the library was initialized with trackViewportBands: false.
    // Calibration source: attentional-foraging/scripts/viewport_time_calibration.py
    ar_vp_any_ms: episode.vp_any_ms ?? null,
    ar_vp_top_ms: episode.vp_top_ms ?? null,
    ar_vp_mid_ms: episode.vp_mid_ms ?? null,
    ar_vp_bot_ms: episode.vp_bot_ms ?? null,
  };
}

/**
 * Create a PostHog adapter. Pass the returned adapter's onEpisode/onClick
 * to the ApproachRetreat constructor, then call adapter.bind(ar) to wire
 * session-summary capture on pagehide/visibilitychange.
 *
 * @param {object} posthog — a posthog-js instance (must expose .capture)
 * @param {object} options
 * @param {string} [options.eventName='ar_episode']
 * @param {string} [options.clickEventName='ar_click']
 * @param {string} [options.summaryEventName='ar_session_summary']
 * @param {object|function} [options.context={}] — merged into every event;
 *        pass a function if you need lazy evaluation
 * @param {boolean} [options.disabled=false] — no-op mode for dev
 * @param {number} [options.trajectoryStride=10] — keep every Nth raw cursor
 *        sample from each episode and ship as ar_trajectory (flat array).
 *        0 disables trajectory capture. Requires the library to be
 *        constructed with { includeSamplesInEpisodeJson: true }.
 * @param {number} [options.targetPathDepth=3] — ancestors walked when
 *        building target_path on ar_click events (clicksense-aligned).
 */
export function createPostHogAdapter(posthog, options = {}) {
  const {
    eventName = 'ar_episode',
    clickEventName = 'ar_click',
    summaryEventName = 'ar_session_summary',
    context = {},
    disabled = false,
    trajectoryStride = 10,
    targetPathDepth = 3,
  } = options;

  const getCtx = typeof context === 'function' ? context : () => context;

  if (disabled || !posthog || typeof posthog.capture !== 'function') {
    return {
      onEpisode() {},
      onClick() {},
      captureSummary() {},
      bind() {},
      _disabled: true,
    };
  }

  let bound = false;

  const adapter = {
    onEpisode(episode) {
      const props = {
        ...flattenEpisode(episode),
        ...getCtx(),
      };
      if (trajectoryStride > 0 && episode.samples) {
        const flat = buildTrajectory(episode.samples, trajectoryStride);
        if (flat) {
          props.ar_trajectory = flat;
          props.ar_trajectory_format = 'xytvxvy/1';
          props.ar_trajectory_stride = trajectoryStride;
          props.ar_trajectory_sample_count = flat.length / 5;
          props.ar_trajectory_raw_sample_count = episode.samples.length;
        }
      }
      posthog.capture(eventName, props);
    },

    onClick(click) {
      const ep = click.episode || {};
      // Extract DOM target fields using clicksense v0.2 vocabulary so
      // ar_click events are joinable with click_confidence on shared keys
      // (target_href, target_name, target_path). Prefer click.element (the
      // actual clicked node); fall back to click.target (result container).
      const targetFields = extractTargetFields(
        click.element || click.target,
        targetPathDepth
      );
      posthog.capture(clickEventName, {
        ar_position: click.position,
        ar_dwell_before_click: ep.dwell_ms ?? null,
        ar_visit_before_click: ep.visit_number ?? null,
        ar_approach_velocity_before_click: ep.approach_velocity ?? null,
        ar_approach_angle_before_click: ep.approach_angle ?? null,
        ar_direction_before_click: ep.direction ?? null,
        ar_retreat_distance_before_click: ep.retreat_distance ?? null,
        ar_sample_count_before_click: ep.sample_count ?? null,
        ...targetFields,
        ...getCtx(),
      });
    },

    /**
     * Capture a session summary event. Flushes any in-flight episodes first
     * so the classify() counts include everything.
     *
     * Also captures the nine M4 approach features per result position via
     * ar.getApproachFeatures(). These are the canonical feature vector
     * referenced by the Edmonds 2026 CIKM paper (§3.3, §4.1) and are the
     * input M4 click predictors and M5 deferred-class detectors consume.
     * They are whole-trial running aggregates against each result's
     * page-space center, not per-episode — a cursor that never entered
     * an AOI still has a nine-feature record for that result.
     */
    captureSummary(ar) {
      if (typeof ar.flush === 'function') ar.flush();

      const episodes = ar.getEpisodes();
      const classes = ar.classify();

      const firstClick = episodes.find((e) => e.clicked);
      const sessionStart = episodes.length > 0 ? episodes[0].entered_at : null;
      const timeToFirstClickMs =
        firstClick && sessionStart != null
          ? Math.round(firstClick.clicked_at - sessionStart)
          : null;

      const forwardCount = episodes.filter((e) => e.direction === 'forward').length;
      const regressiveCount = episodes.filter((e) => e.direction === 'regressive').length;

      const positions = (cls) => (classes[cls] || []).map((s) => s.position);
      const totalDwellMs = episodes.reduce((sum, e) => sum + (e.dwell_ms || 0), 0);
      const maxPositionApproached = episodes.reduce(
        (m, e) => Math.max(m, e.position ?? 0),
        -1
      );

      const approachFeatures =
        typeof ar.getApproachFeatures === 'function' ? ar.getApproachFeatures() : [];

      // Merge per-AOI viewport-band totals into the approach-features array
      // on `position`. Augmentative — the nine-feature schema is unchanged;
      // band fields are nullable on rows that have no band record. AOIs
      // with a band record but no approach-feature tracker (cursor never
      // drove a tracker) are appended as band-only rows. Calibration source:
      // attentional-foraging/scripts/viewport_time_calibration.py.
      const viewportBands =
        typeof ar.getViewportBands === 'function' ? ar.getViewportBands() : [];
      const bandByPosition = new Map(viewportBands.map((b) => [b.position, b]));
      const viewportAnalytics =
        typeof ar.getViewportAnalytics === 'function'
          ? ar.getViewportAnalytics()
          : [];
      const analyticsByPosition = new Map(
        viewportAnalytics.map((a) => [a.position, a])
      );
      const seen = new Set();
      const mergedFeatures = approachFeatures.map((f) => {
        seen.add(f.position);
        const b = bandByPosition.get(f.position);
        const a = analyticsByPosition.get(f.position);
        return {
          ...f,
          vp_any_ms: b ? b.vp_any_ms : null,
          vp_top_ms: b ? b.vp_top_ms : null,
          vp_mid_ms: b ? b.vp_mid_ms : null,
          vp_bot_ms: b ? b.vp_bot_ms : null,
          vt_center_ms: a ? a.vt_center_ms : null,
          avg_viewport_y_px: a ? a.avg_viewport_y_px : null,
          max_overlap_frac: a ? a.max_overlap_frac : null,
          min_abs_velocity_px_per_s: a ? a.min_abs_velocity_px_per_s : null,
          n_reversals: a ? a.n_reversals : null,
          ms_at_50pct_or_more: a ? a.ms_at_50pct_or_more : null,
          iab_viewable: a ? a.iab_viewable : null,
        };
      });
      for (const b of viewportBands) {
        if (seen.has(b.position)) continue;
        const a = analyticsByPosition.get(b.position);
        seen.add(b.position);
        mergedFeatures.push({
          position: b.position,
          vp_any_ms: b.vp_any_ms,
          vp_top_ms: b.vp_top_ms,
          vp_mid_ms: b.vp_mid_ms,
          vp_bot_ms: b.vp_bot_ms,
          vt_center_ms: a ? a.vt_center_ms : null,
          avg_viewport_y_px: a ? a.avg_viewport_y_px : null,
          max_overlap_frac: a ? a.max_overlap_frac : null,
          min_abs_velocity_px_per_s: a ? a.min_abs_velocity_px_per_s : null,
          n_reversals: a ? a.n_reversals : null,
          ms_at_50pct_or_more: a ? a.ms_at_50pct_or_more : null,
          iab_viewable: a ? a.iab_viewable : null,
        });
      }
      for (const a of viewportAnalytics) {
        if (seen.has(a.position)) continue;
        mergedFeatures.push({
          position: a.position,
          vt_center_ms: a.vt_center_ms,
          avg_viewport_y_px: a.avg_viewport_y_px,
          max_overlap_frac: a.max_overlap_frac,
          min_abs_velocity_px_per_s: a.min_abs_velocity_px_per_s,
          n_reversals: a.n_reversals,
          ms_at_50pct_or_more: a.ms_at_50pct_or_more,
          iab_viewable: a.iab_viewable,
        });
      }
      mergedFeatures.sort((a, b) => a.position - b.position);

      const bandContext =
        typeof ar.getViewportBandContext === 'function'
          ? ar.getViewportBandContext()
          : { viewport_h: null, schema: null };
      const analyticsContext =
        typeof ar.getViewportAnalyticsContext === 'function'
          ? ar.getViewportAnalyticsContext()
          : { viewport_h: null, viewport_center_tol_px: null, schema: null };

      posthog.capture(summaryEventName, {
        ar_total_episodes: episodes.length,
        ar_total_clicked: (classes.clicked || []).length,
        ar_total_deferred: (classes.deferred || []).length,
        ar_total_rejected: (classes.evaluated_rejected || []).length,
        ar_total_not_approached: (classes.not_approached || []).length,
        ar_positions_clicked: positions('clicked'),
        ar_positions_deferred: positions('deferred'),
        ar_positions_rejected: positions('evaluated_rejected'),
        ar_positions_not_approached: positions('not_approached'),
        ar_forward_count: forwardCount,
        ar_regressive_count: regressiveCount,
        ar_total_dwell_ms: Math.round(totalDwellMs),
        ar_time_to_first_click_ms: timeToFirstClickMs,
        ar_max_position_approached: maxPositionApproached >= 0 ? maxPositionApproached : null,
        ar_approach_features: mergedFeatures,
        ar_approach_feature_schema: 'edmonds-2026-m4-v1',
        ar_viewport_band_schema: bandContext.schema,
        ar_viewport_band_basis_px: bandContext.viewport_h,
        ar_viewport_analytics_schema: analyticsContext.schema,
        ar_viewport_center_tol_px: analyticsContext.viewport_center_tol_px,
        ar_iab_viewable_threshold_ms: analyticsContext.iab_viewable_threshold_ms,
        ...getCtx(),
      });
    },

    /**
     * Wire automatic session-summary capture on page unload.
     * Uses visibilitychange (hidden) and pagehide because beforeunload is
     * unreliable on mobile and bfcache-enabled browsers. Idempotent — the
     * summary fires at most once per bind() call.
     */
    bind(ar) {
      if (bound) return;
      bound = true;

      let fired = false;
      const fire = () => {
        if (fired) return;
        fired = true;
        this.captureSummary(ar);
      };

      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') fire();
      });
      window.addEventListener('pagehide', fire);
    },
  };

  return adapter;
}
