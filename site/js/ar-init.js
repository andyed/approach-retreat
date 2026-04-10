/**
 * Shared init for all five layout variants.
 *
 * Each layout page calls initSerpPage({ layoutName, render }) and gets back
 * the ApproachRetreat instance. loadQuestion() resolves the current ?q= from
 * URL and fetches the corresponding JSON.
 */
import { ApproachRetreat } from '../dist/approach-retreat.esm.js';
import {
  createPostHogAdapter,
  buildSessionContext,
  isPostHogDisabled,
} from '../dist/adapters/posthog.js';

/**
 * Resolve current ?q= and fetch the matching questions index + answers JSON.
 * Returns { meta, answers, index } where meta is the questions.json entry.
 */
export async function loadQuestion() {
  const idxResp = await fetch('../data/questions.json');
  if (!idxResp.ok) throw new Error('Could not load questions.json');
  const index = await idxResp.json();

  const url = new URL(window.location.href);
  const qid = url.searchParams.get('q') || index.default;
  const meta =
    index.questions.find((q) => q.id === qid) ||
    index.questions.find((q) => q.id === index.default) ||
    index.questions[0];

  const dataResp = await fetch(`../data/${meta.id}.json`);
  if (!dataResp.ok) throw new Error(`Could not load data/${meta.id}.json`);
  const answers = await dataResp.json();

  return { meta, answers, index };
}

/**
 * Initialize ApproachRetreat + PostHog adapter for a layout page.
 *
 * @param {object} opts
 * @param {string} opts.layoutName — layout identifier for telemetry context
 * @param {object} opts.queryMeta — entry from questions.json
 * @param {function} [opts.onEpisode] — per-layout extra callback (e.g. debug overlay)
 * @param {function} [opts.onClick] — per-layout click handler (e.g. expand result)
 * @returns {{ ar: ApproachRetreat, adapter: object }}
 */
export function initApproachRetreat({ layoutName, queryMeta, onEpisode, onClick }) {
  const posthog = window.posthog || null;
  const adapter = createPostHogAdapter(posthog, {
    context: buildSessionContext({
      ar_layout: layoutName,
      ar_query_id: queryMeta?.id || null,
      ar_year_min: queryMeta?.year_min ?? null,
      ar_year_max: queryMeta?.year_max ?? null,
    }),
    disabled: isPostHogDisabled() || !posthog,
  });

  const chainedEpisode = (episode) => {
    adapter.onEpisode(episode);
    if (onEpisode) onEpisode(episode);
  };
  const chainedClick = (click) => {
    adapter.onClick(click);
    if (onClick) onClick(click);
  };

  const ar = new ApproachRetreat({
    resultSelector: '[data-result]',
    includeSamplesInEpisodeJson: true,
    onEpisode: chainedEpisode,
    onClick: chainedClick,
  });
  adapter.bind(ar);
  ar.refresh();

  return { ar, adapter };
}

/**
 * Wire the debug overlay (press 'd' to toggle). Call from any layout page.
 */
export function wireDebugOverlay(ar) {
  const episodesEl = document.getElementById('debug-episodes');
  const retreatsEl = document.getElementById('debug-retreats');
  const classesEl = document.getElementById('debug-classes');

  const update = () => {
    const eps = ar.getEpisodes();
    if (episodesEl) episodesEl.textContent = eps.length;
    if (retreatsEl) retreatsEl.textContent = eps.filter((e) => e.retreated).length;
    if (classesEl) {
      const c = ar.classify();
      classesEl.innerHTML = Object.entries(c)
        .map(
          ([k, v]) =>
            `${k}: ${v.map((s) => s.position).join(',') || '-'}`
        )
        .join('<br>');
    }
  };

  document.addEventListener('keydown', (e) => {
    if (e.key === 'd' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      document.body.classList.toggle('ar-debug-on');
    }
  });

  return update;
}

/**
 * Escape user-facing content before injecting into innerHTML. The JSON data
 * files are trusted (we wrote them) but this keeps the renderer safe if that
 * ever changes — and avoids ampersand surprises.
 */
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Render the answer list into a container. One DOM shape with layout-specific
 * tweaks controlled by the variant flag. Every result element carries
 * [data-result] + [data-position] so the library picks it up automatically.
 *
 * Variants:
 *   default         — title/url/snippet/meta/full_text (narrow, dense, grid,
 *                     and carousel rows — carousel layouts bucket in the page
 *                     and call renderAnswers per row with the default variant)
 *   rich-thumbnail  — prepends a .result-thumbnail element
 *   two-pane        — compact card, no meta, no full_text (lives in reading pane)
 */
export function renderAnswers(container, answers, { variant = 'default' } = {}) {
  for (const a of answers) {
    const isAd = a.type === 'ad';
    const div = document.createElement('div');
    div.className = isAd ? 'result result-ad' : 'result';
    div.dataset.result = '';
    div.dataset.position = a.position;
    if (isAd) div.dataset.etype = 'ad';

    if (variant === 'rich-thumbnail') {
      const thumb = document.createElement('div');
      thumb.className = 'result-thumbnail';
      div.appendChild(thumb);
      const body = document.createElement('div');
      body.className = 'result-body';
      body.innerHTML = renderResultInner(a, isAd, variant);
      div.appendChild(body);
    } else {
      div.innerHTML = renderResultInner(a, isAd, variant);
    }

    container.appendChild(div);
  }
}

function renderResultInner(a, isAd, variant) {
  const hideMeta = variant === 'two-pane';
  const hideFull = variant === 'two-pane';

  const metaBlock =
    !isAd && !hideMeta
      ? `<div class="result-meta">${(a.upvotes || 0).toLocaleString()} upvotes &middot; ${escapeHtml(String(a.year))}</div>`
      : '';
  const fullBlock = hideFull
    ? ''
    : `<div class="result-full-text">${escapeHtml(a.full_text || '')}</div>`;

  if (isAd) {
    return `
      <div class="result-title"><span class="result-sponsored">Sponsored</span>${escapeHtml(a.title)}</div>
      <div class="result-url">${escapeHtml(a.author_bio || '')}</div>
      <div class="result-snippet">${escapeHtml(a.snippet || '')}</div>
      ${fullBlock}
    `;
  }
  return `
    <div class="result-title">${escapeHtml(a.title)}</div>
    <div class="result-url">${escapeHtml(a.author || '')} &middot; ${escapeHtml(a.author_bio || '')}</div>
    <div class="result-snippet">${escapeHtml(a.snippet || '')}</div>
    ${metaBlock}
    ${fullBlock}
  `;
}

/**
 * Render an answer into the two-pane reading pane. Used as the click target
 * for the wide-two-pane layout.
 */
export function renderReadingPane(pane, answer) {
  if (!pane || !answer) return;
  const isAd = answer.type === 'ad';
  pane.innerHTML = `
    <div class="rp-title">${escapeHtml(answer.title)}</div>
    <div class="rp-author">${isAd ? 'Sponsored' : escapeHtml(answer.author || '')}</div>
    <div class="rp-meta">${escapeHtml(answer.author_bio || '')}${
      !isAd && answer.year ? ` &middot; ${escapeHtml(String(answer.year))}` : ''
    }${
      !isAd && answer.upvotes
        ? ` &middot; ${answer.upvotes.toLocaleString()} upvotes`
        : ''
    }</div>
    <div class="rp-body">${escapeHtml(answer.full_text || '')}</div>
  `;
}

/**
 * Build the question-switcher dropdown header. Preserves the current layout
 * when navigating between questions.
 */
export function renderHeader({ meta, index, layoutName }) {
  const queryEl = document.querySelector('.serp-query');
  const infoEl = document.querySelector('.serp-info');
  const switcherEl = document.querySelector('.question-switcher');

  if (queryEl) queryEl.textContent = meta.title;

  if (infoEl) {
    const range =
      meta.year_min && meta.year_max ? `${meta.year_min}&ndash;${meta.year_max}` : '';
    const count = meta.answer_count ? `${meta.answer_count} answers` : '';
    const adBit = meta.ad_count ? ` + ${meta.ad_count} ad` : '';
    const bits = [count + adBit, range, meta.subtitle].filter(Boolean);
    infoEl.innerHTML = `${bits.join(' &middot; ')} &middot; <a href="../index.html">&larr; All layouts</a>`;
  }

  if (switcherEl) {
    switcherEl.innerHTML = '';
    const label = document.createElement('label');
    label.textContent = 'Question: ';
    label.setAttribute('for', 'q-select');
    const select = document.createElement('select');
    select.id = 'q-select';
    for (const q of index.questions) {
      const opt = document.createElement('option');
      opt.value = q.id;
      opt.textContent = q.title;
      if (q.id === meta.id) opt.selected = true;
      select.appendChild(opt);
    }
    select.addEventListener('change', (e) => {
      const next = e.target.value;
      const url = new URL(window.location.href);
      url.searchParams.set('q', next);
      window.location.href = url.toString();
    });
    switcherEl.appendChild(label);
    switcherEl.appendChild(select);
  }
}
