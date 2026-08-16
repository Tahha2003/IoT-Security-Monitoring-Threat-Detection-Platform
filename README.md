<div align="center">

# 🛡️ IoT Threat Detection & Security Monitoring Platform

### An On-Premises, AI-Powered Intrusion Detection System for IoT Networks

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](LICENSE)

**Final Year Project — BSc Computer Science / Cybersecurity**

*"Because in the age of AI, every business is a target — and cloud-based security is no longer enough."*

</div>

---

## ⚠️ Why This Project Exists

> **Cyber threats have changed. Your security needs to change with them.**

The rise of AI has dramatically lowered the barrier to launching sophisticated cyber attacks. Tools that once required expert knowledge can now be automated, scaled, and directed at any connected device — including the IoT sensors, cameras, and smart devices that run your business.

**The problem with today's IoT security:**

| Problem | Impact |
|---------|--------|
| Most IDS platforms are **cloud-based** | Your network traffic leaves your premises — privacy risk |
| Manual alert response | Attackers move in seconds; humans respond in minutes |
| Static, non-adaptive models | Zero-day attacks bypass signature-based detection |
| Black-box vendor solutions | No visibility into what is being detected or why |

This platform was built as a **final year university project** with one core purpose:

> **To demonstrate that a fully functional, on-premises IoT Intrusion Detection System can be built with open-source tools — and to raise awareness that every business, regardless of size, can and should deploy one.**

You own your data. You own your response. You own your security.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Hardware Setup](#-hardware-setup)
- [Network Topology](#-network-topology)
- [Pipeline Deep Dive](#-pipeline-deep-dive)
- [ML Models](#-ml-models)
- [SOAR Playbooks](#-soar-playbooks--automated-response)
- [Dashboard](#-dashboard)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Attack Testing](#-attack-testing)
- [Performance](#-performance)
- [Limitations & Future Work](#-limitations--future-work)

---

## 🔍 Overview

This platform is a **modular, real-time IoT security monitoring system** that operates entirely on-premises. It intercepts live network traffic, extracts behavioral features, scores each network flow using ensemble machine learning, and automatically responds to confirmed threats — all without sending a single packet to the cloud.

### What it does

```
Live Network Traffic
        ↓
Packet Capture (Raspberry Pi edge node)
        ↓
Deep Packet Inspection (Zeek + Scapy)
        ↓
Feature Extraction (38 behavioral features)
        ↓
ML Inference (Random Forest + Isolation Forest)
        ↓
Risk Scoring & Alert Generation
        ↓
SOAR Automated Response (4 playbooks)
        ↓
Real-Time Dashboard (React + WebSocket)
```

### Who it is for

- **Small and medium businesses** running on-premises IoT infrastructure (cameras, sensors, BYOD)
- **Security analysts** who need real-time visibility into their IoT network
- **IT administrators** who want automated first-response to network threats
- **Researchers and students** learning about network security, ML, and IDS architecture

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IoT TESTBED NETWORK                                 │
│                                                                              │
│   [ESP32/DHT22]──WiFi──[Raspberry Pi AP]──Ethernet──[Managed Switch]        │
│   [IP Camera]──WiFi────────────────────────────────────/                    │
│   [BYOD Phone]─WiFi────────────────────────────────── /                     │
│   [Kali Linux]──Ethernet──────────────────────────────                      │
│                                    │ SPAN Port Mirror                        │
│                                    ▼                                         │
│                         [Backend Machine]                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌────────────┐ ┌────────────────┐
            │  Capture    │ │   Flow     │ │   SIEM /       │
            │  Service    │ │  Service   │ │   SOAR Engine  │
            │  (Port 9000)│ │  (Pipeline)│ │                │
            └─────────────┘ └────────────┘ └────────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌────────────┐ ┌────────────────┐
            │  ML Engine  │ │ PostgreSQL │ │   API Service  │
            │  RF + ISO   │ │  (Alerts) │ │  FastAPI +     │
            │  Forest     │ │            │ │  WebSocket     │
            └─────────────┘ └────────────┘ └────────────────┘
                                                    │
                                                    ▼
                                          ┌────────────────┐
                                          │    Dashboard   │
                                          │  React + Tail  │
                                          │  wind CSS      │
                                          └────────────────┘
```

> 📁 See `docs/architecture/` for detailed architecture documentation and phase-by-phase implementation notes.

---

## ✨ Features

### 🔴 Real-Time Threat Detection
- Live packet capture from a Raspberry Pi edge node via TCP stream
- Zeek network monitoring framework extracts session-level features
- 38-feature behavioral profile built per network flow
- Sub-second latency from packet to alert

### 🤖 AI-Powered Anomaly Detection
- **Random Forest** classifier — supervised detection of known attack patterns
- **Isolation Forest** — unsupervised detection of behavioral anomalies
- Ensemble scoring combines both models into a single risk score (0.0–1.0)
- Models trained on combined IoT datasets (TON_IoT, CICIDS2017, UNSW-NB15)
- Hot-swap model reloading — retrain without pipeline restart

### 🔎 Deep Packet Inspection
- Zeek-based DPI extracts protocol-level features (HTTP, DNS, MQTT, NTP)
- Scapy fallback for flows Zeek does not parse
- Protocol anomaly detection alongside ML-based behavioral scoring
- Full session reconstruction from raw PCAP stream

### ⚡ SOAR Automated Response
- 4 pre-built playbooks triggered at configurable risk thresholds
- **Block Attacker** — UFW firewall rule for external threat sources
- **Camera Defense** — iptables rate limiting when IoT camera is targeted
- **Device Quarantine** — network isolation of compromised IoT endpoints
- **Scan Detection** — throttling of port scanning activity
- Playbooks can be enabled/disabled live from the dashboard
- Manual override buttons (Unblock / Release Quarantine) in the UI

### 📊 Interactive Dashboard
- Live alert feed with severity colour-coding (CRITICAL / HIGH / MEDIUM / LOW)
- Network topology map showing connected IoT devices and active threats
- Attack timeline chart with real-time updates via WebSocket
- Anomaly gauge and risk score visualisation
- Top attackers leaderboard
- System health panel (CPU, memory, pipeline status)
- One-click SOAR controls with audit trail

### 🗄️ SIEM Storage & Analytics
- All alerts persisted to PostgreSQL with full metadata
- Risk score, attack classification, protocol, ports, timestamps
- REST API for alert queries, statistics, and device status
- Alert export and historical trend analysis

### 🔄 Continuous Learning
- Feedback mechanism for analyst-confirmed alerts
- Dataset pipeline for retraining with new labelled data
- Retrain script that hot-swaps models without downtime

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Packet Capture** | tcpdump + socat | Raw PCAP stream from Raspberry Pi to backend |
| **DPI Engine** | Zeek 6.x | Session extraction and protocol analysis |
| **Feature Builder** | Python / Scapy | 38-feature flow profiling |
| **ML — Supervised** | scikit-learn Random Forest | Binary attack/normal classification |
| **ML — Unsupervised** | scikit-learn Isolation Forest | Novelty/anomaly detection |
| **Preprocessing** | Custom FeaturePreprocessor | Categorical encoding, normalisation |
| **Pipeline** | Python threading | 7-thread concurrent processing pipeline |
| **API** | FastAPI + Uvicorn | REST endpoints and WebSocket broadcast |
| **Database** | PostgreSQL 15 | Alert storage and SIEM persistence |
| **SOAR** | Python + UFW/iptables | Automated playbook execution |
| **Dashboard** | React 18 + Recharts | Real-time UI with live data |
| **Styling** | Tailwind CSS | Dark-mode security dashboard aesthetic |
| **Monitoring** | Prometheus + custom metrics | Pipeline health and throughput |
| **Edge Node** | Raspberry Pi 4 | Capture agent and IoT AP |

---

## 🔌 Hardware Setup

### Required Components

| Component | Model | Role |
|-----------|-------|------|
| Raspberry Pi 4 | 4GB RAM | Edge capture node + IoT AP |
| Managed Switch | Cisco/TP-Link (SPAN support) | Traffic mirroring to backend |
| Backend Machine | i5/i7, 8GB+ RAM | Detection engine + dashboard |
| ESP32 + DHT22 | Any ESP32 devboard | Real IoT sensor endpoint |
| IP Camera | Any RTSP camera | Monitored IoT device |
| Android Phone | Any | BYOD device simulation |
| Kali Linux VM/Machine | *(optional)* | Controlled attack simulation |

### Minimum Backend Requirements

```
CPU:   4 cores (6+ recommended for real-time ML)
RAM:   8 GB (16 GB recommended)
OS:    Ubuntu 22.04 LTS
Disk:  20 GB free
```

---

## 🌐 Network Topology

```
Internet
    │
    └── Router (192.168.10.1)
            │ WiFi
            ├── IP Camera   (192.168.10.101) ── Monitored IoT Device
            └── BYOD Phone  (192.168.10.102) ── Monitored IoT Device
                                │
                        Managed Switch
                        ├── GI01 ── Raspberry Pi  (192.168.10.150) ── SPAN Destination
                        ├── GI03 ── Backend PC     (192.168.10.120) ── SOURCE (mirrored)
                        ├── GI05 ── Router         (192.168.10.1)   ── SOURCE (mirrored)
                        └── GI11 ── Kali Linux     (192.168.10.130) ── SOURCE (attack node)

Raspberry Pi WiFi (wlan0: 192.168.50.1) ── IOT-LAB AP
    └── ESP32 (DHT22 sensor) ── IoT telemetry endpoint
    └── Pi Camera ── MJPEG video stream
```

> All traffic from SOURCE ports is mirrored to the Raspberry Pi (SPAN destination),
> which streams the raw PCAP to the backend over TCP port 9000.

---

## ⚙️ Pipeline Deep Dive

The main pipeline runs as **7 concurrent threads**, each with a dedicated role:

```
Thread 1:  Packet Listener     — TCP server on :9000, receives PCAP from Pi
Thread 2:  Zeek Feeder         — Feeds captured PCAP to Zeek for DPI
Thread 3:  Zeek Parser         — Reads conn.log, builds feature dicts, queues flows
Thread 4:  ML Inference Worker — Dequeues flows, runs RF + ISO Forest, scores risk
Thread 5:  DPI Worker          — Parallel deep packet inspection with Scapy
Thread 6:  Metrics Worker      — Prometheus metrics collection
Thread 7:  SOAR Engine         — Monitors alert stream, triggers playbooks
```

### Flow of a Single Network Connection

```
1. Pi captures packet from SPAN port
2. Pi streams raw PCAP bytes over TCP to backend:9000
3. Backend writes to /tmp/live.pcap
4. Zeek processes pcap → extracts session in conn.log
5. Zeek parser reads conn.log → builds 38-feature dict
6. Features pushed to ML queue
7. InferenceEngine runs RF.predict() + ISO.predict()
8. Risk score computed: score = 0.6*rf_proba + 0.4*(iso_score)
9. Alert created if risk > threshold
10. Alert written to PostgreSQL
11. Alert broadcast via WebSocket to dashboard
12. SOAR engine evaluates: if risk >= 0.80 AND 3+ events in 60s → playbook
```

### The 38 Features

The feature extractor builds a behavioral profile per flow including:

| Category | Features |
|----------|----------|
| **Volume** | bytes sent/received, packets sent/received, avg packet size |
| **Timing** | duration, inter-arrival time, connection rate |
| **Protocol** | protocol type (TCP/UDP/ICMP), service, connection state |
| **Ports** | source port, destination port, port range entropy |
| **Ratios** | byte ratio, packet ratio, SYN/ACK ratio |
| **History** | connection history flags (RSTRH, SF, REJ, etc.) |

---

## 🧠 ML Models

### Random Forest Classifier
- **Type:** Supervised binary classification (0 = normal, 1 = attack)
- **Training data:** Balanced dataset — 14,816 samples (50/50 normal/attack)
- **Source datasets:** TON_IoT + CICIDS2017 + UNSW-NB15 + local testbed captures
- **Performance:** ~87% accuracy, 0.89 F1-score on attack class
- **Output:** Binary prediction + continuous probability (used for risk scoring)

### Isolation Forest
- **Type:** Unsupervised anomaly detection
- **Purpose:** Catches novel attacks that the RF has not seen before
- **Contamination:** 0.15 (calibrated to testbed normal traffic ratio)
- **Output:** +1 (normal) or -1 (anomaly)

### Ensemble Risk Score

```
risk_score = (0.6 × rf_probability) + (0.4 × iso_anomaly_score)

Severity mapping:
  CRITICAL  ≥ 0.80  → SOAR trigger eligible
  HIGH      ≥ 0.60  → Alert + toast notification
  MEDIUM    ≥ 0.35  → Alert logged
  LOW       < 0.35  → Log only
```

### Retraining

```bash
# Prepare and balance dataset
python3 -m ml.training.dataset_preparer

# Train both models
python3 -m ml.training.model_training

# Models hot-swap on next inference cycle — no restart needed
```

---

## 🚨 SOAR Playbooks — Automated Response

The SOAR engine monitors the alert stream and triggers playbooks when:
- Risk score ≥ 0.80
- 3+ events from the same source within 60 seconds
- No cooldown active for that source (60-second cooldown per IP)

### Playbook 1 — Block Attacker
```
Trigger:  CRITICAL alert from external IP (not IoT device)
Action:   sudo ufw insert 1 deny from <ip> to any
Result:   All traffic from attacker dropped at OS firewall level
Log:      logs/siem/soar_engine.log
Revert:   Dashboard "UNBLOCK" button → ufw delete rule
```

### Playbook 2 — Camera Defense
```
Trigger:  Any attack targeting the IP camera (192.168.10.101)
Action:   iptables rate-limit + bandwidth throttle from attacker to camera
Result:   Camera remains operational; attacker traffic throttled
Log:      logs/soar/camera_defense.log
```

### Playbook 3 — Device Quarantine
```
Trigger:  CRITICAL alert sourced FROM an IoT device (compromised device)
Action:   iptables FORWARD DROP for device's IP (network isolation)
Result:   Compromised device cannot communicate with rest of network
Log:      logs/soar/quarantine.log
Revert:   Dashboard "RELEASE" button → iptables rule removal
```

### Playbook 4 — Scan Detection
```
Trigger:  20+ unique destination ports accessed within 30 seconds
Action:   iptables rate-limit + throttle
Result:   Scanning activity slowed; analyst alerted
Log:      logs/soar/scan_detection.log
```

All playbooks respect a **runtime enable/disable flag** — toggleable from the dashboard without restarting the pipeline.

---

## 📊 Dashboard

The React dashboard provides a full operational picture of your IoT network security posture in real time.

### Panels

| Panel | Description |
|-------|-------------|
| **Stats Bar** | Total alerts, active threats, blocked IPs, model accuracy |
| **Live Alert Feed** | Scrolling real-time alerts with severity, IP, attack type, risk score |
| **Network Topology** | Visual graph of connected IoT devices and active threat links |
| **Attack Timeline** | Time-series chart of alert volume by severity |
| **Anomaly Gauge** | Current network anomaly level (0–100%) |
| **Severity Pie** | Distribution of CRITICAL/HIGH/MEDIUM/LOW alerts |
| **Top Attackers** | Ranked list of most active threat sources |
| **Devices Panel** | All known IoT devices with status (Normal / Suspicious / Quarantined) |
| **System Health** | CPU, memory, pipeline thread status, DB connection |
| **SOAR Panel** | Playbook status, recent actions, manual overrides |

### Real-Time Updates

The dashboard connects to the backend via **WebSocket** (`ws://localhost:8000/ws/alerts`). Every alert generated by the pipeline is broadcast instantly — no polling, no page refresh.

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10+
python3 --version

# Node.js 16+
node --version && npm --version

# Zeek
/opt/zeek/bin/zeek --version

# PostgreSQL
sudo systemctl status postgresql
```

### 1. Clone and Set Up

```bash
git clone https://github.com/your-username/iot-threat-detection.git
cd iot-threat-detection

# Create virtual environment
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Install Python dependencies
pip install -r requirements.txt

# Install dashboard dependencies
cd dashboard && npm install && cd ..
```

### 2. Set Up Database

```bash
sudo -u postgres psql -c "CREATE DATABASE fyp_security;"

PGPASSWORD=postgres psql -U postgres -d fyp_security \
    -f services/siem-service/db/schema.sql
```

### 3. Train ML Models

```bash
python3 -m ml.training.dataset_preparer
python3 -m ml.training.model_training

# Verify models
ls ml/training/models/
# rf_model.pkl  iso_model.pkl  preprocessor.pkl
```

### 4. Start the Backend Pipeline

```bash
bash infrastructure/scripts/start_pipeline.sh

# Verify
curl http://localhost:8000/health
# {"status":"ok"}
```

### 5. Start the Dashboard

```bash
cd dashboard
npm start
# Open http://localhost:3000
```

### 6. Connect the Pi Capture Agent

On the Raspberry Pi:
```bash
bash ~/edge/capture/capture.sh
```

The dashboard status indicator will switch from **OFFLINE** to **LIVE**.

---

## 📁 Project Structure

```
iot-threat-detection/
│
├── dashboard/                    # React frontend
│   └── src/
│       ├── components/           # AlertFeed, NetworkTopology, SoarPanel, etc.
│       ├── hooks/                # useWebSocket real-time hook
│       └── services/             # API client
│
├── services/
│   ├── api-service/              # FastAPI REST + WebSocket server
│   ├── capture-service/          # MQTT + raw sensor ingest
│   ├── dpi-service/              # Scapy/Zeek DPI engine
│   ├── flow_service/             # Main pipeline (7-thread orchestrator)
│   │   ├── core/                 # inference_engine, result_buffer, queues
│   │   ├── zeek_parser.py        # Zeek conn.log → feature dict
│   │   ├── packet_listener.py    # TCP PCAP receiver
│   │   ├── main_pipeline.py      # Thread orchestrator
│   │   └── state.py              # Shared pipeline state
│   ├── siem-service/             # Alert persistence (PostgreSQL writer)
│   └── soar-service/             # SOAR engine + 4 playbooks
│
├── ml/
│   ├── training/                 # Model training scripts
│   │   ├── model_training.py     # RF + ISO Forest training
│   │   ├── dataset_preparer.py   # Dataset balancing and preprocessing
│   │   └── models/               # Saved .pkl model files
│   ├── features/                 # Feature builder + preprocessor
│   ├── datasets/                 # Training data (CSV)
│   └── configs/                  # Feature contract definition
│
├── infrastructure/
│   ├── scripts/                  # start/stop/reset pipeline scripts
│   └── monitoring/               # Prometheus config + metrics.py
│
├── shared/
│   ├── config/                   # system_config.yaml, thresholds.json
│   ├── schemas/                  # JSON schemas (alert, flow, ML output)
│   ├── contracts/                # Phase data format specs
│   └── utils/                    # config_loader, logger, helpers
│
├── logs/
│   ├── pipeline/                 # Per-thread log files
│   ├── dashboard/                # API + Uvicorn logs
│   ├── siem/                     # SOAR engine + batch writer logs
│   └── soar/                     # Per-playbook action logs
│
├── docs/
│   ├── architecture/             # Network topology, edge notes
│   ├── phase2/                   # Capture pipeline design docs
│   └── RUNBOOK.md                # Complete operations guide
│
├── tests/                        # Test suites (unit, integration)
├── requirements.txt
└── README.md
```

---

## 🗡️ Attack Testing

The platform was validated against controlled IoT attack scenarios within the isolated testbed.

### Simulated Attack Types

| Attack | Method | Expected Response |
|--------|--------|-------------------|
| **ICMP Flood (DoS)** | `hping3 --flood` | PB1: Block Attacker (UFW) |
| **SYN Flood** | `hping3 -S --flood` | PB1: Block + PB3: Quarantine BYOD |
| **Port Scan** | `nmap -sS` | PB4: Scan Detection + throttle |
| **Camera Flood** | Burst traffic to 10.101 | PB2: Camera Defense |
| **Botnet Simulation** | Multi-vector from multiple IPs | Multi-playbook cascade |
| **ARP Spoofing** | `arpspoof` | High-risk alert + analyst notification |

### Running an Attack Test

```bash
# Reset firewall to clean state first
bash infrastructure/scripts/reset_firewall.sh

# Run ICMP flood (Kali machine)
sudo hping3 -1 --flood 192.168.10.101

# Watch SOAR trigger (backend)
tail -f logs/siem/soar_engine.log

# Verify block applied after 60 seconds
sudo ufw status numbered | grep DENY
```

---

## 📈 Performance

Results measured on the on-premises testbed with live traffic.

| Metric | Value |
|--------|-------|
| Alert latency (packet → dashboard) | < 3 seconds |
| ML inference time per flow | ~12 ms |
| Random Forest accuracy | 87% |
| Attack class F1-score | 0.89 |
| Isolation Forest anomaly detection | ✅ Novel attack detection |
| SOAR response time (trigger → block) | < 5 seconds |
| Dashboard WebSocket latency | < 100 ms |
| Pipeline throughput | ~500 flows/minute |
| False positive rate (tuned threshold) | ~8% |

---

## ⚠️ Limitations & Future Work

### Current Limitations

- **Testbed scale only** — validated on a 6-device lab, not a full enterprise network
- **Single backend node** — no distributed processing or horizontal scaling
- **IPv4 only** — IPv6 traffic is not yet profiled or classified
- **Supervised models require labelled data** — the model reflects the training datasets' attack distributions

### Planned Extensions

- [ ] **Federated Learning** — distributed model training across multiple edge nodes
- [ ] **MQTT/CoAP DPI** — deeper IoT protocol analysis beyond TCP/UDP sessions
- [ ] **CNN-LSTM temporal model** — sequence-based attack detection
- [ ] **Grafana integration** — pre-built security dashboards over Prometheus
- [ ] **Docker Compose deployment** — one-command setup for all services
- [ ] **CVE correlation** — linking detected patterns to known vulnerability databases
- [ ] **Email/SMS alerting** — out-of-band notification for critical events
- [ ] **Multi-site support** — remote sensor aggregation

---

## 📖 Documentation

| Document | Location | Contents |
|----------|----------|----------|
| Operations Runbook | `docs/RUNBOOK.md` | Full setup, startup, testing, troubleshooting |
| Network Topology | `docs/architecture/phase1_topology.md` | Hardware layout and SPAN config |
| Edge Architecture | `docs/architecture/edge_architecture_note.md` | Raspberry Pi role and traffic path |
| Capture Pipeline | `docs/phase2/phase2_capture_pipeline.md` | Pi → backend PCAP stream design |
| BPF Contract | `docs/phase2/phase2_bpf_contract.md` | Kernel-level packet filter rules |
| Device IP Map | `docs/architecture/device_ip_map.md` | Full device registry |

---

## 🔑 Key Configuration

### Thresholds (`shared/config/thresholds.json`)
```json
{
  "risk_critical": 0.80,
  "risk_high":     0.60,
  "risk_medium":   0.35,
  "soar_trigger":  0.80,
  "soar_window":   60,
  "soar_min_events": 3,
  "soar_cooldown": 60
}
```

### Key Ports

| Port | Service |
|------|---------|
| 3000 | React Dashboard |
| 8000 | FastAPI (REST + WebSocket) |
| 9000 | Pi PCAP TCP stream receiver |
| 9091 | Prometheus metrics |
| 5432 | PostgreSQL |

### Severity → Action Mapping

| Severity | Risk Score | Auto Action |
|----------|-----------|-------------|
| CRITICAL | ≥ 0.80 | SOAR playbook eligible |
| HIGH | ≥ 0.60 | Alert + toast notification |
| MEDIUM | ≥ 0.35 | Alert logged + dashboard |
| LOW | < 0.35 | Log only |

---

## 🧑‍💻 Contributing

This project is an academic final year project and is open for learning and extension.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add: your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the **Apache License 2.0**. See `LICENSE` for the full text.

```
Copyright 2026 IoT Threat Detection & Security Monitoring Platform

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

Key permissions under Apache 2.0:
- ✅ Commercial use
- ✅ Modification and distribution
- ✅ Patent use
- ✅ Private use
- ⚠️ Must include original license and copyright notice
- ⚠️ State changes made to the code

---

## 🙏 Acknowledgements

- **Zeek Network Security Monitor** — zeek.org
- **scikit-learn** — for the ML framework
- **FastAPI** — for the async backend framework
- **React + Recharts** — for the dashboard
- **TON_IoT, CICIDS2017, UNSW-NB15** — public IoT/network security datasets used for model training

---

<div align="center">

**Built as a Final Year Project to demonstrate that on-premises, AI-powered IoT security is achievable by anyone.**

*In the age of AI, the question is not whether your business will be targeted — it is whether you will see it coming.*

</div>
