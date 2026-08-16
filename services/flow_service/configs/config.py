"""
Flow Service Config
All paths are absolute — safe to run from any working directory.
"""

import os

# ---------------------------
# Network — packet_listener
# ---------------------------
HOST        = "0.0.0.0"
PORT        = 9000
BUFFER_SIZE = 65536

# ---------------------------
# Queue
# ---------------------------
QUEUE_MAXLEN = 50000

# ---------------------------
# Base paths
# ---------------------------
# This file lives at: <project_root>/services/flow_service/configs/config.py
# So BASE_DIR = <project_root>/services/flow_service
# PROJECT_ROOT = <project_root>
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

LOGS_DIR         = os.path.join(BASE_DIR, "logs")
PIPELINE_LOG_DIR = os.path.join(LOGS_DIR, "pipeline")

# ---------------------------
# Zeek
# ---------------------------
# Update ZEEK_BINARY if Zeek is installed elsewhere (e.g. /usr/bin/zeek)
ZEEK_BINARY = os.getenv("ZEEK_BINARY", "/opt/zeek/bin/zeek")

# ZEEK_MODE: "live" = Zeek runs on interface (started by start_pipeline.sh)
#            "pcap" = pipeline writes /tmp/live.pcap and runs Zeek -r
ZEEK_MODE = os.getenv("ZEEK_MODE", "live")

# Where Zeek writes its logs when running in PCAP mode (-r)
ZEEK_OUTPUT_DIR = os.path.join(LOGS_DIR, "zeek", "current")

# Where Zeek writes conn.log in LIVE mode (-i interface)
# Zeek -i writes to its CWD or /opt/zeek/logs/current/ depending on install
# Set ZEEK_LOG_DIR env var to override — check with: zeekctl status
ZEEK_LOG_DIR = os.getenv(
    "ZEEK_LOG_DIR",
    os.path.join(LOGS_DIR, "zeek", "current")   # default: same as pcap output
)

CONN_LOG_PATH = os.path.join(ZEEK_LOG_DIR, "conn.log")

LIVE_PCAP        = os.getenv("LIVE_PCAP", "/tmp/live.pcap")
ZEEK_RUN_INTERVAL = 2   # seconds between Zeek runs in pcap mode

# ---------------------------
# Parser
# ---------------------------
PARSER_INTERVAL = 0.3   # seconds between conn.log reads

# ---------------------------
# Logging format
# ---------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s | %(message)s"
LOG_LEVEL  = "INFO"

# ---------------------------
# Create required dirs on import
# ---------------------------
def ensure_dirs():
    os.makedirs(ZEEK_OUTPUT_DIR, exist_ok=True)
    os.makedirs(PIPELINE_LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(LOGS_DIR, "zeek", "current"), exist_ok=True)

ensure_dirs()
