# System Diagrams
# IoT Device Security Monitoring and Threat Detection Platform

This folder contains all UML and architectural diagrams for the platform, organized by diagram type. Each diagram is shown with a concise description.

---

## Network Architecture Diagrams

---

### IoT Network Architecture (High-Level)

![IoT Network Architecture Overview](Project%20Diagram.jpeg)

*Figure: IoT Network Architecture — High-Level Overview*

Shows all physical components and their roles. Raspberry Pi sits on the managed switch as the SPAN destination, receiving mirrored traffic from all source ports. Backend PC runs the full detection pipeline. WiFi Camera and BYOD Mobile connect wirelessly via the router. Kali Linux acts as the testbed operator for attack simulation. Solid lines = wired connections; dashed lines = wireless connections.

---

### IoT Network Architecture (IP-Level Detail)

![IoT Network Architecture Detailed](IoT%20Network%20Architecture.png)

*Figure: IoT Network Architecture — Detailed IP Layout*

Extends the high-level view with exact IP addresses, switch port labels, SPAN configuration, and subnet information. WiFi Camera (192.168.50.10) and BYOD Mobile (192.168.50.40) on the wireless subnet; Raspberry Pi (192.168.2.106) on the wired subnet as SPAN destination; Backend PC (192.168.2.101) as the central detection engine. The IOT-LAB WiFi interface (192.168.50.21) on the backend is used as the BACKEND_IP for the Pi capture script.

---

## System & Architecture Diagrams

---

### System Architecture Diagram

![System Architecture Diagram](System%20Architecture%20Diagram.png)

*Figure: System Architecture Diagram — Pipeline Overview*

Shows the complete system from IoT device to dashboard across all major components. Traffic flows from devices through the WiFi Router and Switch to the Raspberry Pi SPAN port, then streams via TCP:9000 to the 7-thread backend pipeline (T1 Packet Listener → T2 Zeek Feeder → T3 Zeek Parser → T4 ML Inference → T5 DPI Worker → T6 SIEM Batch Writer → T7 Metrics). Alerts route to SOAR (UFW/iptables), PostgreSQL, and the React Dashboard via FastAPI WebSocket.

---

### System Diagram v2 — C4 Context Level

![System Diagram v2](System%20Diagram%20v2.png)

*Figure: System Context Diagram (C4 Model — Context Level)*

The IoT IDS Platform appears as the central system containing its six internal components: Detection Pipeline (7 threads), ML Engine (RF + Isolation Forest), SOAR Engine (4 playbooks), SIEM Database (PostgreSQL), REST API + WebSocket (FastAPI :8000), React Dashboard (:3000), and Prometheus Metrics (:9091). Three human actors surround it: Security Analyst (receives real-time alerts, submits TP/FP verdicts), Administrator (manages pipeline and SOAR config), and Testbed Operator (injects SYN flood/port scan/ICMP flood attacks). External systems include the Raspberry Pi (TCP:9000 raw PCAP stream), Network Switch (SPAN mirror source), UFW/iptables (automated response target), Zeek (pcap-replay subprocess), and Suricata (selective DPI subprocess).

---

### System Data Flow Architecture Diagram

![System Data Flow Architecture](System%20Data%20Flow%20Architecture%20Diagram.png)

*Figure: System Data Flow Architecture — Code-Level Thread and Queue Map*

The most detailed diagram — maps exact code-level data flow through all 7 threads and 4 queues. T1 receives raw PCAP bytes via TCP:9000 → QUEUE_1. T2 drains QUEUE_1 and spawns `zeek -r` → conn.log. T3 parses conn.log (inode-aware) → ML_QUEUE (15-feature dicts). T4 runs RF + ISO Forest → RESULT_QUEUE. T5 runs Suricata on flagged flows and builds alert dict. T6 flushes SIEM deque → PostgreSQL every 2s. T7 updates Prometheus metrics every 1s. Adaptive backpressure sampling kicks in when ML_QUEUE exceeds 300/800/2000 entries.

---

## Use-Case Diagrams

---

### Use-Case — Testbed Operator

![Use-Case Testbed Operator](Use-Case%20-%20Testbed%20Operator.jpg)

*Figure 1: Use-Case Diagram — Testbed Operator*

The Testbed Operator (Kali Linux) configures SPAN on the managed switch and executes four controlled attack scenarios: SYN flood (`hping3 -S --flood`), ICMP flood (`hping3 -1 --flood`), port scan (`nmap -sS`), and camera burst flood. The `<<include>>` arrows from port scan, ICMP flood, and SYN flood to "Start Packet Capture on Raspberry Pi" indicate that active capture is a prerequisite for any attack to be detected. "Verify Firewall Rules" extends the attack use cases as an optional post-attack validation step to confirm SOAR has inserted UFW/iptables rules.

---

### Use-Case — IoT Device

![Use-Case IoT Device](Use-Case%20-%20IoT%20Device.jpg)

*Figure 2: Use-Case Diagram — IoT Device (WiFi Camera / BYOD Mobile)*

IoT devices interact with the monitoring system passively through traffic only — all monitoring occurs via SPAN, so devices are unaware of being analyzed. Under normal conditions devices generate RTSP/HTTP/DNS traffic and appear in the Devices Panel with NORMAL status. When targeted by a flood, "Trigger Alert" extends to "Appear in Devices Panel" with SUSPICIOUS status. When acting as a compromised attack source, "Trigger Quarantine" includes "Get Quarantined" (iptables FORWARD DROP applied). "Get Released from Quarantine" extends quarantine via the dashboard RELEASE button calling `POST /api/soar/unblock/{ip}`.

---

### Use-Case — Security Analyst

![Use-Case Security Analyst](Use-Case%20-%20Security%20Analyst.jpg)

*Figure 3: Use-Case Diagram — Security Analyst*

Use cases are organized into three functional groups visible in the diagram. **Alert Analysis** group: View Live Alert Feed, View Full Alert History (with filters), Submit TP Verdict, Submit FP Verdict, and Filter Alerts by Severity/Attack Type/Source IP — all three verdict/filter use cases include "View Full Alert History" as a base. **Monitoring** group: View Network Topology Map, View Attack Timeline Chart, View Anomaly Gauge, View Top Attackers Leaderboard, View Device Status Panel. **Incident Response** group: Manually Unblock IP Address, Manually Release Quarantined Device (both extend to "View SOAR Playbook Execution Log" via `<<extend>>`).

---

### Use-Case — Administrator / System Engineer

![Use-Case Administrator](Use-Case%20-%20Administrator_System%20Engineer.jpg)

*Figure 4: Use-Case Diagram — Administrator / System Engineer*

The Administrator manages four functional areas. **Pipeline lifecycle**: Start Detection Pipeline (includes "Select Network Interface (NIC Picker)"), Stop Detection Pipeline. **SOAR management**: Enable SOAR Playbook (extends to "View System Health"), Disable SOAR Playbook. **Configuration**: Configure Device IPs (`system_config.yaml`), Set Up Sudo Rules (`setup_sudo.sh`), Trigger ML Model Retraining (extends to "View System Logs"). **Maintenance**: Reset Firewall Rules and Clear Alert Database both extend to "Stop Detection Pipeline," reflecting that these operations are typically performed alongside a pipeline shutdown.

---

## Class Diagrams

---

### Class Diagram — Testbed Operator

![Class Diagram Testbed Operator](Class%20Diagram%20-%20Testbed%20Operator.png)

*Figure 5: Class Diagram — Testbed Operator Subsystem*

Four classes model the testbed operator subsystem. `TestbedOperator` (attributes: operatorId, machine="Kali Linux", ipAddress; methods: configureSPAN, startCapture, stopCapture, launchAttack) sits at the center and controls `AttackSimulator` (attack type, target IP, methods: executeSYNFlood, executeICMPFlood, executePortScan, executeCameraFlood), configures `NetworkSwitch` (model="Cisco Catalyst", spanEnabled, sourcePort, destinationPort; methods: configureSPAN, mirrorTraffic), and manages `CaptureAgent` (interface="eth0", backendIP, backendPort=9000, bpfFilter; methods: startCapture, stopCapture, streamPCAP, reconnect). AttackSimulator injects traffic via NetworkSwitch (0..*); CaptureAgent receives mirrored traffic from NetworkSwitch.

---

### Class Diagram — IoT Device

![Class Diagram IoT Device](Class%20Diagram%20-%20IoT%20Device.png)

*Figure 6: Class Diagram — IoT Device Subsystem*

Abstract `IoTDevice` class (deviceId, ipAddress, macAddress, status: Status, deviceType) with `Status` enumeration (NORMAL, SUSPICIOUS, QUARANTINED). `WiFiCamera` subclass adds streamURL, resolution="1080p", protocol="RTSP" and traffic generation methods. `BYODMobile` subclass adds osType="Android", connectedApps and HTTP/DNS methods. `DeviceRegistry` manages 0..* IoTDevice instances via a Map, provides `isIoTDevice(ip): Boolean` — called by both the SIEM batch writer (storage filter) and SOAR engine (playbook routing) — and `updateStatus()` used when quarantine or release occurs. `Alert` class captures all generated security events with a `verdict` field set by analyst review via `POST /api/review/{id}`.

---

### Class Diagram — Security Analyst

![Class Diagram Security Analyst](Class%20Diagram%20-%20Security%20Analyst.png)

*Figure 7: Class Diagram — Security Analyst Subsystem*

`SecurityAnalyst` (analytId, username, role="ANALYST") uses `Dashboard` (wsURL, apiURL, connectionStatus; connect, reconnect, render) and operates `SOARControlPanel` (playbookStatus map; getPlaybookStatus, unblockIP, releaseDevice, getSOARLog). Dashboard displays 1 `AlertFeed` (alerts list, maxDisplay=500, connected; connect, receiveAlert, getLatest) and applies 1 `AlertFilter` (severity, attackType, srcIP, limit; apply()). SecurityAnalyst submits verdicts via 1 `VerdictService` (fpDatasetPath="ml/datasets/fp_dataset.csv"; submitTP, submitFP, exportToFPDataset). AlertFeed contains 0..* `Alert` records; VerdictService references those same Alert records to export FP flows.

---

### Class Diagram — Administrator / System Engineer

![Class Diagram Administrator](Class%20Diagram%20-%20Administrator_System%20Engineer.png)

*Figure 8: Class Diagram — Administrator / System Engineer Subsystem*

`Administrator` (adminId, role="ADMIN"; startPipeline, stopPipeline, trainModels, resetFirewall, clearDatabase, viewLogs) controls five management classes: `PipelineManager` (pid, status, interface, threads; start, stop, getStatus, getThreadHealth), `MLModelManager` (rfModelPath, isoModelPath, preprocessorPath; train, load, modelsExist, retrain), `PlaybookConfig` (flagsFilePath="logs/soar/playbook_flags.json", flags map; enable, disable, isEnabled, save), `SystemConfig` (iotDevices, cameraIP, backendIP, dbConfig; load, save, getIoTDevices), and `SystemHealthMonitor` (cpuUsage, memoryUsage, dbConnected, modelsLoaded; getStatus, checkDB, checkModels). Dependency arrows show PipelineManager and MLModelManager both read IPs/config from SystemConfig.

---

## Sequence Diagrams

---

### Sequence Diagram — Testbed Operator

![Sequence Diagram Testbed Operator](Sequence%20Diagram%20-%20Testbed%20Operator.png)

*Figure 9: Sequence Diagram — Testbed Operator: SYN Flood Detection and SOAR Response*

Seven lifelines: TestbedOperator (Kali Linux), NetworkSwitch (Cisco SPAN), RaspberryPi (CaptureAgent), BackendPipeline (T1–T7), SOAREngine, Firewall (UFW/iptables), Dashboard (React). Flow: (1) SYN flood injected → (2) SPAN mirrors traffic → (3) Pi streams raw PCAP TCP:9000 → (4–6) T1 writes pcap, T2 runs zeek -r, T3 parses to 15-feature dict → (7) T4 RF=0.92, ISO=-1 → (8) T5 Suricata "ET DOS SYN Flood" → (9) risk=0.91, CRITICAL → (10–13) SOAR checks threshold/window/cooldown → (14–15) `ufw insert 1 deny from <kali_ip>` → (16) "TRIGGER" returned → (17) POST /internal/broadcast → (18) dashboard shows CRITICAL + SOAR toast. `alt` fragment shows NO_ACTION if risk < 0.80; `loop` frame covers sustained attack repetition.

---

### Sequence Diagram — IoT Device

![Sequence Diagram IoT Device](Sequence%20Diagram%20-%20IoT%20Device.png)

*Figure 10: Sequence Diagram — IoT Device: Camera Attack and Device Quarantine*

Eight lifelines: WiFiCamera (192.168.50.10), Attacker (Kali acting as compromised BYOD), NetworkSwitch, RaspberryPi, BackendPipeline, SOAREngine, iptables (Firewall), Dashboard. Phase 1 (normal): camera generates RTSP → SPAN → pipeline → severity=LOW, status=NORMAL in Devices Panel. Phase 2 (attack): SYN flood FROM 192.168.50.40 TO 192.168.50.10 → pipeline T4 detects src=192.168.50.40 (IoT device!) risk=0.88 → SOAR evaluates `src_ip IN IOT_DEVICES` → routes to quarantine_device → `iptables -I FORWARD -s 192.168.50.40 -j DROP` → dashboard Devices Panel updated to QUARANTINED. `alt` fragment shows analyst RELEASE path: `POST /api/soar/unblock/192.168.50.40` removes FORWARD DROP rule, status returns to NORMAL.

---

### Sequence Diagram — Security Analyst

![Sequence Diagram Security Analyst](Sequence%20Diagram%20-%20Security%20Analyst.png)

*Figure 11: Sequence Diagram — Security Analyst: Alert Review and FP Verdict*

Six lifelines: SecurityAnalyst, Dashboard (React Browser), FastAPI (:8000), PostgreSQL (fyp_security), VerdictService, FPDataset (fp_dataset.csv). Four interaction frames shown: **[On dashboard open]** WebSocket connects → API queries last 50 alerts → replays to client → Alert Feed populated. **[Live alert arrives]** WebSocket push → CRITICAL toast shown. **[Analyst views full history]** clicks "VIEW ALL" → `GET /api/alerts/all?severity=CRITICAL&limit=200` → AllAlertsModal opens. **[Analyst submits FP verdict]** clicks FP on alert 1042 → `POST /api/review/1042 {verdict: "FP"}` → DB updated → exportToFPDataset → flow features + label=0 appended to fp_dataset.csv → verdict badge updated. Final frame: analyst unblocks 192.168.2.130 via `POST /api/soar/unblock/192.168.2.130` → ufw delete rule executed.

---

### Sequence Diagram — Administrator / System Engineer

![Sequence Diagram Administrator](Sequence%20Diagram%20—%20Administrator_System%20Engineer.png)

*Figure 12: Sequence Diagram — Administrator: Pipeline Startup and Playbook Toggle*

Six lifelines: Administrator, Dashboard (SystemControl Panel), FastAPI (:8000), start_pipeline.sh, MainPipeline (7 threads), PlaybookFlagsFile (playbook_flags.json). Four interaction frames: **[System startup]** NIC picker loads via `GET /api/system/interfaces` → admin selects "wlxe009bf6913de" → clicks START → `POST /api/system/start?zeek_interface=wlxe009bf6913de` → start_pipeline.sh executes 8 steps (kernel tuning, DB, Zeek cleanup, Suricata, ML check, env vars, API, pipeline) → all 7 threads launched. **[Status check every 4s]** `GET /api/system/status` → all pills GREEN. **[Disable playbook]** toggle "block_attacker" OFF → `POST /api/soar/playbooks/block_attacker {enabled: false}` → in-memory flag updated → `playbook_flags.json` written → toggle shows DISABLED. **[View logs]** selects "pipeline" → `GET /api/system/logs/pipeline` → last 100 lines displayed.

---

## Activity Diagram

---

### Activity Diagram — Traffic Analysis Workflow

![Activity Diagram](Activity%20Diagram.png)

*Figure 14: Activity Diagram — IoT Traffic Analysis and Threat Response Workflow*

Five swimlanes: (1) IoT Device / Attacker generates traffic. (2) Raspberry Pi captures via tcpdump on eth0 (SPAN port) and streams via socat to TCP:9000. (3) Backend Pipeline T1–T3: receives PCAP → writes /tmp/live.pcap → runs `zeek -r` → parses conn.log → extracts 15-feature dict → pushes to ML_QUEUE. (4) ML + DPI Engine T4–T5: backpressure decision (queue > 300 → apply 50%/33%/sparse sampling), RF.predict_proba() + IsolationForest.predict(), DPI decision (rf_proba > 0.30 OR iso == -1 → Suricata subprocess → parse eve.json), risk_score = 0.6×rf_proba + 0.4×iso_score, severity mapping (≥0.80 CRITICAL / 0.65–0.80 HIGH / 0.35–0.65 MEDIUM / <0.35 LOW). (5) SOAR + SIEM: queue_alert() → soar_evaluate() checks risk/window/cooldown → routes to quarantine_device or block_attacker + camera_defense + scan_detection → POST /internal/broadcast → WebSocket → Dashboard. T6 batch_loop flushes to PostgreSQL every 2s.

---

## Component Diagram

---

### Component Diagram

![Component Diagram](Component%20Diagram.png)

*Figure 16: Component Diagram — Software Architecture*

Six layers shown with UML component notation (lollipop = provided interface, socket = required interface). **Layer 1 Edge**: `CaptureAgent` — requires NetworkMirror (Switch SPAN), provides PCAPStream (TCP:9000). **Layer 2 Ingestion**: `PacketListener (T1)` → QUEUE_1 → `ZeekFeeder (T2)` → conn.log → `ZeekParser (T3)` → ML_QUEUE (15-feature flow dicts). **Layer 3 Detection**: `MLInferenceEngine (T4)` depends on RandomForestModel, IsolationForestModel, FeaturePreprocessor; provides RESULT_QUEUE. `DPIWorker (T5)` depends on SuricataEngine; provides AlertDict. Supporting components RiskScorer and AlertBuilder compute final risk_score/severity/attack_type. **Layer 5 Storage + Response**: `SIEMBatchWriter (T6)` depends on PostgreSQL. `SOAREngine` depends on BlockAttackerPlaybook (calls UFW), CameraDefensePlaybook (calls iptables), QuarantineDevicePlaybook (calls iptables), ScanDetectionPlaybook (calls iptables). **Layer 6 API + Presentation**: `FastAPIService (:8000)` provides REST endpoints and WebSocket /ws. `ReactDashboard (:3000)` requires both. `PrometheusMetrics (:9091)` receives queue_depth and inference_ms from T7.

---

## Operational Diagram

---

### Operational Diagram — Live Runtime Overview

![Operational Diagram](Operational%20Diagram.jpg)

*Figure 15: Operational Diagram — Live Runtime Process Architecture*

Three zones shown. **External Network / Devices** (left): WiFi Camera (192.168.50.10), BYOD Mobile (192.168.50.40), Cisco Switch (SPAN/mirrored traffic), Kali Linux (attack traffic to switch), Router. **Raspberry Pi 192.168.2.106** (center): `tcpdump` captures on eth0/SPAN port → output piped to `socat` TCP client → streams captured packets to Backend:9000. Two interfaces: eth0 (192.168.2.106, wired to switch), wlan0 (192.168.50.1, IOT-LAB WiFi). **Backend PC 192.168.2.101** (right): `main_pipeline.py` 7 threads (T1 packet_listener TCP:9000, T2 zeek_feeder `zeek -r`, T3 zeek_parser reads conn.log, T4 ml_inference_worker RF + ISO Forest, T5 dpi_worker Suricata subprocess, T6 batch_loop PostgreSQL:5432, T7 metrics_worker Prometheus:9091). FastAPI/Uvicorn :8000 (REST + WebSocket /ws + /internal/broadcast with x-internal-token). Suricata receives temp PCAP files (UUID-named). PostgreSQL (fyp_security/alerts) receives batch INSERT every 2s. UFW and iptables receive OS call firewall rules from SOAR. React Dashboard :3000 receives WebSocket JSON alerts.

---

## Deployment Diagram

---

### Deployment Diagram v2

![Deployment Diagram v2](Deployment%20Diagram%20v2.png)

*Figure 17: Deployment Diagram — Physical Infrastructure and Software Deployment*

Eight physical nodes. **Node 1 — Raspberry Pi 4** (Raspberry Pi OS / Ubuntu Server 22.04): CaptureAgent artifact (tcpdump + socat script); eth0=192.168.2.106 (wired to switch SPAN destination port), wlan0=192.168.50.1 (IOT-LAB WiFi SSH access). **Node 2 — Backend PC** (Ubuntu 22.04 LTS): Python 3.10 runtime hosts main_pipeline.py (7 threads), FastAPI/Uvicorn, SOAREngine, SIEMBatchWriter; Node.js runtime hosts React Dashboard (npm start :3000); PostgreSQL 15 (`fyp_security`, table `alerts`); Zeek 6.x (pcap-replay subprocess); Suricata 7.x (per-flow subprocess); Prometheus Client (:9091). **Node 3 — Cisco Managed Switch**: SPAN source ports B (Backend PC), C (WiFi Router uplink) → destination port A (Raspberry Pi). **Node 4 — WiFi Router**: subnet 192.168.50.0/24, wired uplink to switch, wireless clients: Camera + BYOD. **Node 5 — WiFi Camera** (192.168.50.10, RTSP/HTTP). **Node 6 — BYOD Mobile** (192.168.50.40, HTTP/DNS/HTTPS). **Node 7 — Kali Linux**: hping3, nmap, arpspoof; wired to Cisco switch. **Node 8 — Analyst/Admin Workstation**: web browser → http://192.168.2.101:3000. Communication paths table at bottom of diagram shows all 10 inter-node paths with protocols and ports.

---