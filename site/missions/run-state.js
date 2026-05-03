/**
 * Run-state module for the movie-mission flow.
 *
 * A "run" is a single dogfooder pass through some or all of the six movie
 * missions. State lives in localStorage so the user can bail and return,
 * redo missions, and revisit their generated prompt via permalink.
 *
 * Mission order is randomized at run creation to remove order effects from
 * the calibration data.
 */

const STORE_KEY = 'ar_runs_v1';

export const MISSION_IDS = [
  'date-night',
  'kids-saturday',
  'extended-family',
  'solo-wind-down',
  'teen-sleepover',
  'rainy-sunday-afternoon',
];

export const MISSION_LABELS = {
  'date-night': 'Date night',
  'kids-saturday': 'Kids on Saturday',
  'extended-family': 'Extended family',
  'solo-wind-down': 'Solo wind-down',
  'teen-sleepover': 'Teen sleepover',
  'rainy-sunday-afternoon': 'Rainy Sunday afternoon',
};

export const MISSION_INSTRUCTIONS = {
  'date-night':
    "Pick the movie you'd actually want to watch tonight with your partner.",
  'kids-saturday':
    "Pick the movie you'd actually put on for the kids this Saturday morning.",
  'extended-family':
    "Pick the movie you'd actually put on with the whole extended family in the room.",
  'solo-wind-down':
    'Pick the movie you actually want to watch alone tonight, lights low.',
  'teen-sleepover':
    "Pick the movie you'd actually put on for a 14-year-old's sleepover crowd.",
  'rainy-sunday-afternoon':
    "Pick the movie you'd actually want playing on a rainy Sunday with nothing to do.",
};

function emptyStore() {
  return { version: 1, active_run: null, runs: {} };
}

export function loadStore() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return emptyStore();
    if (!parsed.runs) parsed.runs = {};
    return parsed;
  } catch (e) {
    console.warn('run-state: corrupt store, resetting', e);
    return emptyStore();
  }
}

function saveStore(store) {
  localStorage.setItem(STORE_KEY, JSON.stringify(store));
}

function shortId() {
  return Math.random().toString(36).slice(2, 8);
}

function shuffled(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function createRun() {
  const store = loadStore();
  const id = `run-${shortId()}`;
  const run = {
    run_id: id,
    created_at: Date.now(),
    mission_order: shuffled(MISSION_IDS),
    missions: {},
  };
  store.runs[id] = run;
  store.active_run = id;
  saveStore(store);
  return run;
}

export function getActiveRun() {
  const store = loadStore();
  if (!store.active_run) return null;
  return store.runs[store.active_run] || null;
}

export function getRun(runId) {
  const store = loadStore();
  return store.runs[runId] || null;
}

export function setActiveRun(runId) {
  const store = loadStore();
  if (!store.runs[runId]) return false;
  store.active_run = runId;
  saveStore(store);
  return true;
}

/**
 * Record the result of a single mission. `payload` shape:
 *   { selected: { position, title, year },
 *     classification: { clicked, deferred, evaluated_rejected, not_approached },
 *     episodes: [...]   // optional raw forensics
 *   }
 *
 * Re-recording the same mission overwrites — used by the "redo" button.
 */
export function recordMission(runId, missionId, payload) {
  const store = loadStore();
  const run = store.runs[runId];
  if (!run) throw new Error(`unknown run ${runId}`);
  run.missions[missionId] = {
    completed_at: Date.now(),
    ...payload,
  };
  saveStore(store);
  return run;
}

export function nextMissionId(run) {
  for (const id of run.mission_order) {
    if (!run.missions[id]) return id;
  }
  return null; // all done
}

export function missionProgress(run) {
  const total = run.mission_order.length;
  const done = run.mission_order.filter((id) => run.missions[id]).length;
  return { done, total };
}

export function clearAllRuns() {
  localStorage.removeItem(STORE_KEY);
}

export function clearMission(runId, missionId) {
  const store = loadStore();
  const run = store.runs[runId];
  if (!run) return;
  delete run.missions[missionId];
  saveStore(store);
}

/**
 * Map AR signals + the SERP answers to a mission summary with three tiers:
 *
 *   selected   — the click
 *   alternates — drawn-to-it positives: items the user reapproached, or
 *                items in the deferred bucket. Top 3 by dwell.
 *   rejected   — *high-confidence* negatives: outcome==evaluated_rejected
 *                AND reapproach_count==0 AND total_dwell_ms >= 500ms.
 *                Top 2 by dwell × mean_retreat_distance.
 *
 * Items not meeting either gate fall into the silent middle (brief glances,
 * no engagement) and are dropped from the prompt entirely. Rec algos love a
 * good negative — but only if AR is sure.
 *
 * Full AR classification is preserved alongside in the run record so the
 * future validation/override step on prompt.html can let the user reach in.
 */

const REJECT_MIN_DWELL_MS = 500;

function isConfidentReject(sig) {
  return (
    sig &&
    sig.outcome === 'evaluated_rejected' &&
    (sig.reapproach_count || 0) === 0 &&
    (sig.total_dwell_ms || 0) >= REJECT_MIN_DWELL_MS
  );
}

function isAlternate(sig) {
  if (!sig) return false;
  if ((sig.reapproach_count || 0) > 0) return true;
  if (sig.outcome === 'deferred') return true;
  return false;
}

export function summarizeMission(answers, signals, clickedPosition) {
  const byPos = new Map(answers.map((a) => [a.position, a]));
  const sigByPos = new Map((signals || []).map((s) => [s.position, s]));

  let selected = null;
  if (clickedPosition != null && byPos.has(clickedPosition)) {
    const a = byPos.get(clickedPosition);
    selected = { position: a.position, title: a.title, year: a.year };
  }

  const candidates = answers
    .filter((a) => a.position !== clickedPosition)
    .map((a) => ({ a, sig: sigByPos.get(a.position) || null }));

  const rejected = candidates
    .filter((x) => isConfidentReject(x.sig))
    .sort((a, b) => {
      const sa = (a.sig.total_dwell_ms || 0) * (a.sig.mean_retreat_distance || 1);
      const sb = (b.sig.total_dwell_ms || 0) * (b.sig.mean_retreat_distance || 1);
      return sb - sa;
    })
    .slice(0, 2)
    .map(({ a, sig }) => ({
      position: a.position,
      title: a.title,
      year: a.year,
      dwell_ms: sig.total_dwell_ms,
      retreat_dist: Math.round(sig.mean_retreat_distance || 0),
    }));

  const rejectedPositions = new Set(rejected.map((r) => r.position));
  const alternates = candidates
    .filter((x) => !rejectedPositions.has(x.a.position))
    .filter((x) => isAlternate(x.sig))
    .sort((a, b) => (b.sig.total_dwell_ms || 0) - (a.sig.total_dwell_ms || 0))
    .slice(0, 3)
    .map(({ a, sig }) => ({
      position: a.position,
      title: a.title,
      year: a.year,
      dwell_ms: sig.total_dwell_ms,
      reapproach_count: sig.reapproach_count || 0,
    }));

  return { selected, alternates, rejected };
}

function fmtMovie(m) {
  return `${m.title}${m.year ? ` (${m.year})` : ''}`;
}

/**
 * Build a copy-pasteable LLM prompt from a completed run.
 *
 * Three-tier affinity:
 *   Picked            — explicit positive
 *   Also considered   — soft positive (drawn back / deferred)
 *   Not for me        — high-confidence negative (looked carefully, walked
 *                       away, never returned). Only emitted when AR is sure.
 */
export function buildPrompt(run) {
  const blocks = [];
  for (const id of run.mission_order) {
    const m = run.missions[id];
    if (!m || !m.selected) continue;
    const lines = [`${MISSION_LABELS[id].toUpperCase()}`];
    lines.push(`  Picked:           ${fmtMovie(m.selected)}`);
    if (m.alternates && m.alternates.length) {
      lines.push(`  Also considered:  ${m.alternates.map(fmtMovie).join(', ')}`);
    }
    if (m.rejected && m.rejected.length) {
      lines.push(`  Not for me:       ${m.rejected.map(fmtMovie).join(', ')}`);
    }
    blocks.push(lines.join('\n'));
  }
  if (!blocks.length) {
    return '(no missions completed yet — pick at least one movie to generate a prompt.)';
  }
  return [
    "I'm picking movies and want recommendations grounded in what I just chose.",
    '',
    blocks.join('\n\n'),
    '',
    'Recommend 5 recent (2022–2026) movies for each mission above.',
    '',
    '"Also considered" are movies I was drawn toward but did not pick —',
    'soft positives that encode taste alongside the pick.',
    '',
    '"Not for me" are movies I looked at carefully and decided against —',
    'treat these as confident negatives, strong signals about what to avoid',
    'in the same vein.',
    '',
    'Do not recommend anything from my Picked, Also-considered, or',
    'Not-for-me lists. Briefly explain each pick (one sentence).',
  ].join('\n');
}

// Cross-device permalink: encode run as base64-JSON in URL fragment.
// Strips raw episodes to keep the URL short.
export function encodeRunForUrl(run) {
  const slim = {
    run_id: run.run_id,
    created_at: run.created_at,
    mission_order: run.mission_order,
    missions: Object.fromEntries(
      Object.entries(run.missions).map(([k, m]) => [
        k,
        {
          completed_at: m.completed_at,
          selected: m.selected,
          alternates: m.alternates,
          rejected: m.rejected,
        },
      ]),
    ),
  };
  const json = JSON.stringify(slim);
  // URL-safe base64
  return btoa(unescape(encodeURIComponent(json)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export function decodeRunFromUrl(b64) {
  const padded = b64.replace(/-/g, '+').replace(/_/g, '/');
  const json = decodeURIComponent(escape(atob(padded)));
  return JSON.parse(json);
}
