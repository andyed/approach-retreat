import { describe, it, expect } from 'vitest';
import { classifyAoiInViewport } from '../../src/approach-retreat.js';

// classifyAoiInViewport is the pure geometry primitive that decides whether an
// AOI is on screen and which third (top/mid/bot) its center falls in. Its
// edge semantics are deliberately matched to the Python reference
// (viewport_time_calibration.py): touching edges do NOT intersect, and the
// three bands are [0, h/3) / [h/3, 2h/3) / [2h/3, h]. These cases lock that.
describe('classifyAoiInViewport', () => {
  const scrH = 900; // thirds at 300 / 600

  it('center in the top third → top', () => {
    expect(classifyAoiInViewport(100, 200, 0, scrH)).toEqual({
      intersecting: true,
      band: 'top',
    });
  });

  it('center in the middle third → mid', () => {
    expect(classifyAoiInViewport(400, 500, 0, scrH)).toEqual({
      intersecting: true,
      band: 'mid',
    });
  });

  it('center in the bottom third → bot', () => {
    expect(classifyAoiInViewport(700, 800, 0, scrH)).toEqual({
      intersecting: true,
      band: 'bot',
    });
  });

  it('AOI bottom edge exactly touching viewport top is NOT intersecting', () => {
    // min(aoiBot=0, vpBot=900) > max(aoiTop=-100, vpTop=0) → 0 > 0 is false.
    expect(classifyAoiInViewport(-100, 0, 0, scrH)).toEqual({
      intersecting: false,
      band: 'off',
    });
  });

  it('AOI fully above the viewport → off', () => {
    expect(classifyAoiInViewport(-500, -100, 0, scrH)).toEqual({
      intersecting: false,
      band: 'off',
    });
  });

  it('tall AOI intersects while its center is off-viewport → intersecting, band off', () => {
    // Spans -2000..200 at scroll 0: intersects the viewport, but center
    // (centerVpY = -900) is above it, so no band applies.
    expect(classifyAoiInViewport(-2000, 200, 0, scrH)).toEqual({
      intersecting: true,
      band: 'off',
    });
  });

  it('respects scrollY when locating the center band', () => {
    // AOI at page 1000..1100; scrolled to 800 → center vp-Y = 250 → top third.
    expect(classifyAoiInViewport(1000, 1100, 800, scrH)).toEqual({
      intersecting: true,
      band: 'top',
    });
  });
});
