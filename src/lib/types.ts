export type Point3 = {
  x: number;
  y: number;
  z: number;
};

export type LeadVehicle = {
  id: string;
  status: boolean;
  x: number;
  y: number;
  relativeVelocityMps: number;
};

export type SceneFrame = {
  schemaVersion: 1;
  mode: 'live' | 'sim';
  sequence: number;
  monoTime: number;
  wallTime: number;
  fresh: boolean;
  units: 'metric' | 'imperial';
  ego: {
    speedMps: number;
    displaySpeed: number;
    speedUnit: 'mph' | 'km/h';
    gear: string;
    engaged: boolean;
    standstill: boolean;
  };
  cruise: {
    setSpeedMps: number | null;
    speedLimitMps: number | null;
  };
  assist: {
    status: string;
    longitudinalPlanSource: string;
    shouldStop: boolean;
    stopDistanceM: number | null;
  };
  model: {
    path: Point3[];
    laneLines: Point3[][];
    laneLineProbs: number[];
    roadEdges: Point3[][];
    leads: LeadVehicle[];
  };
  semanticObjects: [];
  diagnostics: {
    connectedClients: number;
    source: string;
    frameAgeMs: number;
    staleServices: string[];
  };
};

export type ConnectionState = 'connecting' | 'live' | 'sim' | 'stale' | 'waiting' | 'busy' | 'error';

export function displayMps(speedMps: number, units: 'metric' | 'imperial'): number {
  if (units === 'metric') {
    return Math.round(speedMps * 3.6);
  }
  return Math.round(speedMps * 2.23693629);
}

export function speedUnit(units: 'metric' | 'imperial'): 'mph' | 'km/h' {
  return units === 'metric' ? 'km/h' : 'mph';
}

