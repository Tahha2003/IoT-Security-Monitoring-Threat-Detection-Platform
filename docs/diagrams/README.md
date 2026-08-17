# System Diagrams

This folder contains 4 architectural diagrams for the IoT Device Security Monitoring and Threat Detection Platform. Each diagram covers a different level of detail — from the high-level physical network layout down to the exact per-thread data flow inside the backend pipeline.

---

## 1. IoT Network Architecture (High-Level Overview)

**File:** `Project Diagram.jpeg`

![IoT Network Architecture](Project%20Diagram.jpeg)

### Description

This is the top-level overview diagram showing all physical components and their roles within the testbed. It is the simplest view — intended as a quick reference for understanding who is connected to what and why.

### What it shows

| Component | Role |
|-----------|------|
| **Raspberry Pi** | Data collection and local processing — SPAN destination on the managed switch |
| **Backend PC** | Central server — runs the full detection pipeline, ML engine, API, and dashboard |
| **Managed Switch** | Connects all wired devices; mirrors traffic to Raspberry Pi via SPAN |
| **WiFi Router** | Provides wireless access for IoT devices |
| **WiFi Camera** | Monitored IoT device — captures and streams video traffic |
| **BYOD Mobile** | Monitored IoT device — accesses the IoT network wirelessly |
| **Kali Linux (Testbed Operator)** | Monitoring and controlled attack simulation |
| **Analyst** | Accesses the dashboard to monitor alerts and review detections |
| **Admin** | Manages the system — pipeline control, SOAR configuration, user management |

### Connection types

- **Solid blue line** — Wired connection (Ethernet)
- **Dashed blue line** — Wireless connection (WiFi)

### Key point

The Raspberry Pi sits on the managed switch as the SPAN destination port. All traffic entering and leaving the switch source ports (Backend PC, WiFi Router uplink) is mirrored to the Pi, which then streams that raw PCAP data to the Backend PC over TCP for processing. No traffic analysis happens on the Pi itself.

---

## 2. Detailed Network Architecture (IP-Level)

**File:** `IoT Network Architecture.png`

![Detailed Network Architecture](IoT%20Network%20Architecture.png)

### Description

This diagram extends the high-level overview with exact IP addresses, subnet information, switch port labels, SPAN configuration details, and the out-of-band management network. It is the definitive reference for network configuration.

### Subnets

| Subnet | Range | Purpose |
|--------|-------|---------|
| Wireless IoT subnet | `192.168.50.0/24` | WiFi Router + IoT devices (Camera, BYOD Mobile) |
| Wired testbed subnet | `192.168.2.0/24` | Managed switch segment (Pi, Backend PC, Kali) |
| Out-of-band management | `192.168.50.0/24` | IOT-LAB WiFi — SSH access to Pi, BACKEND_IP route |

### Device IP Map

| Device | IP Address | Switch Port | Role |
|--------|-----------|-------------|------|
| WiFi Camera | 192.168.50.10 | — (wireless) | IoT Device |
| BYOD Mobile | 192.168.50.40 | — (wireless) | IoT Device |
| Raspberry Pi (eth0) | 192.168.2.106 | Port A | **SPAN destination** — receives mirrored traffic |
| Backend PC (eth) | 192.168.2.101 | Port B | Traffic source — mirrored to Port A |
| WiFi Router | uplink | Port C | Traffic source — mirrored to Port A |
| Kali Linux | 192.168.2.x | Port D | Testbed operator / attack simulation |
| Backend PC (WiFi) | 192.168.50.21 | — | IOT-LAB WiFi interface (`wlxe009bf6913de`) |
| Raspberry Pi (wlan0) | 192.168.50.1 | — | IOT-LAB WiFi — SSH access point |

### SPAN Configuration

```
Source Ports:      B (Backend PC), C (WiFi Router uplink)
Destination Port:  A (Raspberry Pi)
Effect:            All traffic entering/leaving ports B and C
                   is copied and sent to port A
```

### Out-of-Band Management

The IOT-LAB WiFi subnet (`192.168.50.0/24`) is used exclusively for management — SSH into the Pi and the route from the Backend PC to the Pi. The Pi's capture script (`tcpdump | socat`) sends raw PCAP to `192.168.50.21` (the backend's IOT-LAB WiFi address), not to `192.168.2.101` (the wired address), because the Pi reaches the backend via the IOT-LAB subnet.

### Connection legend

| Line type | Meaning |
|-----------|---------|
| Dashed blue | Wireless connection |
| Solid black | Wired connection |
| Red arrow | SPAN mirror traffic path |
| Dashed purple | Out-of-band management (IOT-LAB WiFi) |

---

## 3. System Architecture Diagram (Pipeline Overview)

**File:** `System Architecture Diagram.png`

![System Architecture Diagram](System%20Architecture%20Diagram.png)

### Description

This diagram shows the complete system from IoT device to dashboard — all major components and how they connect. It sits between the network diagram (physical layer) and the data flow diagram (code-level detail). It is the best diagram for understanding the overall processing pipeline at a glance.

### Flow summary

```
IoT Devices (WiFi Camera, BYOD Mobile)
        ↓ Wireless → WiFi Router → Managed Switch
Raspberry Pi (SPAN destination — eth0)
        ↓ tcpdump | socat → TCP:9000
Backend PC — 7-Thread Detection Pipeline
        ↓
T1 Packet Listener   →  QUEUE_1 (raw PCAP bytes)
T2 Zeek Feeder       →  writes /tmp/live.pcap, runs Zeek
T3 Zeek Parser       →  ML_QUEUE (15-feature flow dicts)
T4 ML Inference      →  RESULT_QUEUE (RF + ISO scores)
T5 DPI Worker        →  Suricata — inspects flagged flows only
        ↓
Risk Scoring         →  Alert Dict (IP, Type, Risk, Severity)
        ↓
T6 SIEM Batch Writer →  PostgreSQL (every 2 seconds)
SOAR Engine          →  UFW / iptables (4 playbooks)
FastAPI /internal/broadcast → WebSocket → React Dashboard
T7 Metrics Worker    →  Prometheus :9091
```

### Key components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| T1 Packet Listener | Python socket | Receives raw PCAP stream from Pi on TCP:9000 |
| T2 Zeek Feeder | Zeek 6.x | Writes PCAP to file, spawns `zeek -r` per batch |
| T3 Zeek Parser | Python | Parses `conn.log`, extracts 15 features per flow |
| T4 ML Inference | scikit-learn | Random Forest + Isolation Forest ensemble |
| T5 DPI Worker | Suricata 7.x | Signature matching on ML-flagged flows only |
| Risk Scoring | Python | `0.6×RF + 0.4×ISO` → severity label |
| T6 SIEM Batch Writer | psycopg2 | Bulk inserts to PostgreSQL every 2 seconds |
| SOAR Engine | Python + UFW/iptables | 4 automated playbooks |
| FastAPI | Uvicorn :8000 | REST API + WebSocket broadcaster |
| React Dashboard | React 18 + Recharts | Real-time security operations UI |
| T7 Metrics Worker | prometheus-client | Queue depth and inference latency metrics |

### SOAR Playbooks (4)

| Playbook | Trigger | Action |
|----------|---------|--------|
| Block Attacker | CRITICAL from external IP | `ufw insert 1 deny from <ip>` |
| Quarantine Device | CRITICAL from IoT device (compromised) | `iptables FORWARD DROP` |
| Protect Camera | Attack targeting camera IP | `iptables` rate-limit |
| Throttle Scans | Port scan detected | `iptables` connection throttle |

---

## 4. System Data Flow Diagram (Code-Level Detail)

**File:** `System Data Flow Architecture Diagram.png`

![System Data Flow Architecture](System%20Data%20Flow%20Architecture%20Diagram.png)

### Description

This is the most detailed diagram in the set. It maps the exact code-level data flow through every thread, every queue, and every function call in the backend pipeline. It directly corresponds to the actual Python source code in `services/flow_service/main_pipeline.py`. Use this diagram when debugging the pipeline or understanding how a specific alert is produced.

### Thread-by-thread breakdown

#### T1 — `packet_listener.py`
- Listens on `TCP:9000`
- Receives raw PCAP bytes from the Raspberry Pi (`tcpdump | socat`)
- Pushes bytes into `QUEUE_1` (bounded `deque`, maxlen=50,000)

#### T2 — `zeek_feeder.py`
- Reads from `QUEUE_1`
- Writes PCAP batches to `/tmp/live.pcap`
- Spawns short-lived `zeek -r /tmp/live.pcap` process
- Zeek produces `conn.log` in `services/flow_service/logs/zeek/current/`

#### T3 — `zeek_parser.py`
- Parses `conn.log` using inode-aware file tracking
- Extracts **15 features** per flow (feature contract v3.0.0)
- Pushes 15-feature dicts into `ML_QUEUE` (bounded `deque`, maxlen=50,000)

#### T4 — `ml_inference_worker`
- Dequeues flows from `ML_QUEUE`
- Runs `RandomForest.predict_proba()` → `rf_proba`, `rf_label`
- Runs `IsolationForest.predict()` → `iso_pred` (+1 normal / -1 anomaly)
- Sets `send_to_dpi = (rf_proba > 0.30) OR (iso_pred == -1)`
- Pushes result into `RESULT_QUEUE` (bounded `deque`, maxlen=50,000)

#### T5 — `dpi_worker`
- Dequeues from `RESULT_QUEUE`
- If `send_to_dpi = False` → builds alert from ML result only
- If `send_to_dpi = True` → runs Suricata on raw packets → parses `eve.json` → merges DPI signatures with ML result

#### `_build_and_queue_alert()`
Called from T5 — final alert assembly:

```
risk_score = 0.6 × rf_proba + 0.4 × iso_score

Alert Dict fields:
  timestamp, src_ip, dst_ip, protocol, ports
  attack_type, severity, risk_score
  rf_proba, iso_score, dpi_info (if any)
  playbook_action (if SOAR triggered)

Actions:
  queue_alert()              → SIEM deque (non-blocking)
  soar_evaluate()            → playbook routing
  POST /internal/broadcast   → WebSocket → Dashboard
```

#### T6 — `batch_loop()` (SIEM Batch Writer)
- Flushes SIEM `deque` to PostgreSQL every **2 seconds**
- Uses `executemany` for bulk insert performance
- On DB failure: re-queues batch — no data loss

#### T7 — `metrics_worker()`
- Collects pipeline metrics (queue depth, inference latency)
- Exposes to Prometheus on `:9091`

### Queue reference

| Queue | Type | maxlen | Connects |
|-------|------|--------|---------|
| `QUEUE_1` | `deque` | 50,000 | T1 → T2 |
| `ML_QUEUE` | `deque` | 50,000 | T3 → T4 |
| `RESULT_QUEUE` | `deque` | 50,000 | T4 → T5 |
| SIEM deque | `deque` | 10,000 | T5 → T6 |

### Adaptive backpressure

When `ML_QUEUE` depth grows, T4 automatically samples fewer flows:

| Queue Depth | Mode | Behaviour |
|-------------|------|-----------|
| < 300 | Full | Every flow processed |
| 300 – 800 | 50% | Every 2nd flow |
| 800 – 2000 | 33% | Every 3rd flow |
| > 2000 | Sparse | Every 7th flow |

---

## Diagram Comparison

| Diagram | Level | Best used for |
|---------|-------|---------------|
| `Project Diagram.jpeg` | Physical overview | Quick reference — who is connected to what |
| `IoT Network Architecture.png` | IP-level network | Network configuration, IP addresses, SPAN setup |
| `System Architecture Diagram.png` | Component pipeline | Understanding all major components and their connections |
| `System Data Flow Architecture Diagram.png` | Code-level data flow | Debugging pipeline, understanding exact thread/queue/function flow |
