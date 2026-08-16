# Flow Service — Main Detection Pipeline

The flow service is the core of the platform. It runs a 7-thread concurrent pipeline that receives raw PCAP data from the Raspberry Pi, extracts network flow features using Zeek (in pcap-replay mode), scores each flow with the ML ensemble plus a baseline calibration layer, runs selective Suricata DPI, and routes confirmed threats to the SOAR engine and SIEM writer.

---

## Architecture

```
Raspberry Pi (SPAN mirror — eth0)
        │  tcpdump | socat → TCP:9000
        ▼
[T1] packet_listener.py     — TCP server :9000, writes /tmp/live.pcap → QUEUE_1
        │
        ▼
[T2] zeek_feeder.py         — Drains QUEUE_1, spawns short-lived  zeek -r /tmp/live.pcap
        │                       (pcap-replay mode — no persistent zeek -i process)
        ▼
[T3] zeek_parser.py         — Reads conn.log (inode-aware), builds 38-feature dicts → ML_QUEUE
        │
        ▼
[T4] ML Inference Worker    — RF + Isolation Forest + Baseline Calibration → RESULT_QUEUE
        │
        ▼
[T5] DPI Worker             — Suricata on ML-flagged flows → merge → alert dict
        │
        ├──→ queue_alert()            (SIEM — non-blocking)
        ├──→ soar_evaluate()          (SOAR engine)
        └──→ POST /internal/broadcast (API → WebSocket → Dashboard)

[T6] Batch Loop             — SIEM writer: flushes queue → PostgreSQL every 2 s
[T7] Metrics Worker         — Prometheus queue-depth gauge every 1 s
```

**Zeek mode:** T2 spawns a new `zeek -r` process per PCAP batch. This is intentional — running `zeek -i` in the background would create a second Zeek process competing on `conn.log`. The startup script (`start_pipeline.sh`) kills any stale `zeek -i` processes at boot.

---

## Structure

```
flow_service/
├── main_pipeline.py          # Thread orchestrator + watchdog loop
├── pipeline_runner.py        # Thin wrapper used by start_pipeline.sh
├── unified_runner.py         # Alternative: API + pipeline in one process
├── packet_listener.py        # T1 — TCP PCAP receiver
├── zeek_feeder.py            # T2 — PCAP → zeek -r
├── zeek_parser.py            # T3 — conn.log → 38-feature dicts (inode-aware)
├── state.py                  # Shared queues (QUEUE_1, ML_QUEUE, RESULT_QUEUE) + SYSTEM_STATE
├── monitor.py                # Live queue depth / thread health monitor
├── debug_queues.py           # Debug utility — prints queue contents
├── core/
│   ├── inference_engine.py       # Loads RF + ISO Forest, runs prediction
│   ├── baseline_calibration.py   # IoT false-positive reduction layer (NEW — Session 3)
│   ├── bridge.py                 # FlowBridge — connects T3 output to inference engine
│   ├── risk_scorer.py            # Final risk score + severity label
│   ├── dpi_queue.py              # Queue between T4 and T5
│   ├── result_buffer.py          # Sliding window result buffer
│   └── result_queue.py           # Thread-safe T4 → T5 handoff queue
├── configs/
│   └── config.py                 # HOST, PORT, BUFFER_SIZE, QUEUE_MAXLEN constants
└── scripts/                      # Helper shell scripts
```

---

## Thread Details

### T1 — Packet Listener (`packet_listener.py`)
- Binds TCP server on `0.0.0.0:9000`
- Accepts the Raspberry Pi connection
- Writes incoming bytes to `/tmp/live.pcap` and appends to `QUEUE_1`
- Implements adaptive backpressure — delays receipt when `QUEUE_1` exceeds thresholds

### T2 — Zeek Feeder (`zeek_feeder.py`)
- Drains PCAP batches from `QUEUE_1`
- Writes to `/tmp/live.pcap` snapshot
- Invokes `zeek -r /tmp/live.pcap` — short-lived process, not a daemon
- Zeek writes `conn.log` to `services/flow_service/logs/zeek/current/`

### T3 — Zeek Parser (`zeek_parser.py`)
- Reads `conn.log` produced by Zeek
- **Inode-aware file tracking:** resets read position only when the file is replaced (inode changes), not on every normal append. This fixed a bug where the full file was re-read on every cycle in live mode.
- Parses each row into a 38-feature dict
- Tags known devices (WiFi Camera, BYOD Mobile) based on `system_config.yaml` — all traffic is parsed, no IP is silently dropped
- Pushes feature dicts to `ML_QUEUE`

### T4 — ML Inference Worker (`main_pipeline.py`)
- Dequeues feature dicts from `ML_QUEUE`
- Applies adaptive backpressure sampling when queue is deep (see table below)
- Calls `FlowBridge.process(flow)` → `InferenceEngine` → RF + Isolation Forest
- Passes result through `BaselineCalibration` to dampen FP score on known-good IoT shapes
- Sets `send_to_dpi = True` if `rf_proba > 0.30` OR `iso == -1`
- Pushes result to `RESULT_QUEUE`
- **Null-guard:** if `bridge.process(flow)` returns `None`, the flow is skipped via `continue` (fixes a previous T4 crash-and-restart-loop bug)

### T5 — DPI Worker (`main_pipeline.py`)
- Dequeues from `RESULT_QUEUE`
- If `send_to_dpi = True`: calls `dpi_engine.run_dpi(raw_packets)` → Suricata
- Builds final alert dict
- Calls `queue_alert()`, `soar_evaluate()`, and broadcasts to API

### T6 — Batch Writer (`siem-service/writer/batch_writer.py`)
- Runs `batch_loop()` — flushes alert queue to PostgreSQL every 2 seconds
- Normal traffic from non-IoT devices is not stored unless the ML flagged it

### T7 — Metrics Worker (`main_pipeline.py`)
- Calls `update_queue_depth(len(ML_QUEUE))` every second
- Feeds the Prometheus metrics server on port 9091

---

## Adaptive Backpressure

When `ML_QUEUE` gets deep, the inference worker samples rather than processes every flow:

| ML_QUEUE Depth | Mode | Behaviour |
|----------------|------|-----------|
| < 300 | Full | Every flow processed |
| 300 – 800 | 50% | Every 2nd flow |
| 800 – 2000 | 33% | Every 3rd flow |
| > 2000 | Sparse | Every 7th flow |

---

## ML Pipeline Detail

### Inference Engine (`core/inference_engine.py`)
Loads three `.pkl` files from `ml/training/models/`:
- `rf_model.pkl` — Random Forest (binary classifier)
- `iso_model.pkl` — Isolation Forest (anomaly detector)
- `preprocessor.pkl` — `FeaturePreprocessor` (categorical encoding + normalisation)

### Baseline Calibration (`core/baseline_calibration.py`)
Added in Session 3 to reduce false positives on real-device traffic.

**Logic:**
- Examines the raw flow dict (connection state, duration, byte counts)
- If the flow matches a known-good IoT traffic shape (normal conn_state like `SF`, non-zero duration, bidirectional bytes present), the RF probability is dampened
- Attack-shaped traffic (`S0`, `REJ`, near-zero bytes, very short duration) is **never** dampened — these always pass through at full RF score
- The dampened probability is then used in the risk score formula

**Wiring:** `risk_scorer.py` receives both the ML scores and the original `flow` dict so the calibration can inspect raw features:

```python
risk_score = risk_scorer.compute(rf_proba, iso_pred, flow)
```

### Risk Scoring (`core/risk_scorer.py`)

```
risk_score = (0.6 × rf_probability) + (0.4 × iso_anomaly_score)
             after BaselineCalibration adjustment

Severity:
  CRITICAL  ≥ 0.80  →  SOAR trigger eligible
  HIGH      ≥ 0.60  →  Alert + dashboard toast
  MEDIUM    ≥ 0.35  →  Alert logged
  LOW       < 0.35  →  Log only (non-IoT normal flows dropped before storage)
```

`risk_scorer.py` also maintains a per-IP repeat-count dict (`_repeat_counts`). When this dict exceeds 10,000 entries, the lowest-count 5,000 IPs are evicted — prevents unbounded memory growth on long-running sessions.

---

## Alert Filtering

Only genuine threats and IoT device traffic are stored in PostgreSQL:

```python
# Drop if: RF=normal AND ISO=normal AND no DPI alerts AND source is not IoT device
if not is_iot_device and rf_label == 0 and iso_pred == 1 and not dpi_alerts:
    return   # discard — pure normal traffic from non-IoT device
```

IoT device traffic (WiFi Camera, BYOD Mobile) is always stored regardless of classification — for baselining and monitoring.

---

## Config Centralization

All device IPs (`IOT_DEVICES`, `CAMERA_IP`, `BACKEND_IP`) are loaded from a single location:

```python
from shared.utils.config_loader import ConfigLoader
cfg = ConfigLoader.load()

IOT_DEVICES = set(cfg['network']['iot_devices'])
CAMERA_IP   = cfg['network']['camera_ip']
BACKEND_IP  = cfg['network']['backend_ip']
```

No IP is hardcoded in `main_pipeline.py`, `zeek_parser.py`, or any other file in this service. Update `shared/config/system_config.yaml` and restart to pick up new IPs.

The previous bug of `os.environ["ZEEK_MODE"] = "pcap"` being hardcoded in `main_pipeline.py` (which silently overrode the env var set by `start_pipeline.sh`) has been removed. `ZEEK_MODE` is now set exclusively by the startup script.

---

## Running

Always start via the master script from project root:

```bash
export ZEEK_INTERFACE=eth0   # your NIC connected to the managed switch
bash infrastructure/scripts/start_pipeline.sh
```

Do not run `main_pipeline.py` directly — the startup script sets required environment variables (`ZEEK_LOG_DIR`, `ZEEK_MODE`, `LIVE_PCAP`, `INTERNAL_TOKEN`, `PYTHONPATH`).

To monitor live queue depths and thread health:

```bash
python3 -m services.flow_service.monitor
```

---

## Logs

All logs in `logs/pipeline/` with rotating handlers (5 MB max, 3 backups):

| Log File | Thread | Contents |
|----------|--------|----------|
| `main_pipeline.log` | Main | Thread start/stop, watchdog restarts |
| `packet_listener.log` | T1 | Pi connection events, backpressure |
| `zeek_feeder.log` | T2 | Zeek invocations, PCAP batches |
| `zeek_parser.log` | T3 | Feature extraction, inode resets, parse errors |
| `ml_inference.log` | T4 | Inference results, calibration events, backpressure |
| `dpi_worker.log` | T5 | Suricata results, DPI timeouts |
| `metrics_worker.log` | T7 | Prometheus updates |

---

## Dependencies

- **Zeek 6+** — must be on `PATH` or at `/opt/zeek/bin/zeek`
- **Suricata** — for T5 DPI (gracefully absent — returns empty list if not installed)
- **Python 3.10+** — `threading`, `collections.deque`, `requests`, `yaml`, `joblib`
- **scikit-learn** — RF + Isolation Forest model loading
- **psycopg2** — PostgreSQL (via SIEM batch writer)
