---
name: testing-operator-console
description: How to run and adversarially test the AURA-MAS Streamlit operator console (auth gate, alert feed, evidence rendering) and the replay pipeline without Docker, Redis, MQTT or GPU deps.
---

# Testing the AURA-MAS operator console

## Environment (no `.venv` is checked in)

```bash
python3 -m venv /tmp/v
/tmp/v/bin/pip install pytest numpy streamlit opencv-python-headless   # add librosa for audio replay
mkdir -p /tmp/pkg && ln -sfn <repo>/code /tmp/pkg/aura_mas             # code/ must import as aura_mas
export PYTHONPATH=/tmp/pkg
cd <repo>                                                             # ALWAYS run from repo root:
                                                                      # data/evidence + data/*.jsonl paths are relative
/tmp/v/bin/python -m pytest /tmp/pkg/aura_mas/tests -q                # 9 passed, <1s
```

Redis/MQTT/Docker are not required — `AlertStore` falls back to JSONL and `make_bus` to `LocalBus`.
`torch`/`ultralytics`/`tensorflow` are optional: video scenarios need `ultralytics` (multi-GB, install
torch from the CPU wheel index first); audio-only scenarios (`scenarios/audio_*.json`) need only
`librosa` and take ~40s, which makes them the cheap way to prove the replay pipeline still emits alerts.

## Running the dashboard in each auth state

`code/dashboard/app.py:authenticated()` is env-driven, so test each state with a separate Streamlit
process on its own port (env vars are read at request time, but separate processes keep sessions clean):

```bash
# locked (fail closed)
streamlit run /tmp/pkg/aura_mas/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
# password gate
AURA_DASHBOARD_PASSWORD=... streamlit run ... --server.port 8502
# documented escape hatch
AURA_DASHBOARD_ALLOW_ANONYMOUS=1 streamlit run ... --server.port 8503
```

Add `--server.headless true` so Streamlit does not try to open its own browser. A browser refresh (F5)
starts a new Streamlit session, so `session_state.authenticated` is dropped and the login form returns —
that is the expected no-state-leak behaviour, not a bug. Chrome may pop a "Save password?" bubble after
sign-in that covers the detail panel; click "Never" before screenshotting.

## Feeding the console crafted alerts

The console shows `AlertStore.read_alerts()` from `data/alerts.jsonl`; when that file is missing/empty it
falls back to globbing `data/alerts_*.jsonl` (`load_alerts`, app.py). So the least invasive way to inject
adversarial records while keeping the existing cited artifacts loaded is a **new** file matching that
glob (e.g. `data/alerts_zz_testfixture.jsonl`), deleted afterwards. Give fixtures the newest timestamps
so they sort to the top of the feed.

Useful fixture shapes:
- hostile `event_type` / `zone` / `sensors` (`<img src=x onerror="document.title='PWNED'">`,
  `</span><b>PWNED</b>`, `<script>...</script>`) — the strongest visible assertion is that the browser
  **tab title never changes**, plus the strings appearing as literal text in the detail panel.
- `confidence: 5.0` → must display `1.00` (clamped by `_parse_message`).
- malformed lines (wrong field type, >1 MiB payload, missing required fields) → must be dropped, which
  you verify through the `Alert feed (N)` header count, not just logs.
- evidence lists mixing `/etc/hostname`, an image in `/tmp`, a `data/evidence/../../../tmp/...` traversal
  path and one real `data/evidence/*.jpg` → only the in-root JPG may render. Make the out-of-root image a
  solid bright colour so an escape would be unmistakable in a screenshot.

### Known UI-unreachable path

An alert whose `severity` is not `CRITICAL`/`WARNING`/`INFO` is filtered out of the feed entirely by the
`Severity` multiselect (its options are hard-coded), so it can never be selected and the
`SEVERITY_COLOR.get(..., DEFAULT_COLOR)` fallback (and escaping of the `severity` field) cannot be
exercised through the UI. Verify those at unit level and report them as UI-untestable rather than passing.

## Cleanup

Delete fixture JSONLs, `data/audit.jsonl` (created by the Acknowledge/Dismiss buttons), and any
`data/alerts_*`/`results/run_*` files a test replay produced; then confirm `git status --porcelain` is empty —
`data/` and `results/` hold cited thesis artifacts.

## Devin Secrets Needed

None. The dashboard password is arbitrary (you set `AURA_DASHBOARD_PASSWORD` yourself) and no external
services are contacted.
