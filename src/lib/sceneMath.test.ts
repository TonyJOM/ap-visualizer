import { describe, expect, it } from 'vitest';
import { clamp01, findPathYAtDistance, isFrameStale, normalizeLaneOpacity } from './sceneMath';
import { makeSimFrame } from './simulator';

describe('scene math', () => {
  it('clamps lane confidence', () => {
    expect(clamp01(-2)).toBe(0);
    expect(clamp01(0.4)).toBe(0.4);
    expect(clamp01(4)).toBe(1);
  });

  it('finds the lateral path position nearest a distance', () => {
    expect(findPathYAtDistance([{ x: 0, y: 0, z: 0 }, { x: 20, y: 1.4, z: 0 }], 18)).toBe(1.4);
  });

  it('detects stale scene frames', () => {
    const frame = makeSimFrame(1, 1_000_000);
    expect(isFrameStale(frame, 1_000_300)).toBe(false);
    expect(isFrameStale(frame, 1_001_000)).toBe(true);
    expect(isFrameStale({ ...frame, fresh: false }, 1_000_300)).toBe(true);
  });

  it('dims stale lane opacity', () => {
    expect(normalizeLaneOpacity(1, true)).toBeLessThan(normalizeLaneOpacity(1, false));
  });
});

