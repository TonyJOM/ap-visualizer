import { displayMps, SceneFrame, speedUnit } from './types';

const makeLine = (offset: number, curve: number, zOffset = 0): { x: number; y: number; z: number }[] => {
  const points = [];
  for (let i = 0; i <= 32; i += 1) {
    const x = (i / 32) ** 2 * 155;
    const y = offset + Math.sin(x * 0.026) * curve;
    points.push({ x, y, z: zOffset + Math.sin(x * 0.04) * 0.035 });
  }
  return points;
};

export function makeSimFrame(sequence: number, now = Date.now()): SceneFrame {
  const t = now / 1000;
  const speedMps = 10.5 + Math.sin(t * 0.18) * 2.5;
  const shouldStop = Math.sin(t * 0.08) > 0.72;
  const stopDistanceM = shouldStop ? 42 + Math.sin(t * 0.7) * 5 : null;
  const units = 'imperial' as const;

  return {
    schemaVersion: 1,
    mode: 'sim',
    sequence,
    monoTime: now * 1_000_000,
    wallTime: now / 1000,
    fresh: true,
    units,
    ego: {
      speedMps,
      displaySpeed: displayMps(speedMps, units),
      speedUnit: speedUnit(units),
      gear: 'D',
      engaged: true,
      standstill: false
    },
    cruise: {
      setSpeedMps: 13.4,
      speedLimitMps: 11.17
    },
    assist: {
      status: 'engaged',
      longitudinalPlanSource: shouldStop ? 'e2e' : 'cruise',
      shouldStop,
      stopDistanceM
    },
    model: {
      path: makeLine(0, 0.25),
      laneLines: [makeLine(-5.4, 0.2), makeLine(-1.8, 0.16), makeLine(1.8, 0.16), makeLine(5.4, 0.2)],
      laneLineProbs: [0.45, 0.95, 0.94, 0.5],
      roadEdges: [makeLine(-7.2, 0.35), makeLine(7.2, 0.35)],
      leads: [
        { id: 'lead-1', status: true, x: 38 + Math.sin(t * 0.3) * 4, y: 0.5, relativeVelocityMps: -0.8 },
        { id: 'lead-2', status: Math.sin(t * 0.2) > 0, x: 72, y: -3.2, relativeVelocityMps: 1.2 }
      ]
    },
    semanticObjects: [],
    diagnostics: {
      connectedClients: 1,
      source: 'synthetic',
      frameAgeMs: 0,
      staleServices: []
    }
  };
}

