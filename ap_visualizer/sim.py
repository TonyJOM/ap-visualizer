from __future__ import annotations

import math
import time
from types import SimpleNamespace

from ap_visualizer.scene import build_scene_frame


def _xyzt(offset: float, curve: float) -> SimpleNamespace:
  xs = [(index / 32) ** 2 * 155.0 for index in range(33)]
  ys = [offset + math.sin(x * 0.026) * curve for x in xs]
  zs = [math.sin(x * 0.04) * 0.035 for x in xs]
  return SimpleNamespace(x=xs, y=ys, z=zs)


def synthetic_data(sequence_number: int, now: float | None = None) -> dict[str, SimpleNamespace]:
  now = time.time() if now is None else now
  speed_mps = 10.5 + math.sin(now * 0.18) * 2.5
  should_stop = math.sin(now * 0.08) > 0.72
  stop_distance = 42.0 + math.sin(now * 0.7) * 5.0
  path = _xyzt(0.0, 0.25)
  velocity = SimpleNamespace(x=[max(0.0, speed_mps * (1.0 - x / stop_distance)) if should_stop else speed_mps for x in path.x])

  return {
    "modelV2": SimpleNamespace(
      position=path,
      velocity=velocity,
      laneLines=[_xyzt(-5.4, 0.2), _xyzt(-1.8, 0.16), _xyzt(1.8, 0.16), _xyzt(5.4, 0.2)],
      laneLineProbs=[0.45, 0.95, 0.94, 0.5],
      roadEdges=[_xyzt(-7.2, 0.35), _xyzt(7.2, 0.35)],
      leadsV3=[],
      action=SimpleNamespace(shouldStop=should_stop),
    ),
    "longitudinalPlan": SimpleNamespace(shouldStop=should_stop, longitudinalPlanSource="e2e" if should_stop else "cruise"),
    "longitudinalPlanSP": SimpleNamespace(longitudinalPlanSource="cruise", speedLimit=SimpleNamespace(resolver=SimpleNamespace())),
    "radarState": SimpleNamespace(
      leadOne=SimpleNamespace(status=True, dRel=38.0 + math.sin(now * 0.3) * 4.0, yRel=0.5, vRel=-0.8),
      leadTwo=SimpleNamespace(status=math.sin(now * 0.2) > 0, dRel=72.0, yRel=-3.2, vRel=1.2),
    ),
    "carState": SimpleNamespace(
      vEgo=speed_mps,
      gearShifter="drive",
      standstill=False,
      cruiseState=SimpleNamespace(speedCluster=13.4, speed=13.4),
    ),
    "carStateSP": SimpleNamespace(speedLimit=11.17),
    "selfdriveState": SimpleNamespace(enabled=True, active=True, engageable=True, state="enabled"),
    "controlsState": SimpleNamespace(),
    "liveMapDataSP": SimpleNamespace(speedLimitValid=False, speedLimit=0.0),
  }


def make_sim_frame(sequence_number: int, connected_clients: int = 1) -> dict:
  now = time.time()
  return build_scene_frame(
    synthetic_data(sequence_number, now),
    sequence_number=sequence_number,
    mode="sim",
    connected_clients=connected_clients,
    source="synthetic",
    is_metric=False,
    now=now,
  )

