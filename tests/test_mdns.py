from __future__ import annotations

from ap_visualizer.mdns import (
  MdnsPublisher,
  build_address_command,
  build_service_command,
)


class FakeProcess:
  def __init__(self) -> None:
    self.terminated = False
    self.killed = False

  def poll(self):
    return None if not self.terminated else 0

  def terminate(self) -> None:
    self.terminated = True

  def kill(self) -> None:
    self.killed = True
    self.terminated = True

  def wait(self, timeout=None):
    return 0


def test_mdns_commands_publish_visualizer_alias_and_http_service():
  assert build_address_command("avahi-publish", "ap-visualizer.local", "192.168.68.93") == [
    "avahi-publish",
    "--no-fail",
    "-a",
    "ap-visualizer.local",
    "192.168.68.93",
  ]

  assert build_service_command("avahi-publish", "ap-visualizer.local", "AP Visualizer", 8077) == [
    "avahi-publish",
    "--no-fail",
    "-s",
    "AP Visualizer",
    "_http._tcp",
    "8077",
    "path=/",
    "url=http://ap-visualizer.local:8077",
  ]


def test_publisher_republishes_when_ip_changes():
  ips = iter(["192.168.68.93", "192.168.68.93", "192.168.68.94"])
  commands = []

  def fake_popen(command, **kwargs):
    commands.append(command)
    return FakeProcess()

  publisher = MdnsPublisher(ip_provider=lambda: next(ips), popen=fake_popen)

  publisher.sync()
  assert len(commands) == 2
  assert publisher.published_ip == "192.168.68.93"

  publisher.sync()
  assert len(commands) == 2

  publisher.sync()
  assert len(commands) == 4
  assert publisher.published_ip == "192.168.68.94"

  publisher.stop()


def test_publisher_handles_missing_avahi_without_crashing():
  def fake_popen(command, **kwargs):
    raise FileNotFoundError("avahi-publish")

  publisher = MdnsPublisher(ip_provider=lambda: "192.168.68.93", popen=fake_popen)

  publisher.sync()

  assert publisher.processes == []
  assert publisher.published_ip is None
