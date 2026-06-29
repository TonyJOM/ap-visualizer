import { describe, expect, it } from 'vitest';
import { makeSimFrame } from './simulator';
import { parseSceneMessage } from './useSceneStream';

describe('scene stream parsing', () => {
  it('parses scene frames', () => {
    const frame = makeSimFrame(4, 1_000_000);

    expect(parseSceneMessage(JSON.stringify(frame))).toEqual(frame);
  });

  it('parses busy messages', () => {
    expect(parseSceneMessage(JSON.stringify({ type: 'busy', reason: 'Already connected' }))).toEqual({
      type: 'busy',
      reason: 'Already connected'
    });
  });

  it('rejects unsupported scene schemas', () => {
    expect(() => parseSceneMessage(JSON.stringify({ schemaVersion: 99 }))).toThrow(/schema/i);
  });
});

