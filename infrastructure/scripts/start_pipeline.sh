#!/bin/bash
# ============================================================
# IoT IDS — Master Startup Script (Phase 10)
# THE ONLY WAY TO START THE SYSTEM
#
# Usage from project root:
#   bash infrastructure/scripts/start_pipeline.sh
#
# Required env vars (set before running, or edit defaults below):
#   ZEEK_INTERFACE   — your backend NIC, e.g. eth0, ens3, enp3s0
#   ZEEK_BINARY      — path to zeek binary (default: /opt/zeek/bin/zeek)
#   DB_PASS          — PostgreSQL password (default: postgres)
# ============================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# ---- configurable defaults ----
ZEEK_INTERFACE="${ZEEK_INTERFACE:-wlxe009bf6913de}"
ZEEK_BINARY="${ZEEK_BINARY:-/opt/zeek/bin/zeek}"
DB_PASS="${DB_PASS:-postgres}"

# Zeek will write conn.log here — parser reads from same path
ZEEK_LOG_DIR="$PROJECT_ROOT/services/flow_service/logs/zeek/current"
mkdir -p "$ZEEK_LOG_DIR"
mkdir -p "$PROJECT_ROOT/logs/pipeline"
mkdir -p "$PROJECT_ROOT/logs/dashboard"
mkdir -p "$PROJECT_ROOT/logs/siem"
mkdir -p "$PROJECT_ROOT/logs/dpi"

echo ""
echo "============================================================"
echo "  IoT IDS Pipeline — Starting"
echo "  Project root   : $PROJECT_ROOT"
echo "  Zeek interface : $ZEEK_INTERFACE"
echo "  Zeek log dir   : $ZEEK_LOG_DIR"
echo "============================================================"

# ----------------------------------------------------------
# 1. Kernel tuning
# ----------------------------------------------------------
echo "[1/8] Kernel buffer tuning..."
sudo sysctl -w net.core.rmem_max=33554432       2>/dev/null || true
sudo sysctl -w net.core.netdev_max_backlog=5000  2>/dev/null || true
echo "    [✔] Done"

# ----------------------------------------------------------
# 1.5 Reset SOAR firewall rules (clean slate for new session)
# ----------------------------------------------------------
echo "[*] Resetting SOAR firewall rules from previous session..."
bash "$PROJECT_ROOT/infrastructure/scripts/reset_firewall.sh" 2>/dev/null || true
echo "    [✔] Firewall clean"

# ----------------------------------------------------------
# 2. PostgreSQL
# ----------------------------------------------------------
echo "[2/8] Starting PostgreSQL..."
sudo systemctl start postgresql 2>/dev/null || true
sleep 1

# create DB if not exists
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='fyp_security'" \
    | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE fyp_security;" 2>/dev/null

# apply schema (idempotent — uses IF NOT EXISTS)
PGPASSWORD="$DB_PASS" psql -U postgres -d fyp_security \
    -f "$PROJECT_ROOT/services/siem-service/db/schema.sql" 2>/dev/null || true

echo "    [✔] PostgreSQL ready"

# ----------------------------------------------------------
# 3. Zeek — NOT started here in pcap mode
# zeek_feeder.py (T2) drains QUEUE_1 → /tmp/live.pcap and
# spawns short-lived `zeek -r` runs itself.  Running `zeek -i`
# here would create a second Zeek process racing on conn.log.
# ----------------------------------------------------------
echo "[3/8] Zeek launch skipped (pcap mode — zeek_feeder.py manages Zeek)..."
sudo pkill -f "zeek -i" 2>/dev/null || true   # kill any stale live-mode Zeek
rm -f /tmp/zeek_live.pid
echo "    [✔] Any stale zeek -i process cleared"

# ----------------------------------------------------------
# 4. Suricata
# ----------------------------------------------------------
echo "[4/8] Starting Suricata..."
sudo systemctl start suricata 2>/dev/null \
    || sudo suricata -D -c /etc/suricata/suricata.yaml \
         --set "outputs.1.eve-log.filename=/var/log/suricata/eve.json" \
         2>/dev/null \
    || echo "    [!] Suricata not available — DPI will return empty alerts"
echo "    [✔] Suricata step done"

# ----------------------------------------------------------
# 5. fp_dataset.csv init (GAP 4 FIX)
# ----------------------------------------------------------
echo "[5/8] Initializing fp_dataset.csv..."
FP_PATH="$PROJECT_ROOT/ml/datasets/fp_dataset.csv"
if [ ! -f "$FP_PATH" ]; then
    echo "duration,packet_count,byte_count,avg_pkt_size,flow_rate,dst_port,protocol,conn_state,dns_query_count,label" \
        > "$FP_PATH"
    echo "    [✔] fp_dataset.csv created"
else
    echo "    [✔] fp_dataset.csv already exists"
fi

# ----------------------------------------------------------
# 6. Export env vars for Python processes
# ----------------------------------------------------------
echo "[6/8] Setting environment..."
export ZEEK_LOG_DIR="$ZEEK_LOG_DIR"
export ZEEK_BINARY="$ZEEK_BINARY"
export ZEEK_MODE="pcap"
export LIVE_PCAP="/tmp/live.pcap"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="fyp_security"
export DB_USER="postgres"
export DB_PASS="$DB_PASS"
export FP_DATASET_PATH="$FP_PATH"
export INTERNAL_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export PYTHONPATH="$PROJECT_ROOT"
echo "    [✔] ZEEK_LOG_DIR=$ZEEK_LOG_DIR"
echo "    [✔] PYTHONPATH=$PROJECT_ROOT"

# ----------------------------------------------------------
# 7.5. ML models — train if not present
# ----------------------------------------------------------
echo "[7.5/8] Checking ML models..."
if [ ! -f "$PROJECT_ROOT/ml/training/models/rf_model.pkl" ]; then
    echo "    [!] Models not found — training now (takes ~60s)..."
    python3 "$PROJECT_ROOT/ml/training/model_training.py"
    echo "    [✔] Models trained"
else
    echo "    [✔] Models exist"
fi

# ----------------------------------------------------------
# 7. FastAPI API service
# ----------------------------------------------------------
echo "[7/8] Starting FastAPI API service on :8000..."
nohup python3 "$PROJECT_ROOT/services/api-service/run_api.py" \
    > "$PROJECT_ROOT/logs/dashboard/uvicorn.log" 2>&1 &
echo $! > /tmp/iot_ids_api.pid
sleep 1
echo "    [✔] API service started (PID=$(cat /tmp/iot_ids_api.pid))"

# ----------------------------------------------------------
# 8. Main pipeline (7 threads)
# ----------------------------------------------------------
echo "[8/8] Starting main pipeline..."
nohup python3 "$PROJECT_ROOT/services/flow_service/main_pipeline.py" \
    > "$PROJECT_ROOT/logs/pipeline/main_pipeline_stdout.log" 2>&1 &
echo $! > /tmp/iot_ids_pipeline.pid
sleep 2
echo "    [✔] Pipeline started (PID=$(cat /tmp/iot_ids_pipeline.pid))"

# ----------------------------------------------------------
# Done
# ----------------------------------------------------------
echo ""
echo "============================================================"
echo "  [✔] IoT IDS System Running"
echo ""
echo "  API          : http://localhost:8000"
echo "  API docs     : http://localhost:8000/docs"
echo "  Metrics      : http://localhost:9090/metrics"
echo "  Dashboard    : http://localhost:3000  (run: cd dashboard && npm start)"
echo "  Grafana      : http://localhost:3001"
echo ""
echo "  Zeek logs    : $ZEEK_LOG_DIR"
echo "  Pipeline log : $PROJECT_ROOT/logs/pipeline/main_pipeline.log"
echo "  API log      : $PROJECT_ROOT/logs/dashboard/uvicorn.log"
echo ""
echo "  Stop         : bash infrastructure/scripts/stop_pipeline.sh"
echo "============================================================"
echo ""
echo "  [!] VERIFY THESE ON YOUR BACKEND PC:"
echo "      ZEEK_INTERFACE = $ZEEK_INTERFACE"
echo "      Run: ip link show   to find your NIC name"
echo "      Then: export ZEEK_INTERFACE=<your_nic> && bash infrastructure/scripts/start_pipeline.sh"
echo ""
