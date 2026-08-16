# services/capture-service/scripts/sensor_ingest.py

import threading
import time
import os
import logging
from queue_writer import global_queue

# ---------------------------
# Setup logging
# ---------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "../logs/sensor_ingest.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---------------------------
# Phase 2: placeholder consumer
# ---------------------------
def ingest_loop(poll_interval=1.0):
    """
    Phase 2: loop that checks queue, discards bytes, logs activity.
    Phase 3: real processing will go here.
    """
    logging.info("Sensor ingest loop started (Phase 2 placeholder).")
    while True:
        try:
            queue_size = global_queue.size()
            if queue_size > 0:
                item = global_queue.pop()
                if item:
                    logging.info(f"Phase 2 ingest: received {len(item)} bytes (discarded).")
            time.sleep(poll_interval)
        except Exception as e:
            logging.error(f"Ingest loop error: {e}")
            time.sleep(2)  # backoff on error

# ---------------------------
# Threaded entry point
# ---------------------------
def start_sensor_ingest():
    t = threading.Thread(target=ingest_loop, daemon=True)
    t.start()
    logging.info("Sensor ingest thread started.")
    return t

# ---------------------------
# Run standalone (for testing)
# ---------------------------
if __name__ == "__main__":
    logging.info("Starting standalone sensor_ingest.py (Phase 2).")
    start_sensor_ingest()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Sensor ingest stopped by user.")
