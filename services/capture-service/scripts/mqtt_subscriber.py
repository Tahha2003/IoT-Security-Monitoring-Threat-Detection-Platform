# services/capture-service/scripts/mqtt_subscriber.py

"""
Phase 2 placeholder for MQTT subscriber.
This file is not used in Phase 2, but aligns with folder architecture.
Phase 3: will subscribe to MQTT topics and forward messages to queue or ingestion pipeline.
"""

import logging
import os
import yaml

# ---------------------------
# Setup logging
# ---------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "../logs/mqtt_messages.log")
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

MQTT_ENABLED = cfg.get("mqtt", {}).get("enabled", False)

# ---------------------------
# Phase 2 placeholder function
# ---------------------------
def start_mqtt_subscriber():
    if not MQTT_ENABLED:
        logging.info("Phase 2: MQTT subscriber disabled (placeholder).")
        return
    logging.info("Phase 2 placeholder: MQTT subscriber started (no real subscription).")

# ---------------------------
# Run standalone
# ---------------------------
if __name__ == "__main__":
    logging.info("Running mqtt_subscriber.py in Phase 2 placeholder mode")
    start_mqtt_subscriber()
