import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Pure parity/unit tests run in node (fast, no DOM). The demo-emission
    // suite opts into a browser-like DOM per-file via a
    // `// @vitest-environment happy-dom` docblock at the top of the file.
    environment: 'node',
    include: ['tests/**/*.test.js'],
  },
});
