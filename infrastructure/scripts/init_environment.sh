#!/bin/bash
# ============================================================
# Phase 0 — Environment Setup Script
# Run ONCE on fresh Linux backend before anything else
# ============================================================

set -e

echo "============================================================"
echo "  IoT IDS — Environment Init (Phase 0)"
echo "============================================================"

# Step 0.1 — System packages
echo "[0.1] Installing system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3-pip git \
    postgresql postgresql-contrib \
    suricata zeek \
    tcpdump netcat-openbsd \
    prometheus grafana \
    curl wget

# Step 0.1a — Node.js (GAP 1 FIX)
echo "[0.1a] Installing Node.js..."
sudo apt install -y nodejs npm
node -v && npm -v
echo "    [✔] Node.js ready"

# Step 0.1b — Python packages
echo "[0.1b] Installing Python packages..."
pip3 install -r "$(cd "$(dirname "$0")/../.." && pwd)/requirements.txt"
echo "    [✔] Python packages installed"

# Step 0.2 — node_exporter (Phase 8 GAP 2 FIX)
echo "[0.2] Installing node_exporter..."
NODE_EXP_VER="1.7.0"
NODE_EXP_URL="https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXP_VER}/node_exporter-${NODE_EXP_VER}.linux-amd64.tar.gz"

cd /tmp
wget -q "$NODE_EXP_URL" -O node_exporter.tar.gz
tar xzf node_exporter.tar.gz
sudo mv "node_exporter-${NODE_EXP_VER}.linux-amd64/node_exporter" /usr/local/bin/
rm -rf node_exporter.tar.gz "node_exporter-${NODE_EXP_VER}.linux-amd64"

# Create systemd service for node_exporter
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
User=nobody
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
sleep 2
curl -s localhost:9100/metrics | grep "node_cpu" | head -3
echo "    [✔] node_exporter running on :9100"

# Step 0.3 — Suricata rules update
echo "[0.3] Updating Suricata rules..."
sudo suricata-update 2>/dev/null || echo "    [!] suricata-update failed — run manually"

# Step 0.4 — Folder structure
echo "[0.4] Creating folder structure..."
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$PROJECT_ROOT/logs"/{pipeline,zeek,dashboard,siem,dpi,ml,monitoring}
mkdir -p "$PROJECT_ROOT/services/flow_service/logs/zeek/current"
mkdir -p "$PROJECT_ROOT/ml/datasets/feedback"
mkdir -p "$PROJECT_ROOT/ml/models"/{backups,isolation_forest,random_forest,scaler}
echo "    [✔] Folders created"

echo ""
echo "============================================================"
echo "  [✔] Environment ready"
echo "  Next: download datasets, then run start_pipeline.sh"
echo "============================================================"
