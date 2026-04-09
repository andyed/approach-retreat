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
 */
export function createPostHogAdapter(posthog, options = {}) {
  const {
    eventName = 'ar_episode',
    clickEventName = 'ar_click',
    summaryEventName = 'ar_session_summary',
    context = {},
    disabled = false,
    trajectoryStride = 10,
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
      posthog.capture(clickEventName, {
        ar_position: click.position,
        ar_dwell_before_click: ep.dwell_ms ?? null,
        ar_visit_before_click: ep.visit_number ?? null,
        ar_approach_velocity_before_click: ep.approach_velocity ?? null,
        ar_approach_angle_before_click: ep.approach_angle ?? null,
        ar_direction_before_click: ep.direction ?? null,
        ar_retreat_distance_before_click: ep.retreat_distance ?? null,
        ar_sample_count_before_click: ep.sample_count ?? null,
        ...getCtx(),
      });
    },

    /**
     * Capture a session summary event. Flushes any in-flight episodes first
     * so the classify() counts include everything.
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
