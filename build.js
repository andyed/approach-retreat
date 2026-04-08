import * as esbuild from 'esbuild';

const shared = {
  entryPoints: ['src/index.js'],
  bundle: true,
  minify: true,
};

const watch = process.argv.includes('--watch');

// IIFE for <script> tag
await esbuild.build({
  ...shared,
  outfile: 'dist/approach-retreat.js',
  format: 'iife',
  globalName: 'ApproachRetreat',
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

console.log('Built dist/approach-retreat.{js,esm.js,cjs.js}');
