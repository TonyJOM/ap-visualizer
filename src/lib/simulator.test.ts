import { describe, expect, it } from 'vitest';
import { makeSimFrame } from './simulator';

describe('simulator frame', () => {
  it('matches the v1 scene contract', () => {
    const frame = makeSimFrame(12, 1_000_000);

    expect(frame.schemaVersion).toBe(1);
    expect(frame.mode).toBe('sim');
    expect(frame.sequence).toBe(12);
    expect(frame.semanticObjects).toEqual([]);
    expect(frame.model.path.length).toBeGreaterThan(10);
    expect(frame.model.laneLines).toHaveLength(4);
    expect(frame.model.roadEdges).toHaveLength(2);
    expect(frame.diagnostics.source).toBe('synthetic');
  });
});

