/**
 * Regenerate the README hero wall from the current replay pages.
 *
 * The three hero images are screenshots of site/replay/trials/<trial>.html,
 * so they inherit whatever substrate that page was built on. Before 2026-09-15
 * they were hand-made one-offs from April 2026 and silently drifted two
 * substrate rebuilds behind the counts printed beside them. Run this after any
 * rebuild of the replay bundles.
 *
 *   node scripts/build_hero_wall.mjs              # all three hero trials
 *   node scripts/build_hero_wall.mjs p047-b6-t1   # one trial
 *
 * Playwright is deliberately NOT a devDependency: it would pull a browser
 * download into the Pages CI install for a script that only runs by hand.
 * Install it locally (`npm i -D playwright && npx playwright install chromium`)
 * or point PLAYWRIGHT_PATH at a node_modules that already has it.
 *
 * "tilt" in the old filenames was a misnomer — nothing was ever transformed in
 * perspective. The wall effect comes from the README table's column widths.
 */
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TRIALS = ['p006-b4-t7', 'p047-b6-t1', 'p019-b1-t8'];
const OUT_DIR = path.join(REPO, 'site/assets/hero');

// Capture geometry. The replay page lays out a fixed 1280px column, so the
// viewport width is the content width — no cropping needed.
const VIEW_W = 1280;
const VIEW_H = 980;
const SCALE = 2;
const FRAME_PX = 10;          // orange frame, output pixels
const MARGIN_PX = 20;         // transparent margin, output pixels
const FRAME_COLOR = '#ff9933'; // same orange as the page's cursor glyph
// Capture at 2x for crisp text, then ship at a width the README can actually
// use: it draws these at 300-440 CSS px, so 1400 covers a 2x display twice
// over and halves the bytes every README view pays for.
const OUT_W = 1400;

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const roots = [REPO, process.env.PLAYWRIGHT_PATH].filter(Boolean);
  for (const root of roots) {
    try {
      return require(require.resolve('playwright', { paths: [root] }));
    } catch { /* try the next root */ }
  }
  throw new Error(
    'playwright not found. Run `npm i -D playwright && npx playwright install chromium`, ' +
    'or set PLAYWRIGHT_PATH to a node_modules directory that has it.'
  );
}

/** Scroll the viewer so the trial's most interesting AOI sits mid-frame. */
async function frameSubject(page) {
  return page.evaluate(() => {
    const PRIORITY = ['CLICKED', 'DEFERRED', 'EVALUATED_REJECTED'];
    let subject = null;
    for (const want of PRIORITY) {
      for (const [kind, items] of Object.entries(TRIAL.bboxes)) {
        const labels = (TRIAL.aoi_labels || {})[kind] || [];
        const i = labels.findIndex((l) => l && l.label === want);
        if (i >= 0 && items[i]) { subject = { kind, want, box: items[i] }; break; }
      }
      if (subject) break;
    }
    const viewer = document.getElementById('viewer');
    if (!subject) return { scrolled: 0, subject: null };
    // AOI coordinates are screenshot pixel space and the image renders 1:1 at
    // 1280px, so a y coordinate is already a viewer offset.
    const mid = subject.box.location.y + subject.box.size.height / 2;
    viewer.scrollTop = Math.max(0, mid - viewer.clientHeight / 2);
    return { scrolled: viewer.scrollTop, subject: `${subject.want} ${subject.kind}` };
  });
}

const run = (args) => execFileSync('magick', args, { stdio: ['ignore', 'pipe', 'pipe'] });

async function main() {
  const { chromium } = loadPlaywright();
  const wanted = process.argv.slice(2);
  const trials = wanted.length ? wanted : TRIALS;
  const tmp = mkdtempSync(path.join(tmpdir(), 'ar-hero-'));
  const browser = await chromium.launch();

  try {
    for (const trial of trials) {
      const src = path.join(REPO, 'site/replay/trials', `${trial}.html`);
      const page = await browser.newPage({
        viewport: { width: VIEW_W, height: VIEW_H },
        deviceScaleFactor: SCALE,
      });
      await page.goto(pathToFileURL(src).href, { waitUntil: 'load' });
      // The overlays are drawn from inline TRIAL data after the screenshot
      // decodes; wait for both rather than a fixed sleep.
      await page.waitForFunction(() => {
        const img = document.getElementById('serp-img');
        return img && img.complete && img.naturalWidth > 0
          && document.getElementById('aoi-svg').childElementCount > 0;
      }, null, { timeout: 30_000 });
      const framed = await frameSubject(page);
      await page.waitForTimeout(400); // let the cursor transition settle

      const raw = path.join(tmp, `${trial}.png`);
      writeFileSync(raw, await page.screenshot());
      await page.close();

      const out = path.join(OUT_DIR, `${trial}_hero.png`);
      // -strip keeps reruns byte-identical: without it ImageMagick stamps a
      // time chunk and every rebuild is a fresh 1.5 MB blob in the history.
      run([raw,
           '-bordercolor', FRAME_COLOR, '-border', String(FRAME_PX),
           '-bordercolor', 'none', '-border', String(MARGIN_PX),
           '-resize', `${OUT_W}x`, '-strip', out]);
      const size = run(['identify', '-format', '%wx%h', out]).toString();
      console.log(`${trial}: ${size}  subject=${framed.subject}  scrollTop=${Math.round(framed.scrolled)}`);
    }
  } finally {
    await browser.close();
    rmSync(tmp, { recursive: true, force: true });
  }
}

main();
