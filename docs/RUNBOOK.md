# IoT IDS — Complete Operations Runbook
**Project:** IoT Threat Detection System (FYP Phase 7)  
**Author:** Auto-generated  
**Last Updated:** May 2026

---

## Network Topology

```
Internet
    │
    └── PC (eth0: 192.168.10.120 — Backend)
            │
        Switch (SPAN configured)
        ├── GI01 — Pi (DESTINATION/SPAN port) — eth0: 192.168.10.150
        ├── GI03 — Backend (192.168.10.120) — SOURCE port
        ├── GI05 — Router (192.168.10.1) — SOURCE port
        │           └── WiFi AP
        │               ├── IP Camera  (192.168.10.101)
        │               └── BYOD Phone (192.168.10.102)
        └── GI11 — Kali Linux (192.168.10.130) — SOURCE port

Pi WiFi (wlan0: 192.168.50.1) — IOT-LAB AP
    └── PC connects via IOT-LAB to SSH into Pi
```

---

## Prerequisites Checklist

Before starting, verify these are installed:

```bash
# Python
python3 --version          # 3.8+

# Node.js
node --version             # 16+
npm --version

# Zeek
/opt/zeek/bin/zeek --version

# PostgreSQL
sudo systemctl status postgresql

# UFW
sudo ufw status

# Socat (on Pi)
# ssh pi@192.168.50.1 "socat -V"
```

---

## PART 1 — FIRST TIME SETUP

### Step 1.1 — Train ML Models

```bash
cd ~/iot-threat-detection

# Run dataset preparer first
python3 -m ml.training.dataset_preparer

# Expected output:
# [📊 DATASET SUMMARY]
# Total rows       : 14816
# Valid rows       : 14816
# Malicious Ratio  : 0.50
# [✔] Features built successfully: 14816 samples
```

```bash
# Train models
python3 -m ml.training.model_training

# Expected output:
# [✔] Preprocessor saved
# [🔥 FINAL MODEL PERFORMANCE]
#               precision    recall  f1-score
#            0       1.00      0.75      0.86
#            1       0.80      1.00      0.89
# accuracy                           0.87
# [✔] Models saved successfully
```

**Verify models exist:**
```bash
ls -la ml/training/models/
# rf_model.pkl
# iso_model.pkl
# preprocessor.pkl
```

---

### Step 1.2 — Install Dashboard Dependencies

```bash
cd ~/iot-threat-detection/dashboard
npm install

# Fix react-scripts if broken
chmod +x node_modules/.bin/react-scripts
ln -sf ../react-scripts/bin/react-scripts.js node_modules/.bin/react-scripts
```

---

### Step 1.3 — Setup PostgreSQL Database

```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE fyp_security;" 2>/dev/null || echo "Already exists"

# Apply schema
PGPASSWORD=postgres psql -U postgres -d fyp_security \
    -f ~/iot-threat-detection/services/siem-service/db/schema.sql

# Verify
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='fyp_security', user='postgres', password='postgres')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM alerts\")
print('DB connected. Alerts:', cur.fetchone()[0])
conn.close()
"
```

---

### Step 1.4 — Configure Pi Capture Script

SSH into Pi and update capture script:

```bash
# Connect to Pi (IOT-LAB WiFi must be connected first)
sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de  # add route if needed
ssh pi@192.168.50.1
```

On Pi, verify/update `~/edge/capture/capture.sh`:

```bash
cat ~/edge/capture/capture.sh
```

It should contain:
```bash
#!/bin/bash
BACKEND_IP="192.168.50.21"   # PC's IOT-LAB IP (check with: ip addr show wlx...)
BACKEND_PORT="9000"
RECONNECT_DELAY="3"

sudo tc qdisc del dev eth0 ingress 2>/dev/null || true
sudo tc qdisc del dev wlan0 ingress 2>/dev/null || true
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[CAPTURE] SPAN eth0 → $BACKEND_IP:$BACKEND_PORT"
while true; do
    sudo tcpdump -i eth0 -B 4096 -s 0 -U -w - \
        'host 192.168.10.101 or host 192.168.10.102 or host 192.168.10.130 or host 192.168.10.1' \
        2>/dev/null | \
    socat - TCP:$BACKEND_IP:$BACKEND_PORT,retry=999,interval=3,keepalive,keepidle=10,keepintvl=5,keepcnt=3
    sleep "$RECONNECT_DELAY"
done
```

**Important:** Check PC's IOT-LAB IP:
```bash
# On PC (after connecting to IOT-LAB WiFi):
ip addr show wlxe009bf6913de | grep "192.168.50"
# Use that IP as BACKEND_IP in Pi's capture.sh
```

---

## PART 2 — NORMAL SESSION STARTUP

### Step 2.1 — Connect IOT-LAB WiFi

Connect PC to IOT-LAB WiFi network, then add route:

```bash
sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de
```

Verify:
```bash
ping -c 2 192.168.50.1
# Should get replies
```

---

### Step 2.2 — Start Backend Pipeline

```bash
cd ~/iot-threat-detection
bash infrastructure/scripts/stop_pipeline.sh  # stop any existing
bash infrastructure/scripts/start_pipeline.sh
```

**Verify pipeline started:**
```bash
# Check all 7 threads launched
tail -15 logs/pipeline/main_pipeline.log
# Should see: [✔] All 7 threads launched

# Check API is running
curl -s http://localhost:8000/health
# {"status":"ok"}

# Check port 9000 listening
ss -tlnp | grep 9000
# LISTEN 0.0.0.0:9000
```

---

### Step 2.3 — Start Dashboard

```bash
cd ~/iot-threat-detection/dashboard
node node_modules/react-scripts/bin/react-scripts.js start
```

Open browser: `http://localhost:3000`

**Verify dashboard:**
- Header shows "OFFLINE" (Pi not connected yet)
- Stats show current DB counts
- No alerts in feed yet

---

### Step 2.4 — Start Pi Capture

In a new terminal (IOT-LAB connected):

```bash
ssh pi@192.168.50.1
bash ~/edge/capture/capture.sh
```

**Verify Pi connected (on backend):**
```bash
tail -5 logs/pipeline/packet_listener.log
# [+] Client connected: ('192.168.50.1', xxxxx)
# [+] Fresh pcap file ready: /tmp/live.pcap
```

Dashboard should now show "LIVE" status.

---

### Step 2.5 — Start Kali Services

On Kali machine:

```bash
# Terminal 1 — HTTP server (for BYOD traffic)
python3 -m http.server 8080

# Terminal 2 — NC listener (for bulk traffic)
nc -lvnp 4444

# Terminal 3 — Camera stream
python3 camera.py
```

---

### Step 2.6 — Start Phone Traffic (Termux)

On Android phone in Termux:

```bash
bash master_traffic.sh
```

---

### Step 2.7 — Verify Traffic Flowing

```bash
# Check Zeek is processing traffic
tail -5 logs/pipeline/zeek_feeder.log
# [+] Zeek finished on /tmp/live.pcap.snap

# Check ML inference running
tail -5 logs/pipeline/ml_inference.log
# [T3] ML inference worker started

# Check alerts in DB
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='fyp_security', user='postgres', password='postgres')
cur = conn.cursor()
cur.execute(\"SELECT src_ip, COUNT(*) FROM alerts WHERE timestamp > NOW() - INTERVAL '5 minutes' GROUP BY src_ip ORDER BY COUNT(*) DESC\")
for r in cur.fetchall():
    print(f'  {r[0]:20} : {r[1]} alerts')
conn.close()
"
```

Expected IPs: `192.168.10.101`, `192.168.10.102`, `192.168.10.130`, `192.168.10.1`

---

## PART 3 — ATTACK TESTING

### Step 3.1 — Test Port Scan (Playbook 4)

On Kali:
```bash
bash iot_camera_simulator.sh
# Select: 1 (Fast Scan)
```

**Verify on backend:**
```bash
cat logs/soar/scan_detection.log
# 2026-...T... | SCANNER=192.168.10.130 | UNIQUE_PORTS=20 | ACTION=THROTTLED
```

---

### Step 3.2 — Test Camera Defense (Playbook 2)

On Kali:
```bash
bash iot_camera_simulator.sh
# Select: 10 (Burst Traffic) or 13 (Full Pipeline)
```

**Verify:**
```bash
cat logs/soar/camera_defense.log
# 2026-...T... | ATTACKER=192.168.10.130 | TARGET=192.168.10.101 | SEVERITY=CRITICAL
```

---

### Step 3.3 — Test Block Attacker (Playbook 1)

On Kali:
```bash
bash attack_simulator.sh
# Select: 3 (ICMP Flood)
# OR: sudo hping3 -1 --flood 192.168.10.101
```

Wait 60 seconds for 3+ CRITICAL events.

**Verify block applied:**
```bash
sudo ufw status numbered | grep DENY
# [ X] Anywhere  DENY IN  192.168.10.130

cat logs/siem/soar_engine.log | grep "TRIGGER\|PB1\|BLOCKED"
# [SOAR TRIGGER] src_ip=192.168.10.130 risk=0.8x
# [PB1] block_attacker → BLOCKED
```

---

### Step 3.4 — Test BYOD Attack (Playbook 3)

On Kali:
```bash
bash attack_simulator.sh
# Select: 4 (SYN Flood) — target is 192.168.10.102
```

**Verify quarantine:**
```bash
cat logs/soar/quarantine.log
# 2026-...T... | QUARANTINED=192.168.10.102 (Android BYOD) | RISK=0.85

sudo iptables -L FORWARD | grep 10.102
# DROP  all  --  192.168.10.102  anywhere
```

---

### Step 3.5 — Test Full Attack Pipeline

On Kali:
```bash
bash attack_simulator.sh
# Select: 13 (Run FULL Pipeline)
```

Monitor dashboard in real-time — should see:
- CRITICAL alerts flooding in
- Toast notifications with QUARANTINE button
- Top Attackers updating
- Attack Timeline spikes

---

## PART 4 — VERIFICATION COMMANDS

### Check Pipeline Health

```bash
# All 7 threads running?
ps aux | grep main_pipeline | grep -v grep

# API responding?
curl -s http://localhost:8000/health

# WebSocket working?
curl -s http://localhost:8000/api/alerts?limit=5 | python3 -m json.tool | head -20

# Prometheus metrics?
curl -s http://localhost:9091/metrics | grep pipeline | head -5
```

---

### Check ML Models

```bash
python3 -c "
import sys, joblib
sys.path.insert(0, '.')
rf  = joblib.load('ml/training/models/rf_model.pkl')
iso = joblib.load('ml/training/models/iso_model.pkl')
pp  = joblib.load('ml/training/models/preprocessor.pkl')
print('RF  :', type(rf).__name__, '| estimators:', rf.n_estimators)
print('ISO :', type(iso).__name__, '| estimators:', iso.n_estimators)
print('PP  :', type(pp).__name__)
print('Proto map:', pp.proto_map)
print('Service map:', pp.service_map)
print('ConnState map:', pp.conn_state_map)
"
```

---

### Check Database

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='fyp_security', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM alerts')
print('Total alerts:', cur.fetchone()[0])

cur.execute('SELECT severity, COUNT(*) FROM alerts GROUP BY severity ORDER BY COUNT(*) DESC')
print('By severity:', cur.fetchall())

cur.execute('SELECT src_ip, COUNT(*), MAX(risk_score)::numeric(4,2) FROM alerts GROUP BY src_ip ORDER BY COUNT(*) DESC LIMIT 8')
print('By IP:')
for r in cur.fetchall():
    print(f'  {r[0]:20} : {r[1]:5} alerts | max_risk={r[2]}')

cur.execute(\"SELECT COUNT(*) FROM alerts WHERE timestamp > NOW() - INTERVAL '5 minutes'\")
print('Last 5 min:', cur.fetchone()[0])
conn.close()
"
```

---

### Check SOAR Status

```bash
# Engine log
cat logs/siem/soar_engine.log | tail -20

# Playbook logs
cat logs/soar/camera_defense.log 2>/dev/null || echo "No camera events"
cat logs/soar/quarantine.log 2>/dev/null || echo "No quarantine events"
cat logs/soar/scan_detection.log 2>/dev/null || echo "No scan events"

# Active blocks
sudo ufw status numbered | grep DENY

# Active quarantines
sudo iptables -L FORWARD -n | grep DROP
```

---

### Check Pi Connection

```bash
# Is Pi connected?
tail -5 logs/pipeline/packet_listener.log

# Is pcap being written?
ls -la /tmp/live.pcap
# Check timestamp — should be recent

# Is Zeek processing?
tail -5 logs/pipeline/zeek_feeder.log

# What IPs in conn.log?
python3 -c "
import subprocess
r = subprocess.run(['grep', '-v', '^#', 'services/flow_service/logs/zeek/current/conn.log'], capture_output=True, text=True)
ips = {}
for line in r.stdout.strip().split('\n'):
    parts = line.split('\t')
    if len(parts) >= 5:
        ips[parts[2]] = ips.get(parts[2], 0) + 1
for ip, count in sorted(ips.items(), key=lambda x: -x[1])[:10]:
    print(f'  {ip:25} : {count}')
"
```

---

### Check All Log Files

```bash
# Pipeline logs
ls -la logs/pipeline/
tail -5 logs/pipeline/main_pipeline.log
tail -5 logs/pipeline/packet_listener.log
tail -5 logs/pipeline/zeek_feeder.log
tail -5 logs/pipeline/zeek_parser.log
tail -5 logs/pipeline/ml_inference.log
tail -5 logs/pipeline/dpi_worker.log

# Dashboard logs
tail -5 logs/dashboard/api_service.log
tail -5 logs/dashboard/uvicorn.log

# SIEM logs
tail -5 logs/siem/soar_engine.log
tail -5 logs/siem/batch_writer.log 2>/dev/null

# SOAR playbook logs
ls -la logs/soar/
cat logs/soar/camera_defense.log 2>/dev/null
cat logs/soar/quarantine.log 2>/dev/null
cat logs/soar/scan_detection.log 2>/dev/null
```

---

## PART 5 — RESET & CLEANUP

### Reset Firewall (Before Each Test Session)

```bash
bash infrastructure/scripts/reset_firewall.sh

# Verify clean
sudo ufw status numbered | grep DENY
# Should be empty
sudo iptables -L FORWARD -n | grep DROP
# Should be empty
```

---

### Clear Database (Fresh Start)

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='fyp_security', user='postgres', password='postgres')
cur = conn.cursor()
cur.execute('TRUNCATE TABLE alerts RESTART IDENTITY')
conn.commit()
cur.execute('SELECT COUNT(*) FROM alerts')
print('Alerts after clear:', cur.fetchone()[0])
conn.close()
"
```

---

### Stop Everything

```bash
bash infrastructure/scripts/stop_pipeline.sh

# Kill dashboard if running
pkill -f "react-scripts" 2>/dev/null || true

# Verify stopped
ps aux | grep -E "main_pipeline|uvicorn|react" | grep -v grep
```

---

### Clear Logs

```bash
# Clear pipeline logs
> logs/pipeline/main_pipeline.log
> logs/pipeline/packet_listener.log
> logs/pipeline/zeek_feeder.log
> logs/pipeline/zeek_parser.log
> logs/pipeline/ml_inference.log
> logs/pipeline/dpi_worker.log

# Clear SOAR logs
> logs/siem/soar_engine.log
> logs/soar/camera_defense.log 2>/dev/null
> logs/soar/quarantine.log 2>/dev/null
> logs/soar/scan_detection.log 2>/dev/null

echo "Logs cleared"
```

---

## PART 6 — TROUBLESHOOTING

### Pi Not Connecting

```bash
# Check Pi eth0 IP
ssh pi@192.168.50.1 "ip addr show eth0"
# Should have 192.168.10.150 or similar

# If no IP, set static:
ssh pi@192.168.50.1 "sudo ip addr add 192.168.10.150/24 dev eth0"

# Check Pi can reach backend
ssh pi@192.168.50.1 "ping -c 3 192.168.10.120"
# If fails — SPAN port issue, check switch config

# Check capture script running
ssh pi@192.168.50.1 "ps aux | grep tcpdump"
```

---

### No Alerts Generating

```bash
# 1. Is Pi connected?
tail -3 logs/pipeline/packet_listener.log

# 2. Is Zeek running?
tail -3 logs/pipeline/zeek_feeder.log

# 3. Is conn.log being written?
ls -la services/flow_service/logs/zeek/current/conn.log

# 4. Are flows being parsed?
tail -3 logs/pipeline/zeek_parser.log

# 5. Is ML queue filling?
python3 -c "
import sys; sys.path.insert(0,'.')
from services.flow_service.state import ML_QUEUE
print('ML Queue size:', len(ML_QUEUE))
"
```

---

### SOAR Not Triggering

```bash
# Check threshold — need risk >= 0.80 AND 3+ events in 60s
grep "RISK_THRESHOLD" services/soar-service/engine/soar_engine.py

# Check recent high-risk alerts
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='fyp_security', user='postgres', password='postgres')
cur = conn.cursor()
cur.execute(\"SELECT src_ip, risk_score, severity, timestamp FROM alerts WHERE risk_score >= 0.80 ORDER BY timestamp DESC LIMIT 10\")
for r in cur.fetchall():
    print(r)
conn.close()
"

# Check SOAR engine loaded correctly
tail -5 logs/pipeline/main_pipeline.log | grep -i soar
```

---

### Dashboard Not Loading

```bash
# Check react-scripts
ls -la dashboard/node_modules/.bin/react-scripts
# Should be symlink, not empty file

# Fix if empty:
ln -sf ../react-scripts/bin/react-scripts.js dashboard/node_modules/.bin/react-scripts
chmod +x dashboard/node_modules/react-scripts/bin/react-scripts.js

# Check API
curl -s http://localhost:8000/health
# If fails — restart pipeline
```

---

### Database Connection Error

```bash
# Check PostgreSQL running
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql

# Test connection
PGPASSWORD=postgres psql -U postgres -d fyp_security -c "SELECT 1"
```

---

## PART 7 — QUICK REFERENCE

### Key File Locations

| File | Purpose |
|------|---------|
| `ml/training/models/rf_model.pkl` | Random Forest model |
| `ml/training/models/iso_model.pkl` | Isolation Forest model |
| `ml/training/models/preprocessor.pkl` | Feature preprocessor |
| `ml/datasets/balanced_dataset.csv` | Training dataset |
| `services/flow_service/zeek_parser.py` | Zeek conn.log parser |
| `services/flow_service/core/risk_scorer.py` | Risk scoring logic |
| `services/soar-service/engine/soar_engine.py` | SOAR orchestrator |
| `services/soar-service/rules/` | 4 playbook files |
| `infrastructure/scripts/reset_firewall.sh` | Firewall reset |
| `infrastructure/scripts/start_pipeline.sh` | Pipeline startup |

---

### Key Ports

| Port | Service |
|------|---------|
| 3000 | React Dashboard |
| 8000 | FastAPI (REST + WebSocket) |
| 9000 | Pi PCAP stream receiver |
| 9091 | Prometheus metrics |
| 5432 | PostgreSQL |

---

### Device IP Map

| IP | Device | Role |
|----|--------|------|
| 192.168.10.1 | Router | Gateway |
| 192.168.10.101 | IP Camera | IoT Device |
| 192.168.10.102 | Android BYOD | IoT Device |
| 192.168.10.120 | Backend PC | Detection Engine |
| 192.168.10.130 | Kali Linux | Attacker |
| 192.168.10.150 | Pi (eth0) | Capture Node |
| 192.168.50.1 | Pi (wlan0) | IOT-LAB AP |

---

### Severity Thresholds

| Severity | Risk Score | Action |
|----------|-----------|--------|
| CRITICAL | ≥ 0.80 | SOAR trigger |
| HIGH | ≥ 0.60 | Alert + Toast |
| MEDIUM | ≥ 0.35 | Alert |
| LOW | < 0.35 | Log only |

---

### SOAR Playbook Summary

| Playbook | Trigger | Action | Log |
|----------|---------|--------|-----|
| block_attacker | CRITICAL from external | UFW DENY rule | soar_engine.log |
| camera_defense | Attack on 10.101 | iptables rate limit | soar/camera_defense.log |
| quarantine_device | CRITICAL from IoT | iptables FORWARD DROP | soar/quarantine.log |
| scan_detection | 20+ ports in 30s | iptables throttle | soar/scan_detection.log |

---

## PART 8 — COMPLETE SESSION CHECKLIST

```
PRE-SESSION:
[ ] IOT-LAB WiFi connected on PC
[ ] sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de
[ ] Pi reachable: ping 192.168.50.1

STARTUP:
[ ] bash infrastructure/scripts/stop_pipeline.sh
[ ] bash infrastructure/scripts/start_pipeline.sh
[ ] curl http://localhost:8000/health → {"status":"ok"}
[ ] node node_modules/react-scripts/bin/react-scripts.js start
[ ] ssh pi@192.168.50.1 && bash ~/edge/capture/capture.sh
[ ] tail logs/pipeline/packet_listener.log → "Client connected"
[ ] Dashboard shows "LIVE"

KALI SERVICES:
[ ] python3 -m http.server 8080
[ ] nc -lvnp 4444
[ ] python3 camera.py

PHONE:
[ ] bash master_traffic.sh

VERIFY TRAFFIC:
[ ] Dashboard shows 10.101, 10.102, 10.130 in Connected Devices
[ ] Alerts appearing in Live Alert Feed

ATTACK TEST:
[ ] bash attack_simulator.sh → Option 3 (ICMP Flood)
[ ] Wait 60s → SOAR trigger
[ ] sudo ufw status | grep DENY → Kali blocked
[ ] cat logs/soar/quarantine.log → BYOD quarantined

POST-SESSION:
[ ] bash infrastructure/scripts/reset_firewall.sh
[ ] sudo ufw status | grep DENY → empty
[ ] bash infrastructure/scripts/stop_pipeline.sh
```

---

*IoT IDS FYP — Phase 7 | Complete Runbook*
