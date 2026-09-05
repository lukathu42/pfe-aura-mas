# Live Monitoring Demonstration Quickstart

This path creates a visibly attributable `LIVE` Monitoring Session. It does not substitute a Prepared Replay when a camera fails.

## Start the operational source of truth

```bash
python -m aura_mas.operations.service --db data/aura_operations.db
```

Create and save the example immutable Policy Version:

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/policies \
  -H 'Content-Type: application/json' \
  --data-binary @config/site_policy.example.json
```

Copy the returned `policy_version_id`, then start a Live Monitoring Session:

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "mode":"LIVE",
    "policy_version_id":"POLICY_ID",
    "live_sources":[
      {"camera_id":"cam_entry_pi","transport":"RTSP","endpoint_fingerprint":"sha256:PI_ENDPOINT","continuous":true},
      {"camera_id":"cam_verifier_usb","transport":"USB","endpoint_fingerprint":"sha256:USB_DEVICE","continuous":true}
    ]
  }'
```

Use stable SHA-256 fingerprints of the configured endpoint/device identities; do not place credentials or raw RTSP URLs in the session record.

## Start the two camera views

Copy `config/live_cameras.example.json` to `config/live_cameras.json`, then set the two source variables. A local USB camera can use an HTTP/MJPEG publisher; the internal Pi link should use authenticated RTSP.

```bash
export AURA_CAMERA_PI_URL='rtsp://user:password@pi-host/live'
export AURA_CAMERA_USB_URL='http://127.0.0.1:8081/video'
python -m aura_mas.streaming.live_cameras \
  --config config/live_cameras.json \
  --session-id SESSION_ID
```

Camera credentials are resolved from environment variables and are never written to the health document. Camera health is posted to the operational service; an offline camera creates a Sensor Health Incident, not a surveillance anomaly.

## Open the operator console

```bash
cd frontend
AURA_OPERATIONS_URL=http://127.0.0.1:8090 npm run dev
```

The top operational panel displays Session Mode, immutable Policy Version, camera degradation, Search Level, and durable workflow/verdict state. Prepared Replay controls remain separately labelled below it.
