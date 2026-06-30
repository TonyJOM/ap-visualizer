from __future__ import annotations

import argparse
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable

DEFAULT_HOSTNAME = "ap-visualizer.local"
DEFAULT_SERVICE_NAME = "AP Visualizer"
DEFAULT_SERVICE_TYPE = "_http._tcp"
DEFAULT_PORT = 8077
DEFAULT_INTERVAL_SECONDS = 5.0
PUBLISH_STOP_TIMEOUT_SECONDS = 2.0

PopenFactory = Callable[..., subprocess.Popen]


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


def build_address_command(avahi_publish: str, hostname: str, ip_address: str) -> list[str]:
  return [avahi_publish, "--no-fail", "-a", hostname, ip_address]


def build_service_command(avahi_publish: str, hostname: str, service_name: str, port: int) -> list[str]:
  return [
    avahi_publish,
    "--no-fail",
    "-s",
    service_name,
    DEFAULT_SERVICE_TYPE,
    str(port),
    "path=/",
    f"url=http://{hostname}:{port}",
  ]


class MdnsPublisher:
  def __init__(
    self,
    hostname: str = DEFAULT_HOSTNAME,
    service_name: str = DEFAULT_SERVICE_NAME,
    port: int = DEFAULT_PORT,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    avahi_publish: str = "avahi-publish",
    ip_provider: Callable[[], str | None] = local_ip,
    popen: PopenFactory = subprocess.Popen,
  ) -> None:
    self.hostname = hostname
    self.service_name = service_name
    self.port = port
    self.interval_seconds = interval_seconds
    self.avahi_publish = avahi_publish
    self.ip_provider = ip_provider
    self.popen = popen
    self.processes: list[subprocess.Popen] = []
    self.published_ip: str | None = None

  def _publisher_running(self) -> bool:
    return bool(self.processes) and all(process.poll() is None for process in self.processes)

  def _start(self, ip_address: str) -> None:
    self.stop()
    commands = [
      build_address_command(self.avahi_publish, self.hostname, ip_address),
      build_service_command(self.avahi_publish, self.hostname, self.service_name, self.port),
    ]

    try:
      for command in commands:
        self.processes.append(self.popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
      self.published_ip = ip_address
    except (FileNotFoundError, OSError) as exc:
      self.stop()
      self.published_ip = None
      print(f"AP Visualizer mDNS unavailable: {exc}", file=sys.stderr)

  def stop(self) -> None:
    processes = self.processes
    self.processes = []

    for process in processes:
      if process.poll() is not None:
        continue
      try:
        process.terminate()
        process.wait(timeout=PUBLISH_STOP_TIMEOUT_SECONDS)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
      except ProcessLookupError:
        pass

    self.published_ip = None

  def sync(self) -> None:
    ip_address = self.ip_provider()
    if not ip_address:
      self.stop()
      return

    if ip_address != self.published_ip or not self._publisher_running():
      self._start(ip_address)

  def run_forever(self, should_stop: Callable[[], bool] | None = None) -> None:
    if should_stop is None:
      should_stop = lambda: False

    try:
      while not should_stop():
        self.sync()
        time.sleep(self.interval_seconds)
    finally:
      self.stop()


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Publish AP Visualizer over mDNS")
  parser.add_argument("--hostname", default=DEFAULT_HOSTNAME)
  parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME)
  parser.add_argument("--port", default=DEFAULT_PORT, type=int)
  parser.add_argument("--interval", default=DEFAULT_INTERVAL_SECONDS, type=float)
  parser.add_argument("--avahi-publish", default="avahi-publish")
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  stopping = False

  def request_stop(signum, frame) -> None:
    nonlocal stopping
    stopping = True

  signal.signal(signal.SIGINT, request_stop)
  signal.signal(signal.SIGTERM, request_stop)

  publisher = MdnsPublisher(
    hostname=args.hostname,
    service_name=args.service_name,
    port=args.port,
    interval_seconds=args.interval,
    avahi_publish=args.avahi_publish,
  )
  publisher.run_forever(lambda: stopping)


if __name__ == "__main__":
  main()
