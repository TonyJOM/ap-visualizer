from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

from aiohttp import web, WSMsgType

from ap_visualizer.scene import LIVE_SERVICES, build_scene_frame, health_from_submaster
from ap_visualizer.sim import make_sim_frame

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8077
CANONICAL_URL = f"http://ap-visualizer.local:{DEFAULT_PORT}"
FRAME_INTERVAL_SECONDS = 1.0 / 20.0
ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"


def ensure_openpilot_path() -> None:
  repo_parent = ROOT.parent
  if (repo_parent / "cereal").exists() and str(repo_parent) not in sys.path:
    sys.path.insert(0, str(repo_parent))


def local_ip() -> str | None:
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.connect(("8.8.8.8", 80))
      return sock.getsockname()[0]
  except OSError:
    try:
      return socket.gethostbyname(socket.gethostname())
    except OSError:
      return None


def display_url(request: web.Request | None = None) -> str:
  if request is not None:
    host = request.headers.get("Host", "")
    if host:
      return f"http://{host}"
  ip = local_ip()
  return f"http://{ip}:{DEFAULT_PORT}" if ip else CANONICAL_URL


class SceneSource:
  mode = "live"
  source_name = "cereal"

  async def next_frame(self, sequence_number: int, connected_clients: int) -> dict[str, Any]:
    raise NotImplementedError


class SimulatorSceneSource(SceneSource):
  mode = "sim"
  source_name = "synthetic"

  async def next_frame(self, sequence_number: int, connected_clients: int) -> dict[str, Any]:
    return make_sim_frame(sequence_number, connected_clients)


class LiveSceneSource(SceneSource):
  mode = "live"
  source_name = "cereal"

  def __init__(self) -> None:
    ensure_openpilot_path()
    from cereal import messaging
    from openpilot.common.params import Params

    self.params = Params()
    self.sm = messaging.SubMaster(
      list(LIVE_SERVICES),
      poll="modelV2",
      ignore_alive=["liveMapDataSP"],
      ignore_avg_freq=["liveMapDataSP"],
      ignore_valid=["liveMapDataSP"],
    )

  async def next_frame(self, sequence_number: int, connected_clients: int) -> dict[str, Any]:
    self.sm.update(0)
    health = health_from_submaster(self.sm)
    is_metric = bool(self.params.get_bool("IsMetric"))
    data = {name: self.sm[name] for name in LIVE_SERVICES}
    return build_scene_frame(
      data,
      sequence_number=sequence_number,
      mode=self.mode,
      connected_clients=connected_clients,
      source=self.source_name,
      health=health,
      is_metric=is_metric,
    )


def create_source(mode: str) -> SceneSource:
  if mode == "sim":
    return SimulatorSceneSource()
  if mode == "live":
    return LiveSceneSource()

  try:
    return LiveSceneSource()
  except Exception:
    return SimulatorSceneSource()


class VisualizerServer:
  def __init__(self, source: SceneSource) -> None:
    self.source = source
    self.active_ws: web.WebSocketResponse | None = None
    self.sequence = 0
    self.last_frame: dict[str, Any] | None = None
    self.started_at = time.monotonic()

  @property
  def connected_clients(self) -> int:
    return int(self.active_ws is not None and not self.active_ws.closed)

  async def health(self, request: web.Request) -> web.Response:
    return web.json_response({
      "ok": True,
      "mode": self.source.mode,
      "source": self.source.source_name,
      "url": CANONICAL_URL,
      "fallbackUrl": display_url(request),
      "connectedClients": self.connected_clients,
      "hasFrame": self.last_frame is not None,
      "uptimeSeconds": round(time.monotonic() - self.started_at, 3),
    })

  async def latest(self, request: web.Request) -> web.Response:
    if self.last_frame is None:
      return web.json_response({"ok": False, "reason": "No scene frame has been produced yet."}, status=503)
    return web.json_response(self.last_frame)

  async def qr_svg(self, request: web.Request) -> web.Response:
    url = CANONICAL_URL
    try:
      import qrcode
      import qrcode.image.svg

      factory = qrcode.image.svg.SvgPathImage
      image = qrcode.make(url, image_factory=factory)
      svg = image.to_string(encoding="unicode")
    except Exception:
      svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120" viewBox="0 0 320 120">'
        '<rect width="320" height="120" fill="white"/>'
        '<text x="16" y="60" font-family="system-ui, sans-serif" font-size="16" fill="black">'
        f'{url}</text></svg>'
      )
    return web.Response(text=svg, content_type="image/svg+xml")

  async def websocket(self, request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=15.0)
    await ws.prepare(request)

    if self.active_ws is not None and not self.active_ws.closed:
      await ws.send_str(json.dumps({"type": "busy", "reason": "Another AP Visualizer client is already connected."}))
      await ws.close(code=1008, message=b"single client policy")
      return ws

    self.active_ws = ws

    try:
      while not ws.closed:
        started = time.monotonic()
        self.sequence += 1
        frame = await self.source.next_frame(self.sequence, self.connected_clients)
        self.last_frame = frame
        try:
          await ws.send_str(json.dumps(frame, separators=(",", ":")))
        except ConnectionResetError:
          break

        try:
          message = await ws.receive(timeout=0.001)
          if message.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
            break
        except asyncio.TimeoutError:
          pass

        elapsed = time.monotonic() - started
        await asyncio.sleep(max(0.0, FRAME_INTERVAL_SECONDS - elapsed))
    finally:
      if self.active_ws is ws:
        self.active_ws = None

    return ws

  async def index(self, request: web.Request) -> web.Response:
    index_path = DIST_DIR / "index.html"
    if index_path.exists():
      return web.FileResponse(index_path)
    return web.Response(
      text="AP Visualizer frontend has not been built. Run `npm run build` in the ap-visualizer repo.",
      content_type="text/plain",
      status=503,
    )


VISUALIZER_KEY = web.AppKey("visualizer", VisualizerServer)


def create_app(mode: str = "auto") -> web.Application:
  state = VisualizerServer(create_source(mode))
  app = web.Application()
  app[VISUALIZER_KEY] = state
  app.router.add_get("/health", state.health)
  app.router.add_get("/api/scene/latest", state.latest)
  app.router.add_get("/qr.svg", state.qr_svg)
  app.router.add_get("/ws/scene", state.websocket)
  if DIST_DIR.exists():
    app.router.add_static("/assets", DIST_DIR / "assets", name="assets")
  app.router.add_get("/", state.index)
  app.router.add_get("/{tail:.*}", state.index)
  return app


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="AP Visualizer local web server")
  parser.add_argument("--host", default=os.getenv("AP_VISUALIZER_HOST", DEFAULT_HOST))
  parser.add_argument("--port", default=int(os.getenv("AP_VISUALIZER_PORT", DEFAULT_PORT)), type=int)
  parser.add_argument("--mode", choices=("auto", "live", "sim"), default=os.getenv("AP_VISUALIZER_MODE", "auto"))
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  web.run_app(create_app(args.mode), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
  main()
