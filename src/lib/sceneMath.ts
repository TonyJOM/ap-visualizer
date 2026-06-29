import { Point3, SceneFrame } from './types';

export function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function isFrameStale(frame: SceneFrame, nowMs = Date.now()): boolean {
  return nowMs - frame.wallTime * 1000 > 800 || !frame.fresh;
}

export function findPathYAtDistance(path: Point3[], x: number): number {
  if (path.length === 0) {
    return 0;
  }

  let best = path[0];
  let bestDelta = Math.abs(best.x - x);
  for (const point of path) {
    const delta = Math.abs(point.x - x);
    if (delta < bestDelta) {
      best = point;
      bestDelta = delta;
    }
  }
  return best.y;
}

export function normalizeLaneOpacity(probability: number, stale: boolean): number {
  const base = 0.18 + clamp01(probability) * 0.72;
  return stale ? base * 0.35 : base;
}

