# API Service

The FastAPI backend that connects the detection pipeline, the PostgreSQL database, and the React dashboard. It exposes a REST API for alert queries and system management, a WebSocket endpoint for real-time alert streaming, and a protected internal endpoint that the pipeline uses to broadcast new alerts to all connected dashboard clients.

---

## Responsibilities

- Stream live alerts to the dashboard via WebSocket (`/ws`)
- Replay the last 50 database alerts to any newly connected dashboard client (so the feed is never empty on first load)
- Expose REST endpoints for alert history, SOAR controls, and system management
- Accept authenticated broadcasts from the pipeline over HTTP POST
- Serve NIC list to the dashboard NIC picker
- Provide playbook enable/disable toggle state to the SOAR engine via `playbook_flags.json`
- Tail log files and report pipeline/DB/model health to the dashboard

---

## Structure

```
api-service/
├── app/
│   └── main.py       # Full FastAPI application — all routes, WebSocket, DB, internal auth
└── run_api.py        # Entry point — runs uvicorn on :8000
```

---

## Internal Token Authentication

The `/internal/broadcast` endpoint is called by `main_pipeline.py` every time a new alert is produced. It is protected by a shared secret:

- At startup, `start_pipeline.sh` generates a token: `INTERNAL_TOKEN=$(python3 -c 'import secrets; print(secrets.token_hex(32))')`
- This token is exported as an environment variable before both the API and pipeline processes are launched
- The pipeline sends the token as the `x-internal-token` header
- The API validates it with `secrets.compare_digest()` — constant-time comparison to prevent timing attacks
- Requests without a valid token receive `HTTP 401`

This prevents any external process from injecting fake alerts into the WebSocket stream.

---

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns `{"status": "ok"}` — polled by `start_pipeline.sh` to confirm API is up |

---

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/alerts` | Latest alerts (default limit 100). Optional `?severity=` filter. Also returns `total` count and per-severity breakdown for the Stats Bar |
| `GET` | `/api/alerts/all` | Full alert history. Optional filters: `severity`, `attack_type`, `src_ip`, `limit` |
| `POST` | `/api/review/{alert_id}` | Analyst verdict: `"TP"` or `"FP"`. FP flows are exported to `ml/datasets/fp_dataset.csv` for retraining |

---

### SOAR

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/soar/log` | Last 50 playbook execution records (from in-memory log) |
| `GET` | `/api/soar/quarantined` | List of currently quarantined device IPs |
| `POST` | `/api/soar/unblock/{src_ip}` | Remove UFW block rule for an IP (dashboard UNBLOCK button) |
| `GET` | `/api/soar/playbooks` | Current enabled/disabled state of all 4 playbooks |
| `POST` | `/api/soar/playbooks/{name}` | Toggle a playbook on or off at runtime |

#### Playbook Toggle Mechanism

Toggle state is held in memory (`_playbook_enabled` dict) and also written to `logs/soar/playbook_flags.json` on every change. The SOAR engine reads this file on every alert evaluation — so changes take effect immediately with no pipeline restart:

```json
{
  "block_attacker":    true,
  "camera_defense":    true,
  "quarantine_device": true,
  "scan_detection":    true
}
```

Valid playbook names for `POST /api/soar/playbooks/{name}`:
- `block_attacker`
- `camera_defense`
- `quarantine_device`
- `scan_detection`

---

### System Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/system/status` | Pipeline running, Zeek active, DB connected, models present, alert counts |
| `GET` | `/api/system/interfaces` | Available network interfaces on the backend machine (for dashboard NIC picker) |
| `POST` | `/api/system/start` | Launch `start_pipeline.sh` in background |
| `POST` | `/api/system/stop` | Run `stop_pipeline.sh` |
| `POST` | `/api/system/train` | Start ML model training in background |
| `POST` | `/api/system/reset-firewall` | Run `reset_firewall.sh` to clear all SOAR firewall rules |
| `POST` | `/api/system/clear-db` | Truncate the alerts table (fresh start) |
| `GET` | `/api/system/logs/{service}` | Tail log files |

#### `GET /api/system/interfaces`
Returns a list of network interface names from the backend machine (calls `ip link show` internally). Used by the dashboard **System Control** NIC picker dropdown so the user can select the correct Zeek capture interface without knowing its name in advance.

#### `GET /api/system/logs/{service}`
Valid `service` values:

| Value | Log File |
|-------|----------|
| `pipeline` | `logs/pipeline/main_pipeline.log` |
| `api` | `logs/dashboard/api_service.log` |
| `zeek` | `services/flow_service/logs/zeek/current/conn.log` |
| `parser` | `logs/pipeline/zeek_parser.log` |
| `ml` | `logs/pipeline/ml_inference.log` |
| `dpi` | `logs/pipeline/dpi_worker.log` |
| `soar` | `logs/siem/soar_engine.log` |
| `siem` | `logs/siem/batch_writer.log` |
| `startup` | `logs/pipeline/main_pipeline_stdout.log` |
| `training` | `logs/pipeline/training.log` |

---

### WebSocket

| Path | Description |
|------|-------------|
| `ws://host:8000/ws` | Real-time alert stream. On connect, replays last 50 DB alerts immediately. Stays open and pushes every new alert broadcast by the pipeline |

On-connect replay was added in Session 3 to fix the issue where the Alert Feed, Anomaly Gauge, and Attack Timeline were all blank when no new traffic had arrived yet.

---

### Internal (Pipeline → API)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/internal/broadcast` | Receives an alert dict from the pipeline and fans it out to all connected WebSocket clients. Requires valid `x-internal-token` header |

---

## Database Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fyp_security` | Database name |
| `DB_USER` | `postgres` | Username |
| `DB_PASS` | `postgres` | Password — set via env var, never hardcoded |

---

## Other Environment Variables

| Variable | Set by | Description |
|----------|--------|-------------|
| `INTERNAL_TOKEN` | `start_pipeline.sh` (generated at boot) | Shared secret for `/internal/broadcast` |
| `FP_DATASET_PATH` | `start_pipeline.sh` | Path for FP export CSV — `ml/datasets/fp_dataset.csv` |

---

## Running

The API is always started by `infrastructure/scripts/start_pipeline.sh` at step 7. To run it manually for development:

```bash
cd services/api-service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or via the run script:

```bash
python3 services/api-service/run_api.py
```

Logs are written to `logs/dashboard/uvicorn.log` and `logs/dashboard/api_service.log`.

---

## CORS

CORS is set to allow all origins (`*`) for development convenience. Tighten `allow_origins` before any production deployment.

---

## Key Port

| Port | Service |
|------|---------|
| `8000` | FastAPI REST API + WebSocket |
