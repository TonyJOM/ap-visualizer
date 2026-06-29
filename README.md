# AP Visualizer

AP Visualizer is a display-only companion screen for AdventurePilot. It serves a Safari-friendly web app from the Comma and renders a Rivian-inspired driver-assistance cluster on a second device.

## What it shows

- Ego truck, predicted path, lane lines, road edges, and lead vehicles.
- Driving essentials: speed, set speed, speed limit when available, gear, engagement state, and assist status.
- Generic model/e2e stop intent as a neutral stop line. It does not label stop signs, traffic lights, or intersections.

## Safety and privacy boundaries

- Display only. It never sends control commands to AdventurePilot, Panda, CAN, or the vehicle.
- No camera streaming, no raw CAN endpoint, no hidden telemetry, and no persistent route or scene logging.
- WebSocket frames are normalized render data, not raw openpilot messages.

## Public repo pre-push audit

Before pushing publicly, inspect changes for:

- Secrets, tokens, SSH keys, dongle IDs, VINs, private route names, private IPs, and personal URLs.
- Captured camera frames, route logs, or real drive recordings.
- Any code that writes control messages, publishes to cereal, sends CAN, or stores drive data.

Codex should not commit or push this repo. The owner reviews all code before any public push.

## Development

```bash
npm install
npm run dev
```

The frontend dev server uses synthetic data by default. The production server can be run with:

```bash
python -m ap_visualizer.server --mode sim
```

When installed as an AdventurePilot submodule at `ap_visualizer_repo`, AdventurePilot's manager can start the server on port `8077`.

## AdventurePilot integration

After local review and after the public GitHub repo exists, add this repo to AdventurePilot:

```bash
cd /data/openpilot
git submodule add https://github.com/TonyJOM/ap-visualizer.git ap_visualizer_repo
git submodule update --init --recursive
```

The AdventurePilot manager process is guarded by `APVisualizerEnabled` and by the presence of `ap_visualizer_repo/ap_visualizer/server.py` plus `ap_visualizer_repo/dist/index.html`.
