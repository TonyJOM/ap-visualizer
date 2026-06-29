from __future__ import annotations

import asyncio

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer

from ap_visualizer.server import create_app


def test_health_endpoint_reports_server_state():
  async def run():
    server = TestServer(create_app("sim"))
    await server.start_server()
    try:
      async with ClientSession() as session:
        async with session.get(server.make_url("/health")) as response:
          data = await response.json()
          assert response.status == 200
          assert data["ok"] is True
          assert data["mode"] == "sim"
          assert data["connectedClients"] == 0
    finally:
      await server.close()

  asyncio.run(run())


def test_websocket_rejects_newest_client_when_busy():
  async def run():
    server = TestServer(create_app("sim"))
    await server.start_server()
    try:
      async with ClientSession() as session:
        ws_one = await session.ws_connect(server.make_url("/ws/scene"))
        first_frame = await ws_one.receive_json(timeout=1.0)
        assert first_frame["schemaVersion"] == 1

        ws_two = await session.ws_connect(server.make_url("/ws/scene"))
        busy = await ws_two.receive_json(timeout=1.0)
        assert busy["type"] == "busy"

        await ws_two.close()
        await ws_one.close()
    finally:
      await server.close()

  asyncio.run(run())

