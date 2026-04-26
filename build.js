import * as esbuild from 'esbuild';
import { cp, rm, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';

const shared = {
  entryPoints: ['src/index.js'],
  bundle: true,
  minify: true,
};

const watch = process.argv.includes('--watch');

// --- Library bundles ---

// IIFE for <script> tag
await esbuild.build({
  ...shared,
  outfile: 'dist/approach-retreat.js',
  format: 'iife',
  globalName: 'ApproachRetreatLib',
});

// ESM
await esbuild.build({
  ...shared,
  outfile: 'dist/approach-retreat.esm.js',
  format: 'esm',
});

// CJS
await esbuild.build({
  ...shared,
  outfile: 'dist/approach-retreat.cjs.js',
  format: 'cjs',
});

// --- Adapter bundles ---
// Adapters ship as separate ESM files so pages can import just what they need.

await esbuild.build({
  entryPoints: [
    'src/adapters/posthog.js',
    'src/adapters/callback.js',
  ],
  outdir: 'dist/adapters',
  format: 'esm',
  bundle: true,
  minify: false, // keep adapter source legible for debugging
});

// --- Mirror dist/ → site/dist/ so the static site (served from site/) can
// resolve imports without reaching outside its serving root. ---

if (existsSync('site/dist')) await rm('site/dist', { recursive: true });
await mkdir('site/dist', { recursive: true });
await cp('dist', 'site/dist', { recursive: true });

console.log('Built dist/ and mirrored to site/dist/');
