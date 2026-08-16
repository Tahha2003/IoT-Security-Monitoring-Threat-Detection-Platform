# DPI Service — Deep Packet Inspection Engine

The DPI service wraps Suricata to perform signature-based deep packet inspection on network flows that have been flagged by the ML inference engine. It runs selectively — not on every flow — keeping overhead minimal while ensuring every suspicious flow gets signature-level verification.

---

## Role in the Pipeline

DPI is only invoked when the ML inference worker (T4) sets `send_to_dpi = True`:

```
T4 ML Inference Worker
        │
        ├── send_to_dpi = False ──→ skip DPI → build alert from ML result only
        │
        └── send_to_dpi = True  ──→ T5 DPI Worker
                                          │
                                    dpi_engine.run_dpi(packets)
                                          │
                                    Write temp PCAP → spawn Suricata
                                          │
                                    Parse eve.json → extract alert entries
                                          │
                                    Return [{sig, cat, severity}, ...]
                                          │
                                    Merge with ML result → final alert dict
                                          │
                                    queue_alert() + soar_evaluate() + broadcast
```

### DPI Trigger Condition

```python
send_to_dpi = (rf_proba > 0.30) or (iso_pred == -1)
```

- `rf_proba > 0.30` — RF classifier assigned more than 30% attack probability
- `iso_pred == -1` — Isolation Forest flagged this flow as anomalous

Normal traffic (both RF and ISO agree it's benign) skips DPI entirely.

---

## Structure

```
dpi-service/
├── parser/
│   └── dpi_engine.py     # Suricata wrapper with UUID-based job IDs + worker thread pool
└── __init__.py
```

---

## How It Works (`parser/dpi_engine.py`)

### Worker Pool
On first use, `dpi_engine.py` spawns a pool of worker threads (`DPI_WORKER_COUNT = max(2, cpu_count)`). This avoids the overhead of launching a new Suricata process synchronously per flow.

### Per-Flow Execution

For each flagged flow:

1. Raw packet bytes are written to a temp PCAP file in `/tmp/dpi_<uuid>/` — UUID generated via `uuid.uuid4()` to guarantee no job-ID collisions (previous version used `id(packets)` — a memory address that could be reused)
2. Suricata is invoked: `suricata -r flow.pcap -c /etc/suricata/suricata.yaml -l /tmp/dpi_<uuid>/`
3. Suricata writes `eve.json` to the temp directory
4. `dpi_engine.py` reads `eve.json` and filters for `event_type == "alert"` entries
5. Results returned as a list of `{sig, cat, severity}` dicts
6. Temp directory is cleaned up

### Result Format

```python
# Non-empty: Suricata matched one or more signatures
[
    {
        "sig":      "ET SCAN Nmap Scripting Engine User-Agent Detected",
        "cat":      "Web Application Attack",
        "severity": 2
    }
]

# Empty: no signature matches — alert built from ML result alone
[]
```

---

## UUID Job ID Fix

In Session 1, the job ID was changed from `id(packets)` to `uuid.uuid4()`.

The `id()` of a Python object is its memory address — after an object is garbage collected, a new object can be allocated at the same address, creating a collision between two concurrent DPI jobs pointing to the same temp directory. `uuid.uuid4()` generates a globally unique identifier for every job, eliminating this race condition.

```python
# Before (buggy)
job_id = id(packets)           # could collide if old job GC'd and same addr reused

# After (fixed)
import uuid
job_id = uuid.uuid4().hex      # guaranteed unique per job
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SURICATA_BIN` | `/usr/bin/suricata` | Path to Suricata binary |
| `SURICATA_CONF` | `/etc/suricata/suricata.yaml` | Path to Suricata config |

### Install and Configure Suricata

```bash
# Install
sudo apt install suricata

# Update rules (downloads Emerging Threats ruleset)
sudo suricata-update

# Verify
suricata --build-info
suricata -T -c /etc/suricata/suricata.yaml   # config test
```

---

## Timeout Behaviour

Each DPI job has an **8-second timeout**. If Suricata does not complete within this window (e.g., malformed PCAP, resource contention), the worker:
1. Kills the Suricata subprocess
2. Cleans up the temp directory
3. Returns an empty list `[]`
4. Logs a `WARNING: Suricata timeout` entry

The pipeline continues uninterrupted — a DPI timeout does not drop the alert. The alert is built from the ML result alone, same as for non-flagged flows.

---

## Graceful Absence

If Suricata is not installed, `run_dpi()` catches the `FileNotFoundError` on the first call, logs a one-time warning, and returns `[]` for all subsequent calls. The pipeline runs normally without DPI — ML-only alerts are still generated and stored.

---

## Integration Point

`dpi_engine.run_dpi(packets: bytes) -> list` is the only public function. Called from `_build_and_queue_alert()` in `services/flow_service/main_pipeline.py`:

```python
dpi_results = []
if send_to_dpi and raw_packets:
    dpi_results = dpi_engine.run_dpi(raw_packets)
```

---

## Logs

Logs written to `logs/dpi/dpi_engine.log`:

| Log Entry | Meaning |
|-----------|---------|
| `Initialized N worker threads` | Pool started at first call |
| `N alerts from Suricata for job <uuid>` | Flow processed, N signature matches |
| `Suricata timeout — job <uuid>` | Flow took > 8 s — result skipped, pipeline continues |
| `Suricata not found — DPI disabled` | Binary missing, DPI will be skipped for all flows |
| `Worker error: <exception>` | Unexpected exception in a worker thread |

---

## Dependencies

- **Suricata 6+** — must be installed and rules updated on the backend machine
- **Python stdlib only** — `subprocess`, `threading`, `tempfile`, `json`, `uuid`, `os`
