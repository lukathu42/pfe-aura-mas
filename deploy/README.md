# Deployment / security configuration

The prototype runs fully offline with no brokers at all (`LocalBus` +
JSONL alert log), which is what the offline tests and single-process demos use.
Everything below applies when the MQTT/Redis brokers or the operator console
are actually started.

## Broker credentials (one-off)

```bash
./deploy/init_secrets.sh          # writes .env + deploy/mosquitto/passwd (both git-ignored)
set -a && source .env && set +a
docker compose up -d
```

`docker compose up` fails fast if `AURA_REDIS_PASSWORD` is unset, and Mosquitto
refuses anonymous clients (`deploy/mosquitto/mosquitto.conf`).

Both brokers are published on `127.0.0.1` only. The bus carries surveillance
events, alert severities and evidence file paths, and any client that can reach
it can also *inject* events — which drives PolicyAgent decisions — so it must
never be exposed on a site network directly. Remote edge nodes (the Raspberry
Pi split described in the README) should reach it through an SSH tunnel or a
WireGuard address:

```bash
# on the Pi
ssh -N -L 1883:127.0.0.1:1883 user@laptop
```

For a real multi-host deployment, terminate MQTT over TLS and point the agents
at it with `AURA_MQTT_TLS=1` (plus `AURA_MQTT_CA_CERT` for a private CA).

## Environment variables read by the code

| Variable | Used by | Default |
| --- | --- | --- |
| `AURA_MQTT_HOST` / `AURA_MQTT_PORT` | `MqttBus` | `localhost` / `1883` |
| `AURA_MQTT_USERNAME` / `AURA_MQTT_PASSWORD` | `MqttBus` | unset (warns for non-loopback hosts) |
| `AURA_MQTT_TLS` / `AURA_MQTT_CA_CERT` | `MqttBus` | off |
| `AURA_REDIS_URL` | `AlertStore` | `redis://localhost:6379` |
| `AURA_DASHBOARD_PASSWORD` | Streamlit console | unset → console refuses to render |
| `AURA_DASHBOARD_ALLOW_ANONYMOUS` | Streamlit console | unset → opt-out for isolated offline demos |
| `AURA_EVIDENCE_DIR` | Streamlit console | `data/evidence` |
| `OPENAI_API_KEY` / `OPENAI_API_BASE` | `ExplanationAgent` | unset (agent falls back to its deterministic template) |

No secret is ever hardcoded: every credential is read from the environment.

## Operator console

```bash
set -a && source .env && set +a
streamlit run aura_mas/dashboard/app.py --server.address 127.0.0.1
```

The console is fail-closed: without `AURA_DASHBOARD_PASSWORD` it renders only a
lock message, because it displays alerts and anonymized evidence imagery and
writes acknowledge/dismiss decisions into the audit log. For a throwaway
offline demo, `AURA_DASHBOARD_ALLOW_ANONYMOUS=1` bypasses the gate — never set
it on a machine reachable from a network. Streamlit's shared-secret gate is a
single-role guard, not per-operator identity; a multi-operator deployment
should put an authenticating reverse proxy (or SSO) in front of it so audit-log
entries can be attributed to a named person instead of `"operator"`.

Evidence images are only rendered when they resolve inside `AURA_EVIDENCE_DIR`,
so an injected alert cannot make the console read arbitrary host files.

## Dependencies

`requirements.txt` uses lower bounds so a fresh install picks up security
patches. Audit before a delivery build:

```bash
pip install pip-audit && pip-audit
```
