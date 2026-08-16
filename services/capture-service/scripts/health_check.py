# services/capture-service/scripts/health_check.py

import socket
import threading
import time
import logging
import os
import yaml
from queue_writer import global_queue

# ---------------------------
# Setup logging
# ---------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "../logs/health_check.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---------------------------
# Load config
# ---------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../configs/capture_settings.yaml")
with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

HOST = cfg.get("backend", {}).get("host", "0.0.0.0")
PORT = cfg.get("backend", {}).get("port", 9000)
CHECK_INTERVAL = 10  # seconds

# ---------------------------
# Health check function
# ---------------------------
def check_backend_listener():
    """
    Check if TCP listener is alive on configured port.
    Logs success or failure.
    """
    while True:
        try:
            with socket.create_connection((HOST, PORT), timeout=5) as s:
                logging.info(f"Backend listener is UP at {HOST}:{PORT}")
        except Exception as e:
            logging.error(f"Backend listener DOWN at {HOST}:{PORT} -> {e}")
        # Phase 3 extension: log queue size
        try:
            qsize = global_queue.size()
            logging.info(f"Queue size: {qsize} items")
        except Exception as e:
            logging.error(f"Queue check failed: {e}")
        time.sleep(CHECK_INTERVAL)

# ---------------------------
# Threaded entry point
# ---------------------------
def start_health_monitor():
    t = threading.Thread(target=check_backend_listener, daemon=True)
    t.start()
    logging.info("Health monitor thread started.")
    return t

# ---------------------------
# Run standalone (for testing)
# ---------------------------
if __name__ == "__main__":
    logging.info("Starting standalone health_check.py")
    start_health_monitor()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Health check stopped by user.")
