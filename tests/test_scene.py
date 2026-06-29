from __future__ import annotations

import time
from types import SimpleNamespace

from ap_visualizer.scene import (
  SceneHealth,
  build_scene_frame,
  estimate_stop_distance,
  health_from_submaster,
)
from ap_visualizer.sim import make_sim_frame


def xyzt(xs, ys=None, zs=None):
  return SimpleNamespace(x=xs, y=ys or [0.0] * len(xs), z=zs or [0.0] * len(xs))


def base_data(should_stop=False):
  path = xyzt([0.0, 5.0, 12.0, 20.0], [0.0, 0.1, 0.2, 0.25])
  return {
    "modelV2": SimpleNamespace(
      position=path,
      velocity=xyzt([11.0, 8.0, 0.3, 0.0]),
      action=SimpleNamespace(shouldStop=should_stop),
      laneLines=[xyzt([0.0, 10.0], [-1.8, -1.7]), xyzt([0.0, 10.0], [1.8, 1.7])],
      laneLineProbs=[0.91, 0.88],
      roadEdges=[xyzt([0.0, 10.0], [-5.5, -5.4]), xyzt([0.0, 10.0], [5.5, 5.4])],
      leadsV3=[],
    ),
    "longitudinalPlan": SimpleNamespace(shouldStop=False, longitudinalPlanSource="cruise", speeds=[11.0, 8.0, 0.2]),
    "longitudinalPlanSP": SimpleNamespace(longitudinalPlanSource="cruise", speedLimit=SimpleNamespace(resolver=SimpleNamespace())),
    "radarState": SimpleNamespace(
      leadOne=SimpleNamespace(status=True, dRel=31.0, yRel=0.4, vRel=-0.7),
      leadTwo=SimpleNamespace(status=False),
    ),
    "carState": SimpleNamespace(
      vEgo=10.2,
      gearShifter="drive",
      standstill=False,
      cruiseState=SimpleNamespace(speedCluster=13.4, speed=13.4),
    ),
    "carStateSP": SimpleNamespace(speedLimit=11.17),
    "selfdriveState": SimpleNamespace(enabled=True, active=True, engageable=True, state="enabled"),
    "controlsState": SimpleNamespace(),
    "liveMapDataSP": SimpleNamespace(speedLimitValid=False, speedLimit=0.0),
  }


def test_scene_frame_maps_decoded_values_without_semantic_labels():
  frame = build_scene_frame(
    base_data(should_stop=True),
    sequence_number=7,
    mode="live",
    connected_clients=1,
    source="cereal",
    health=SceneHealth(),
    now=100.0,
    mono_time_ns=123,
  )

  assert frame["schemaVersion"] == 1
  assert frame["ego"]["gear"] == "D"
  assert frame["ego"]["displaySpeed"] == 23
  assert frame["cruise"]["setSpeedMps"] == 13.4
  assert frame["cruise"]["speedLimitMps"] == 11.17
  assert frame["assist"]["shouldStop"] is True
  assert frame["assist"]["stopDistanceM"] == 12.0
  assert frame["model"]["laneLineProbs"] == [0.91, 0.88]
  assert frame["model"]["leads"][0]["x"] == 31.0
  assert frame["semanticObjects"] == []


def test_stop_distance_estimation_uses_model_trajectory():
  model = SimpleNamespace(position=xyzt([0.0, 8.0, 16.0, 30.0]), velocity=xyzt([9.0, 5.0, 0.2, 0.0]))
  plan = SimpleNamespace(speeds=[9.0, 4.0, 0.0])

  assert estimate_stop_distance(model, plan) == 16.0


def test_health_marks_core_stale_services():
  now = time.monotonic()
  sm = SimpleNamespace(
    alive={"modelV2": False, "longitudinalPlan": True, "radarState": True, "carState": True, "selfdriveState": True, "controlsState": True},
    valid={"modelV2": True, "longitudinalPlan": True, "radarState": True, "carState": True, "selfdriveState": True, "controlsState": True},
    freq_ok={"modelV2": True, "longitudinalPlan": True, "radarState": True, "carState": True, "selfdriveState": True, "controlsState": True},
    recv_time={"modelV2": now - 2.0, "carState": now - 2.0},
  )

  health = health_from_submaster(sm)

  assert "modelV2" in health.stale_services
  assert health.frame_age_ms >= 1900


def test_simulator_frame_has_display_only_contract():
  frame = make_sim_frame(3)

  assert frame["mode"] == "sim"
  assert frame["sequence"] == 3
  assert frame["model"]["path"]
  assert frame["semanticObjects"] == []
  assert frame["diagnostics"]["source"] == "synthetic"

