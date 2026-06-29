from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

KPH_TO_MS = 1000.0 / 3600.0
MS_TO_KPH = 3.6
MS_TO_MPH = 2.2369362920544

SCHEMA_VERSION = 1
FRAME_STALE_SECONDS = 0.55
STOP_SPEED_MPS = 0.45
MAX_MODEL_POINTS = 64
LIVE_SERVICES = (
  "modelV2",
  "longitudinalPlan",
  "longitudinalPlanSP",
  "radarState",
  "carState",
  "carStateSP",
  "selfdriveState",
  "controlsState",
  "liveMapDataSP",
)
REQUIRED_FRESH_SERVICES = ("modelV2", "carState")
FRESHNESS_SERVICES = ("modelV2", "longitudinalPlan", "radarState", "carState", "selfdriveState", "controlsState")

STANDARD_LONG_SOURCES = ("cruise", "lead0", "lead1", "lead2", "e2e")
SP_LONG_SOURCES = ("cruise", "sccVision", "sccMap", "speedLimitAssist", "curveSpeed")
GEAR_NAMES = {
  "unknown": "--",
  "park": "P",
  "drive": "D",
  "neutral": "N",
  "reverse": "R",
  "sport": "S",
  "low": "L",
  "brake": "B",
}


@dataclass
class SceneHealth:
  alive: Mapping[str, bool] = field(default_factory=dict)
  valid: Mapping[str, bool] = field(default_factory=dict)
  freq_ok: Mapping[str, bool] = field(default_factory=dict)
  recv_time: Mapping[str, float] = field(default_factory=dict)
  stale_services: list[str] = field(default_factory=list)
  frame_age_ms: float = 0.0


def finite_float(value: Any, default: float = 0.0) -> float:
  try:
    result = float(value)
  except (TypeError, ValueError):
    return default
  return result if math.isfinite(result) else default


def finite_optional(value: Any) -> float | None:
  result = finite_float(value, math.nan)
  return result if math.isfinite(result) and result > 0 else None


def sequence(value: Any) -> list[Any]:
  if value is None:
    return []
  try:
    return list(value)
  except TypeError:
    return []


def get_path(obj: Any, dotted_path: str, default: Any = None) -> Any:
  current = obj
  for part in dotted_path.split("."):
    if current is None:
      return default
    current = getattr(current, part, default)
  return current


def service(data: Mapping[str, Any], name: str) -> Any:
  return data.get(name)


def display_speed(speed_mps: float, units: str) -> int:
  return int(round(speed_mps * (MS_TO_KPH if units == "metric" else MS_TO_MPH)))


def enum_label(value: Any, known: tuple[str, ...] = ()) -> str:
  if value is None:
    return "--"
  if isinstance(value, str):
    return value.split(".")[-1]
  try:
    raw = int(value)
  except (TypeError, ValueError):
    text = str(value)
    return text.split(".")[-1] if text else "--"
  if 0 <= raw < len(known):
    return known[raw]
  return str(raw)


def gear_label(value: Any) -> str:
  label = enum_label(value)
  return GEAR_NAMES.get(label, label.upper()[:1] if label and label != "--" else "--")


def points_from_xyzt(xyzt: Any, max_points: int = MAX_MODEL_POINTS) -> list[dict[str, float]]:
  xs = sequence(getattr(xyzt, "x", None))
  ys = sequence(getattr(xyzt, "y", None))
  zs = sequence(getattr(xyzt, "z", None))
  points = []

  for index, x_value in enumerate(xs[:max_points]):
    x = finite_float(x_value)
    y = finite_float(ys[index] if index < len(ys) else 0.0)
    z = finite_float(zs[index] if index < len(zs) else 0.0)
    if x >= 0:
      points.append({"x": x, "y": y, "z": z})

  return points


def estimate_stop_distance(model_v2: Any, longitudinal_plan: Any) -> float | None:
  model_positions = sequence(get_path(model_v2, "position.x"))
  model_velocities = sequence(get_path(model_v2, "velocity.x"))

  if model_positions and model_velocities:
    for x_value, velocity in zip(model_positions, model_velocities, strict=False):
      x = finite_float(x_value)
      v = finite_float(velocity)
      if x > 1.0 and v <= STOP_SPEED_MPS:
        return max(0.0, x)

    min_index, _ = min(enumerate(model_velocities), key=lambda item: finite_float(item[1]))
    if min_index < len(model_positions):
      return max(0.0, finite_float(model_positions[min_index]))

  plan_speeds = sequence(getattr(longitudinal_plan, "speeds", None))
  if model_positions and plan_speeds:
    for index, speed in enumerate(plan_speeds):
      if finite_float(speed) <= STOP_SPEED_MPS:
        path_index = min(len(model_positions) - 1, round(index / max(len(plan_speeds) - 1, 1) * (len(model_positions) - 1)))
        return max(0.0, finite_float(model_positions[path_index]))

  if model_positions:
    return min(max(finite_float(model_positions[-1]), 8.0), 90.0)

  return None


def model_should_stop(model_v2: Any) -> bool:
  return bool(get_path(model_v2, "action.shouldStop", False))


def plan_should_stop(longitudinal_plan: Any) -> bool:
  return bool(getattr(longitudinal_plan, "shouldStop", False))


def lane_lines(model_v2: Any) -> tuple[list[list[dict[str, float]]], list[float]]:
  lines = [points_from_xyzt(item) for item in sequence(getattr(model_v2, "laneLines", None))]
  probs = [max(0.0, min(1.0, finite_float(prob))) for prob in sequence(getattr(model_v2, "laneLineProbs", None))]

  while len(probs) < len(lines):
    probs.append(0.0)

  return lines, probs[:len(lines)]


def road_edges(model_v2: Any) -> list[list[dict[str, float]]]:
  return [points_from_xyzt(item) for item in sequence(getattr(model_v2, "roadEdges", None))]


def radar_leads(radar_state: Any) -> list[dict[str, Any]]:
  leads = []
  for name in ("leadOne", "leadTwo"):
    lead = getattr(radar_state, name, None)
    if lead is None or not bool(getattr(lead, "status", False)):
      continue
    leads.append({
      "id": name,
      "status": True,
      "x": max(0.0, finite_float(getattr(lead, "dRel", 0.0))),
      "y": finite_float(getattr(lead, "yRel", 0.0)),
      "relativeVelocityMps": finite_float(getattr(lead, "vRel", 0.0)),
    })
  return leads


def model_leads(model_v2: Any, ego_speed_mps: float) -> list[dict[str, Any]]:
  leads = []
  for index, lead in enumerate(sequence(getattr(model_v2, "leadsV3", None))):
    prob = finite_float(getattr(lead, "prob", 0.0))
    xs = sequence(getattr(lead, "x", None))
    ys = sequence(getattr(lead, "y", None))
    speeds = sequence(getattr(lead, "v", None))
    if prob < 0.5 or not xs:
      continue

    leads.append({
      "id": f"model-{index + 1}",
      "status": True,
      "x": max(0.0, finite_float(xs[0])),
      "y": finite_float(ys[0] if ys else 0.0),
      "relativeVelocityMps": finite_float(speeds[0] if speeds else ego_speed_mps) - ego_speed_mps,
    })
  return leads


def speed_limit_mps(data: Mapping[str, Any]) -> float | None:
  car_state_sp = service(data, "carStateSP")
  car_speed_limit = finite_optional(getattr(car_state_sp, "speedLimit", None))
  if car_speed_limit is not None:
    return car_speed_limit

  long_sp = service(data, "longitudinalPlanSP")
  resolver = get_path(long_sp, "speedLimit.resolver")
  if bool(getattr(resolver, "speedLimitFinalLastValid", False)):
    resolved = finite_optional(getattr(resolver, "speedLimitFinalLast", None))
    if resolved is not None:
      return resolved
  if bool(getattr(resolver, "speedLimitValid", False)):
    resolved = finite_optional(getattr(resolver, "speedLimit", None))
    if resolved is not None:
      return resolved

  live_map = service(data, "liveMapDataSP")
  if bool(getattr(live_map, "speedLimitValid", False)):
    mapped = finite_optional(getattr(live_map, "speedLimit", None))
    if mapped is not None:
      return mapped

  return None


def set_speed_mps(car_state: Any) -> float | None:
  cruise_state = getattr(car_state, "cruiseState", None)
  for field_name in ("speedCluster", "speed"):
    value = finite_optional(getattr(cruise_state, field_name, None))
    if value is not None:
      return value

  kph_value = finite_optional(getattr(car_state, "vCruiseCluster", None))
  if kph_value is None:
    kph_value = finite_optional(getattr(car_state, "vCruise", None))
  return kph_value * KPH_TO_MS if kph_value is not None else None


def source_label(data: Mapping[str, Any]) -> str:
  long_sp = service(data, "longitudinalPlanSP")
  sp_source = getattr(long_sp, "longitudinalPlanSource", None)
  if sp_source is not None:
    return enum_label(sp_source, SP_LONG_SOURCES)

  longitudinal_plan = service(data, "longitudinalPlan")
  return enum_label(getattr(longitudinal_plan, "longitudinalPlanSource", None), STANDARD_LONG_SOURCES)


def assist_status(selfdrive_state: Any) -> str:
  if selfdrive_state is None:
    return "waiting"
  if bool(getattr(selfdrive_state, "active", False)):
    return "active"
  if bool(getattr(selfdrive_state, "enabled", False)):
    return "enabled"
  if bool(getattr(selfdrive_state, "engageable", False)):
    return "ready"
  return enum_label(getattr(selfdrive_state, "state", None))


def health_from_submaster(sm: Any, services: tuple[str, ...] = FRESHNESS_SERVICES) -> SceneHealth:
  now = time.monotonic()
  stale_services: list[str] = []

  alive = getattr(sm, "alive", {})
  valid = getattr(sm, "valid", {})
  freq_ok = getattr(sm, "freq_ok", {})
  recv_time = getattr(sm, "recv_time", {})

  for name in services:
    if not alive.get(name, False) or not valid.get(name, False) or not freq_ok.get(name, True):
      stale_services.append(name)

  last_required = max((finite_float(recv_time.get(name), 0.0) for name in REQUIRED_FRESH_SERVICES), default=0.0)
  frame_age_ms = max(0.0, (now - last_required) * 1000.0) if last_required else 0.0
  if frame_age_ms > FRAME_STALE_SECONDS * 1000.0:
    for name in REQUIRED_FRESH_SERVICES:
      if name not in stale_services:
        stale_services.append(name)

  return SceneHealth(alive=alive, valid=valid, freq_ok=freq_ok, recv_time=recv_time,
                     stale_services=stale_services, frame_age_ms=frame_age_ms)


def build_scene_frame(
  data: Mapping[str, Any],
  *,
  sequence_number: int,
  mode: str,
  connected_clients: int,
  source: str,
  health: SceneHealth | None = None,
  is_metric: bool = False,
  now: float | None = None,
  mono_time_ns: int | None = None,
) -> dict[str, Any]:
  now = time.time() if now is None else now
  mono_time_ns = time.monotonic_ns() if mono_time_ns is None else mono_time_ns
  health = health or SceneHealth()

  model_v2 = service(data, "modelV2")
  longitudinal_plan = service(data, "longitudinalPlan")
  radar_state = service(data, "radarState")
  car_state = service(data, "carState")
  selfdrive_state = service(data, "selfdriveState")

  units = "metric" if is_metric else "imperial"
  ego_speed = max(0.0, finite_float(getattr(car_state, "vEgo", 0.0)))
  should_stop = model_should_stop(model_v2) or plan_should_stop(longitudinal_plan)
  stop_distance = estimate_stop_distance(model_v2, longitudinal_plan) if should_stop else None
  lanes, lane_probs = lane_lines(model_v2)
  leads = radar_leads(radar_state)
  if not leads:
    leads = model_leads(model_v2, ego_speed)

  return {
    "schemaVersion": SCHEMA_VERSION,
    "mode": mode,
    "sequence": sequence_number,
    "monoTime": mono_time_ns,
    "wallTime": now,
    "fresh": not health.stale_services,
    "units": units,
    "ego": {
      "speedMps": ego_speed,
      "displaySpeed": display_speed(ego_speed, units),
      "speedUnit": "km/h" if is_metric else "mph",
      "gear": gear_label(getattr(car_state, "gearShifter", None)),
      "engaged": bool(getattr(selfdrive_state, "enabled", False)),
      "standstill": bool(getattr(car_state, "standstill", False)),
    },
    "cruise": {
      "setSpeedMps": set_speed_mps(car_state),
      "speedLimitMps": speed_limit_mps(data),
    },
    "assist": {
      "status": assist_status(selfdrive_state),
      "longitudinalPlanSource": source_label(data),
      "shouldStop": should_stop,
      "stopDistanceM": stop_distance,
    },
    "model": {
      "path": points_from_xyzt(getattr(model_v2, "position", None)),
      "laneLines": lanes,
      "laneLineProbs": lane_probs,
      "roadEdges": road_edges(model_v2),
      "leads": leads,
    },
    "semanticObjects": [],
    "diagnostics": {
      "connectedClients": connected_clients,
      "source": source,
      "frameAgeMs": health.frame_age_ms,
      "staleServices": list(health.stale_services),
    },
  }
