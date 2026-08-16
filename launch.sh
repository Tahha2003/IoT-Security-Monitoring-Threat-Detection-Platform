#!/bin/bash
# ============================================================
# IoT IDS — One-Shot Launcher
# Double-click this file OR run:  bash launch.sh
#
# Starts ONLY what needs a terminal:
#   1. FastAPI backend (if not already running)
#   2. React dashboard (npm start)
#
# The "Start Pipeline" button inside the dashboard handles
# everything else (Zeek, PostgreSQL, ML pipeline, Suricata).
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║    IoT Threat Detection System       ║"
echo "  ║    Starting Dashboard...             ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── Step 1: Start FastAPI if not running ────────────────────────────────────
if [ -f /tmp/iot_ids_api.pid ] && kill -0 "$(cat /tmp/iot_ids_api.pid)" 2>/dev/null; then
    echo "  [✔] API already running (PID=$(cat /tmp/iot_ids_api.pid))"
else
    echo "  [>] Starting FastAPI backend on :8000 ..."
    export PYTHONPATH="$PROJECT_ROOT"
    export DB_HOST="localhost"
    export DB_PORT="5432"
    export DB_NAME="fyp_security"
    export DB_USER="postgres"
    export DB_PASS="${DB_PASS:-postgres}"
    export INTERNAL_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    nohup python3 "$PROJECT_ROOT/services/api-service/run_api.py" \
        > "$PROJECT_ROOT/logs/dashboard/uvicorn.log" 2>&1 &
    echo $! > /tmp/iot_ids_api.pid
    sleep 2
    if kill -0 "$(cat /tmp/iot_ids_api.pid)" 2>/dev/null; then
        echo "  [✔] API started (PID=$(cat /tmp/iot_ids_api.pid))"
    else
        echo "  [!] API failed to start — check logs/dashboard/uvicorn.log"
    fi
fi

# ── Step 2: Start React dashboard ───────────────────────────────────────────
echo "  [>] Starting React dashboard..."
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  Dashboard : http://localhost:3000           │"
echo "  │  API       : http://localhost:8000           │"
echo "  │                                              │"
echo "  │  Use the 'System Control' panel inside the  │"
echo "  │  dashboard to Start/Stop the pipeline.      │"
echo "  │                                              │"
echo "  │  Press Ctrl+C to stop the dashboard.        │"
echo "  └─────────────────────────────────────────────┘"
echo ""

mkdir -p "$PROJECT_ROOT/logs/dashboard"
cd "$PROJECT_ROOT/dashboard"
npm start
