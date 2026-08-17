# IoT IDS — Complete Operations Runbook

**Project:** IoT Threat Detection & Security Monitoring Platform  
**Last Updated:** August 2026

> This is the single authoritative guide for setting up, running, and troubleshooting the system.
> Always use `bash infrastructure/scripts/start_pipeline.sh` to start — never launch services individually.

---

## Network Topology (Real Deployment)

```
                  WiFi Router
                  192.168.50.0/24 (wireless)
                       │
           ┌───────────┼───────────┐
           │                       │
    WiFi Camera              BYOD Mobile
    192.168.50.10            192.168.50.40
    (IoT Device)             (IoT Device)

      Managed Switch (SPAN configured)
      ├── Port A ── Raspberry Pi     192.168.2.106   ← SPAN destination
      ├── Port B ── Backend PC       192.168.2.101   ← source (mirrored)
      ├── Port C ── WiFi Router      (uplink)         ← source (mirrored)
      └── Port D ── Kali Linux       192.168.2.x     ← testbed operator

IOT-LAB WiFi (out-of-band management network)
      Backend PC:  wlxe009bf6913de   192.168.50.21  (check with: ip addr show wlxe009bf6913de)
      Pi wlan0:    192.168.50.1                      ← SSH access point
```

> **Important:** IPs may differ on your specific setup. The single source of truth is
> `shared/config/system_config.yaml`. Update it before starting the system.

### Device IP Map

| IP | Device | Role |
|----|--------|------|
| 192.168.50.10 | WiFi Camera | Monitored IoT Device (wireless) |
| 192.168.50.40 | BYOD Mobile | Monitored IoT Device (wireless) |
| 192.168.2.101 | Backend PC | Detection engine, ML, API, dashboard |
| 192.168.2.106 | Raspberry Pi (eth0) | SPAN destination, PCAP capture agent |
| 192.168.50.1 | Raspberry Pi (wlan0) | IOT-LAB AP — SSH access |
| 192.168.50.21 | Backend PC (wlxe009bf6913de) | IOT-LAB IP — used as BACKEND_IP in Pi script |
| Kali IP | Kali Linux | Testbed operator / attack simulation |

---

## Prerequisites Checklist

```bash
# Python 3.10+
python3 --version

# Node.js 18+ and npm
node --version
npm --version

# Zeek (pcap-replay mode)
/opt/zeek/bin/zeek --version

# Suricata
suricata --version

# PostgreSQL
sudo systemctl status postgresql

# UFW
sudo ufw status

# socat (on Raspberry Pi — not backend)
ssh pi@192.168.50.1 "socat -V"
```

---

## PART 1 — FIRST TIME SETUP

### Step 1.0 — Configure Device IPs

Before anything else, update `shared/config/system_config.yaml` with your actual device IPs:

```yaml
network:
  monitored_ips:
    - "192.168.2.101"    # Backend PC
    - "192.168.50.10"    # WiFi Camera
    - "192.168.50.40"    # BYOD Mobile
  iot_devices:
    - "192.168.50.10"    # WiFi Camera
    - "192.168.50.40"    # BYOD Mobile
  camera_ip: "192.168.50.10"
  backend_ip: "192.168.2.101"
```

Create `dashboard/.env`:

```bash
cat > dashboard/.env << 'EOF'
REACT_APP_API_URL=http://192.168.2.101:8000
REACT_APP_WS_URL=ws://192.168.2.101:8000/ws
EOF
```

Find your actual backend NIC:

```bash
ip link show
# Look for your wired interface: eth0, ens3, enp3s0, etc.
ip addr show
```

---

### Step 1.1 — Install System Dependencies

```bash
# Zeek
sudo apt install zeek

# Or from source (recommended for latest version)
# See: https://zeek.org/get-zeek/

# Add to PATH
echo 'export PATH=/opt/zeek/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Suricata
sudo apt install suricata
sudo suricata-update
sudo suricata --build-info | grep "Features"

# UFW
sudo apt install ufw
sudo ufw enable
```

---

### Step 1.2 — Configure sudo Rules for Pipeline

The pipeline needs passwordless sudo for UFW and iptables:

```bash
bash infrastructure/scripts/setup_sudo.sh
```

This creates a sudoers entry allowing the pipeline to run `ufw` and `iptables` without a password prompt.

Verify:

```bash
sudo -n ufw status    # should not ask for password
sudo -n iptables -L   # should not ask for password
```

---

### Step 1.3 — Python Environment

```bash
# From project root
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Verify key packages
python3 -c "import fastapi, sklearn, psycopg2, scapy; print('OK')"
```

---

### Step 1.4 — Set Up PostgreSQL Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE fyp_security;" 2>/dev/null \
    || echo "Already exists"

# Apply schema (idempotent — uses IF NOT EXISTS)
PGPASSWORD=postgres psql -U postgres -d fyp_security \
    -f services/siem-service/db/schema.sql

# Verify
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='fyp_security', user='postgres', password='postgres'
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM alerts')
print('DB connected. Alerts:', cur.fetchone()[0])
conn.close()
"
```

---

### Step 1.5 — Train ML Models

```bash
cd ~/iot-threat-detection   # or your project root

# Step 1: Prepare and balance dataset
python3 -m ml.training.dataset_preparer

# Expected output:
# [📊 DATASET SUMMARY]
# Total rows       : 14816
# Valid rows       : 14816
# Malicious Ratio  : 0.50
# [✔] Features built successfully: 14816 samples

# Step 2: Train both models
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

Verify:

```bash
ls -la ml/training/models/
# rf_model.pkl
# iso_model.pkl
# preprocessor.pkl
```

> If models are missing at startup, `start_pipeline.sh` auto-trains them (takes ~60s).

---

### Step 1.6 — Install Dashboard Dependencies

```bash
cd dashboard
npm install

# If react-scripts symlink is broken:
chmod +x node_modules/.bin/react-scripts
ln -sf ../react-scripts/bin/react-scripts.js node_modules/.bin/react-scripts
cd ..
```

---

### Step 1.7 — Configure Pi Capture Script

SSH into the Pi (connect to IOT-LAB WiFi first):

```bash
# Add route to IOT-LAB subnet on backend
sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de

# SSH in
ssh pi@192.168.50.1
```

On the Pi, verify `~/edge/capture/capture.sh`:

```bash
cat ~/edge/capture/capture.sh
```

It should look like this (update BACKEND_IP to your backend's IOT-LAB IP):

```bash
#!/bin/bash
# On backend: ip addr show wlxe009bf6913de | grep inet
BACKEND_IP="192.168.50.21"     # ← backend's wlxe009bf6913de address
BACKEND_PORT="9000"
RECONNECT_DELAY="3"

sudo tc qdisc del dev eth0 ingress 2>/dev/null || true
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[CAPTURE] SPAN eth0 → $BACKEND_IP:$BACKEND_PORT"
while true; do
    sudo tcpdump -i eth0 -B 4096 -s 0 -U -w - \
        'host 192.168.50.10 or host 192.168.50.40 or host 192.168.2.101' \
        2>/dev/null | \
    socat - TCP:$BACKEND_IP:$BACKEND_PORT,retry=999,interval=3,keepalive,keepidle=10,keepintvl=5,keepcnt=3
    sleep "$RECONNECT_DELAY"
done
```

> The BPF filter (`host 192.168.50.10 or ...`) restricts the stream to monitored device traffic only.
> Update the IPs in the filter to match your actual devices.

---

## PART 2 — NORMAL SESSION STARTUP

### Step 2.1 — Connect IOT-LAB WiFi (Backend PC)

```bash
# Connect to IOT-LAB WiFi via NetworkManager or manually
# Then add route to reach Pi
sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de

# Verify Pi reachable
ping -c 2 192.168.50.1
```

---

### Step 2.2 — Find and Set Your NIC

```bash
# List all interfaces
ip link show

# Find the interface connected to the managed switch (wired)
# Usually: eth0, ens3, enp3s0, eno1, etc.
ip addr show eth0   # replace with your NIC name
```

Export it before starting:

```bash
export ZEEK_INTERFACE=eth0    # replace with your actual NIC
```

Or use the **NIC picker** in the System Control panel on the dashboard (it calls `GET /api/system/interfaces` and lets you select from a dropdown).

---

### Step 2.3 — Start Backend Pipeline

```bash
cd ~/iot-threat-detection

# Stop any previous run
bash infrastructure/scripts/stop_pipeline.sh

# Start everything
export ZEEK_INTERFACE=eth0     # ← your NIC
bash infrastructure/scripts/start_pipeline.sh
```

What the startup script does (in order):

| Step | Action |
|------|--------|
| 1 | Kernel buffer tuning (rmem_max, netdev_max_backlog) |
| 1.5 | Reset SOAR firewall rules from any previous session |
| 2 | Start PostgreSQL, create DB if missing, apply schema |
| 3 | Kill any stale `zeek -i` process (pcap mode — Zeek managed by T2) |
| 4 | Start Suricata (DPI engine) |
| 5 | Init `ml/datasets/fp_dataset.csv` if missing |
| 6 | Export all env vars (ZEEK_LOG_DIR, ZEEK_MODE, INTERNAL_TOKEN, etc.) |
| 7.5 | Auto-train ML models if `rf_model.pkl` is missing |
| 7 | Start FastAPI on :8000 |
| 8 | Start main pipeline (7 threads) |

Verify startup:

```bash
# API health
curl -s http://localhost:8000/health
# {"status":"ok"}

# Pipeline threads launched
tail -15 logs/pipeline/main_pipeline.log
# [✔] All 7 threads launched

# Port 9000 listening for Pi
ss -tlnp | grep 9000
# LISTEN  0.0.0.0:9000
```

---

### Step 2.4 — Start Dashboard

```bash
cd ~/iot-threat-detection/dashboard
npm start
# Or: node node_modules/react-scripts/bin/react-scripts.js start
```

Open `http://localhost:3000`

Verify:
- Header shows **OFFLINE** (Pi not yet connected)
- Stats bar shows current DB counts
- System Control panel shows pipeline status

---

### Step 2.5 — Start Pi Capture Agent

In a new terminal:

```bash
ssh pi@192.168.50.1
bash ~/edge/capture/capture.sh
```

Verify on backend:

```bash
tail -5 logs/pipeline/packet_listener.log
# [+] Client connected: ('192.168.50.x', xxxxx)
# [+] Fresh pcap file ready: /tmp/live.pcap
```

Dashboard header switches from **OFFLINE** → **LIVE**.

---

### Step 2.6 — Start Kali Traffic Generation

On Kali Linux (testbed operator):

```bash
# Terminal 1 — HTTP server (generates normal traffic)
python3 -m http.server 8080

# Terminal 2 — netcat listener
nc -lvnp 4444

# Terminal 3 — camera simulation / attack scripts
bash iot_camera_simulator.sh
```

---

### Step 2.7 — Verify Traffic Is Flowing

```bash
# Zeek processing pcap?
tail -5 logs/pipeline/zeek_feeder.log
# [+] Zeek finished on /tmp/live.pcap.snap

# ML inference running?
tail -5 logs/pipeline/ml_inference.log
# [T4] ML inference worker running

# Recent alerts in DB?
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='fyp_security', user='postgres', password='postgres'
)
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT src_ip, COUNT(*) as cnt
    FROM alerts
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    GROUP BY src_ip
    ORDER BY cnt DESC
\"\"\")
for r in cur.fetchall():
    print(f'  {str(r[0]):25} : {r[1]} alerts')
conn.close()
"
```

---

## PART 3 — ATTACK TESTING

> Reset firewall before every test session: `bash infrastructure/scripts/reset_firewall.sh`

### Test 1 — Port Scan → Playbook 4 (Scan Detection)

On Kali:

```bash
nmap -sS -p 1-1000 192.168.50.10
# Or: bash iot_camera_simulator.sh → option 1 (Fast Scan)
```

Verify:

```bash
cat logs/soar/scan_detection.log
# [SCAN_DETECTION] SCANNER=<kali_ip> | UNIQUE_PORTS=20+ | ACTION=THROTTLED
```

---

### Test 2 — Camera Flood → Playbook 2 (Camera Defense)

On Kali:

```bash
sudo hping3 --flood 192.168.50.10
# Or: bash iot_camera_simulator.sh → option 10 (Burst Traffic)
```

Verify:

```bash
cat logs/soar/camera_defense.log
# [CAMERA_DEFENSE] ATTACKER=<kali_ip> | TARGET=192.168.50.10 | ACTION=RATE_LIMITED
```

---

### Test 3 — ICMP Flood → Playbook 1 (Block Attacker)

On Kali:

```bash
sudo hping3 -1 --flood 192.168.2.101
```

Wait 60 seconds for 3+ CRITICAL events to accumulate.

Verify:

```bash
# SOAR trigger logged
grep "TRIGGER\|PB1\|BLOCKED" logs/siem/soar_engine.log | tail -5
# [SOAR TRIGGER] src_ip=<kali_ip> risk=0.8x
# [PB1] block_attacker → BLOCKED

# UFW rule applied
sudo ufw status numbered | grep DENY
# [ X] Anywhere  DENY IN  <kali_ip>
```

---

### Test 4 — SYN Flood from BYOD → Playbook 3 (Quarantine)

Simulate compromised BYOD (or from Kali spoofing BYOD IP):

```bash
sudo hping3 -S --flood -a 192.168.50.40 192.168.2.101
```

Verify:

```bash
cat logs/soar/quarantine.log
# [QUARANTINE] DEVICE=192.168.50.40 | RISK=0.85+ | ACTION=FORWARD_DROP

sudo iptables -L FORWARD -n | grep DROP
# DROP  all  --  192.168.50.40  anywhere
```

---

### Test 5 — Full Attack Pipeline

```bash
bash attack_simulator.sh
# Select: 13 (Run FULL Pipeline)
```

Monitor dashboard in real time — expect:
- CRITICAL alerts in live feed
- Toast notifications
- Top Attackers updating
- Attack Timeline ECG spikes
- SOAR panel showing triggered playbooks

---

### Toggle Playbooks During Test

From the dashboard **SOAR Panel**, click any playbook toggle to disable it live. Verify in:

```bash
cat logs/soar/playbook_flags.json
# {"block_attacker": false, "camera_defense": true, ...}
```

The SOAR engine reads this file on every evaluation — no restart needed.

---

## PART 4 — VERIFICATION COMMANDS

### Check Pipeline Health

```bash
# All processes running?
cat /tmp/iot_ids_pipeline.pid | xargs ps -p
cat /tmp/iot_ids_api.pid | xargs ps -p

# API healthy?
curl -s http://localhost:8000/health
# {"status":"ok"}

# All alert counts
curl -s http://localhost:8000/api/alerts?limit=5 | python3 -m json.tool | head -30

# Prometheus metrics
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
print('Service map (sample):', list(pp.service_map.items())[:5])
"

# Verify baseline_calibration.py present
ls services/flow_service/core/baseline_calibration.py
```

---

### Check Database

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='fyp_security', user='postgres', password='postgres'
)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM alerts')
print('Total alerts:', cur.fetchone()[0])

cur.execute('SELECT severity, COUNT(*) FROM alerts GROUP BY severity ORDER BY COUNT(*) DESC')
print('By severity:', cur.fetchall())

cur.execute(\"\"\"
    SELECT src_ip, COUNT(*), ROUND(MAX(risk_score)::numeric, 2)
    FROM alerts
    GROUP BY src_ip
    ORDER BY COUNT(*) DESC
    LIMIT 8
\"\"\")
print('By IP:')
for r in cur.fetchall():
    print(f'  {str(r[0]):25} : {r[1]:5} alerts | max_risk={r[2]}')

cur.execute(\"SELECT COUNT(*) FROM alerts WHERE timestamp > NOW() - INTERVAL '5 minutes'\")
print('Last 5 min:', cur.fetchone()[0])
conn.close()
"
```

---

### Check SOAR Status

```bash
# Engine log (last 20 lines)
tail -20 logs/siem/soar_engine.log

# Individual playbook logs
cat logs/soar/camera_defense.log  2>/dev/null || echo "No camera events"
cat logs/soar/quarantine.log      2>/dev/null || echo "No quarantine events"
cat logs/soar/scan_detection.log  2>/dev/null || echo "No scan events"

# Runtime toggle state
cat logs/soar/playbook_flags.json 2>/dev/null || echo "No flags file (all enabled by default)"

# Active UFW blocks
sudo ufw status numbered | grep DENY

# Active quarantine rules
sudo iptables -L FORWARD -n | grep DROP
```

---

### Check Pi Connection

```bash
# Is Pi connected?
tail -5 logs/pipeline/packet_listener.log

# Is /tmp/live.pcap being written (check timestamp)?
ls -la /tmp/live.pcap

# Is Zeek processing it?
tail -5 logs/pipeline/zeek_feeder.log

# What source IPs are in current conn.log?
python3 -c "
import subprocess
r = subprocess.run(
    ['grep', '-v', '^#', 'services/flow_service/logs/zeek/current/conn.log'],
    capture_output=True, text=True
)
ips = {}
for line in r.stdout.strip().split('\n'):
    parts = line.split('\t')
    if len(parts) >= 5:
        ips[parts[2]] = ips.get(parts[2], 0) + 1
for ip, count in sorted(ips.items(), key=lambda x: -x[1])[:10]:
    print(f'  {ip:25} : {count} flows')
" 2>/dev/null || echo "conn.log not yet available"
```

---

### Check All Log Files

```bash
# Pipeline threads
for f in main_pipeline packet_listener zeek_feeder zeek_parser ml_inference dpi_worker; do
    echo "── $f ──"
    tail -3 logs/pipeline/${f}.log 2>/dev/null || echo "  (no log yet)"
done

# Dashboard / API
tail -5 logs/dashboard/api_service.log  2>/dev/null
tail -5 logs/dashboard/uvicorn.log      2>/dev/null

# SIEM
tail -5 logs/siem/soar_engine.log   2>/dev/null
tail -5 logs/siem/batch_writer.log  2>/dev/null

# SOAR playbooks
ls -la logs/soar/ 2>/dev/null
```

---

## PART 5 — RESET & CLEANUP

### Reset Firewall (Before Each Test Session)

```bash
bash infrastructure/scripts/reset_firewall.sh
```

This removes all UFW DENY rules and iptables FORWARD/INPUT rules added by SOAR playbooks.

Verify clean state:

```bash
sudo ufw status numbered | grep -E "DENY|DROP" || echo "No block rules — clean"
sudo iptables -L FORWARD -n | grep DROP            || echo "No quarantine rules — clean"
```

---

### Clear Database

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='fyp_security', user='postgres', password='postgres'
)
cur = conn.cursor()
cur.execute('TRUNCATE TABLE alerts RESTART IDENTITY')
conn.commit()
cur.execute('SELECT COUNT(*) FROM alerts')
print('Alerts after clear:', cur.fetchone()[0])
conn.close()
"
```

Or use the **Clear DB** button in the **System Control** panel on the dashboard.

---

### Stop Everything

```bash
bash infrastructure/scripts/stop_pipeline.sh

# Stop dashboard if running
pkill -f "react-scripts" 2>/dev/null || true

# Verify stopped
ps aux | grep -E "main_pipeline|uvicorn|react-scripts" | grep -v grep
```

---

### Clear Logs

```bash
for f in logs/pipeline/main_pipeline.log \
          logs/pipeline/packet_listener.log \
          logs/pipeline/zeek_feeder.log \
          logs/pipeline/zeek_parser.log \
          logs/pipeline/ml_inference.log \
          logs/pipeline/dpi_worker.log \
          logs/siem/soar_engine.log \
          logs/siem/batch_writer.log; do
    > "$f" 2>/dev/null
done

> logs/soar/camera_defense.log  2>/dev/null
> logs/soar/quarantine.log      2>/dev/null
> logs/soar/scan_detection.log  2>/dev/null

echo "Logs cleared"
```

---

## PART 6 — TROUBLESHOOTING

### Pi Not Connecting

```bash
# Can backend reach Pi?
ping -c 3 192.168.50.1
# If fails: sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de

# Is Pi's eth0 up?
ssh pi@192.168.50.1 "ip addr show eth0"
# Should have 192.168.2.106 (or whatever you configured)

# Can Pi reach backend on port 9000?
ssh pi@192.168.50.1 "nc -zv 192.168.50.21 9000"
# If fails: check BACKEND_IP in capture.sh — should be backend's IOT-LAB IP

# Is port 9000 listening on backend?
ss -tlnp | grep 9000
# If not: pipeline isn't running — check logs/pipeline/packet_listener.log
```

---

### No Alerts Generating

```bash
# 1. Pi connected?
tail -3 logs/pipeline/packet_listener.log
# Expect: "[+] Client connected"

# 2. Zeek processing?
tail -3 logs/pipeline/zeek_feeder.log
# Expect: "[+] Zeek finished on /tmp/live.pcap.snap"

# 3. conn.log being written?
ls -la services/flow_service/logs/zeek/current/conn.log

# 4. Flows being parsed?
tail -3 logs/pipeline/zeek_parser.log

# 5. ML queue filling?
python3 -c "
import sys; sys.path.insert(0,'.')
from services.flow_service.state import ML_QUEUE
print('ML_QUEUE depth:', len(ML_QUEUE))
"

# 6. Is Zeek finding correct NIC?
# Check ZEEK_INTERFACE was exported before start_pipeline.sh
echo $ZEEK_INTERFACE
```

---

### SOAR Not Triggering

```bash
# Check threshold config
python3 -c "
import json
with open('shared/config/thresholds.json') as f:
    print(json.load(f))
"
# SOAR triggers at risk >= 0.80, 3+ events in 60s

# Check recent high-risk alerts
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='fyp_security', user='postgres', password='postgres'
)
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT src_ip, risk_score, severity, timestamp
    FROM alerts
    WHERE risk_score >= 0.80
    ORDER BY timestamp DESC
    LIMIT 10
\"\"\")
for r in cur.fetchall(): print(r)
conn.close()
"

# Check playbook flags — maybe a playbook was disabled
cat logs/soar/playbook_flags.json 2>/dev/null

# Check SOAR engine log
tail -20 logs/siem/soar_engine.log
```

---

### Dashboard Not Loading

```bash
# Check API is running
curl -s http://localhost:8000/health

# Check dashboard .env
cat dashboard/.env
# REACT_APP_API_URL should match your backend IP

# react-scripts symlink broken?
ls -la dashboard/node_modules/.bin/react-scripts
# If it's empty or missing:
cd dashboard
ln -sf ../react-scripts/bin/react-scripts.js node_modules/.bin/react-scripts
chmod +x node_modules/react-scripts/bin/react-scripts.js
cd ..
```

---

### WebSocket Not Live (Dashboard Shows OFFLINE)

```bash
# Test WebSocket endpoint
curl -s http://localhost:8000/api/alerts?limit=3

# Check uvicorn log for WS connection errors
tail -20 logs/dashboard/uvicorn.log

# Verify REACT_APP_WS_URL in dashboard/.env
# Should be: ws://192.168.2.101:8000/ws  (use actual backend IP, not localhost if remote)
```

---

### ML Models Missing

```bash
ls ml/training/models/
# If rf_model.pkl, iso_model.pkl, or preprocessor.pkl missing:

source venv/bin/activate
python3 -m ml.training.dataset_preparer
python3 -m ml.training.model_training

# Or just restart the pipeline — start_pipeline.sh auto-trains at step 7.5
```

---

### Database Connection Error

```bash
# Is PostgreSQL running?
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql

# Test connection
PGPASSWORD=postgres psql -U postgres -d fyp_security -c "SELECT 1"

# If database doesn't exist
sudo -u postgres psql -c "CREATE DATABASE fyp_security;"
PGPASSWORD=postgres psql -U postgres -d fyp_security \
    -f services/siem-service/db/schema.sql
```

---

### Baseline Calibration — Too Aggressive (Missing Attacks)

If the baseline calibration layer is dampening real attack traffic:

```bash
# Check the calibration file
cat services/flow_service/core/baseline_calibration.py

# The calibration only dampens on normal flow shapes:
# - connection state: SF (normal finish)
# - duration: > 0.001s (not zero-duration)
# - bytes: > 0 in both directions
# Attack-shaped flows (S0, REJ, very short, zero bytes) are never dampened.
```

---

## PART 7 — QUICK REFERENCE

### Key Commands

| Task | Command |
|------|---------|
| Start everything | `export ZEEK_INTERFACE=eth0 && bash infrastructure/scripts/start_pipeline.sh` |
| Stop everything | `bash infrastructure/scripts/stop_pipeline.sh` |
| Reset firewall | `bash infrastructure/scripts/reset_firewall.sh` |
| Check API health | `curl -s http://localhost:8000/health` |
| Tail pipeline log | `tail -f logs/pipeline/main_pipeline.log` |
| Tail SOAR log | `tail -f logs/siem/soar_engine.log` |
| Clear DB (CLI) | see Part 5 Python snippet |
| Retrain models | `python3 -m ml.training.model_training` |

---

### Key File Locations

| File | Purpose |
|------|---------|
| `shared/config/system_config.yaml` | All device IPs — single source of truth |
| `shared/config/thresholds.json` | Risk thresholds + SOAR trigger config |
| `shared/utils/config_loader.py` | Loads config for all services |
| `ml/training/models/rf_model.pkl` | Random Forest model |
| `ml/training/models/iso_model.pkl` | Isolation Forest model |
| `ml/training/models/preprocessor.pkl` | Feature preprocessor |
| `ml/datasets/fp_dataset.csv` | FP feedback export (analyst-confirmed false positives) |
| `services/flow_service/core/baseline_calibration.py` | IoT FP reduction layer |
| `infrastructure/scripts/start_pipeline.sh` | Master startup (only way to start) |
| `infrastructure/scripts/reset_firewall.sh` | Remove all SOAR firewall rules |
| `logs/soar/playbook_flags.json` | Runtime playbook enable/disable state |
| `dashboard/.env` | Dashboard backend URL config |

---

### Key Ports

| Port | Service |
|------|---------|
| 3000 | React Dashboard |
| 8000 | FastAPI (REST + WebSocket) |
| 9000 | Pi PCAP TCP stream receiver |
| 9091 | Prometheus metrics |
| 5432 | PostgreSQL |

---

### Severity → Action Mapping

| Severity | Risk Score | Auto Action |
|----------|-----------|-------------|
| CRITICAL | ≥ 0.80 | SOAR playbook eligible (if 3+ events in 60s) |
| HIGH | ≥ 0.60 | Alert + toast notification |
| MEDIUM | ≥ 0.35 | Alert logged + dashboard |
| LOW | < 0.35 | Log only |

---

### SOAR Playbook Reference

| Playbook | Trigger Condition | Firewall Action | Revert |
|----------|-------------------|-----------------|--------|
| `block_attacker` | CRITICAL from external IP | `ufw deny from <ip>` | Dashboard UNBLOCK button |
| `camera_defense` | Any attack targeting camera IP | `iptables` rate-limit | `reset_firewall.sh` |
| `quarantine_device` | CRITICAL sourced from IoT device | `iptables FORWARD DROP` | Dashboard RELEASE button |
| `scan_detection` | 20+ unique ports in 30s | `iptables` throttle | `reset_firewall.sh` |

All playbooks can be toggled on/off live from the dashboard SOAR Panel.

---

## PART 8 — SESSION CHECKLIST

```
PRE-SESSION:
[ ] shared/config/system_config.yaml — IPs are correct
[ ] dashboard/.env — REACT_APP_API_URL and WS_URL are correct
[ ] IOT-LAB WiFi connected on backend PC
[ ] sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de
[ ] ping 192.168.50.1 — Pi reachable

STARTUP:
[ ] bash infrastructure/scripts/stop_pipeline.sh     (clear any previous run)
[ ] bash infrastructure/scripts/reset_firewall.sh    (clean firewall state)
[ ] export ZEEK_INTERFACE=<your_nic>
[ ] bash infrastructure/scripts/start_pipeline.sh
[ ] curl http://localhost:8000/health  →  {"status":"ok"}
[ ] tail logs/pipeline/main_pipeline.log  →  "[✔] All 7 threads launched"
[ ] ss -tlnp | grep 9000  →  LISTEN
[ ] cd dashboard && npm start

PI:
[ ] ssh pi@192.168.50.1
[ ] bash ~/edge/capture/capture.sh
[ ] tail logs/pipeline/packet_listener.log  →  "Client connected"
[ ] Dashboard header  →  LIVE

TRAFFIC VERIFICATION:
[ ] tail logs/pipeline/zeek_feeder.log  →  "Zeek finished"
[ ] Alerts appearing in Live Alert Feed
[ ] Devices Panel shows camera + BYOD

ATTACK TEST:
[ ] bash infrastructure/scripts/reset_firewall.sh
[ ] Run attack (hping3 / nmap)
[ ] Wait 60s → SOAR trigger in logs/siem/soar_engine.log
[ ] Verify firewall rule: sudo ufw status | grep DENY

POST-SESSION:
[ ] bash infrastructure/scripts/reset_firewall.sh
[ ] bash infrastructure/scripts/stop_pipeline.sh
[ ] Verify: ps aux | grep -E "main_pipeline|uvicorn" | grep -v grep  →  nothing
```

---

*IoT IDS FYP — Operations Runbook | Last updated: August 2026*
