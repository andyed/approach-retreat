/**
 * PostHog adapter for ApproachRetreat.
 * Flattens episode data to PostHog event properties.
 */
export function createPostHogAdapter(posthog, eventName = 'serp_episode') {
  return {
    onEpisode(episode) {
      posthog.capture(eventName, {
        ar_position: episode.position,
        ar_dwell_ms: episode.dwell_ms,
        ar_clicked: episode.clicked,
        ar_retreated: episode.retreated,
        ar_visit_number: episode.visit_number,
        ar_approach_velocity: episode.approach_velocity,
        ar_peak_velocity: episode.peak_velocity,
        ar_sample_count: episode.sample_count,
      });
    },
    onClick(click) {
      posthog.capture('serp_click', {
        ar_position: click.position,
        ar_dwell_before_click: click.episode?.dwell_ms,
        ar_visit_before_click: click.episode?.visit_number,
      });
    },
  };
}
