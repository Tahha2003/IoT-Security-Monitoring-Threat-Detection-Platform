#!/bin/bash
# ============================================================
# IoT IDS — Stop Script
# ============================================================

echo "[*] Stopping IoT IDS Pipeline..."

# Kill pipeline
if [ -f /tmp/iot_ids_pipeline.pid ]; then
    kill "$(cat /tmp/iot_ids_pipeline.pid)" 2>/dev/null && echo "[✔] Pipeline stopped"
    rm -f /tmp/iot_ids_pipeline.pid
fi

# Kill API service
if [ -f /tmp/iot_ids_api.pid ]; then
    kill "$(cat /tmp/iot_ids_api.pid)" 2>/dev/null && echo "[✔] API service stopped"
    rm -f /tmp/iot_ids_api.pid
fi

# Stop Suricata
sudo systemctl stop suricata 2>/dev/null || true

echo "[✔] Done"
