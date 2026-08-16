# services/capture-service/scripts/queue_writer.py

import threading
import logging
import os
from datetime import datetime

# ---------------------------
# Setup logging
# ---------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "../logs/queue_writer.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---------------------------
# Thread-safe placeholder queue
# ---------------------------
class PhaseQueue:
    def __init__(self):
        self.lock = threading.Lock()
        self.queue = []  # Phase 2: we discard items, Phase 3 will use

    def push(self, item):
        with self.lock:
            # Phase 2: do not store, just log
            logging.info(f"Phase 2 placeholder: received item of size {len(item)} bytes (discarded).")
            # Phase 3: append to self.queue for real ingestion

    def pop(self):
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None

    def size(self):
        with self.lock:
            return len(self.queue)

# ---------------------------
# Singleton queue instance
# ---------------------------
global_queue = PhaseQueue()

# ---------------------------
# Utility functions
# ---------------------------
def push_to_queue(item: bytes):
    """Safe entry point for scripts to push data to queue."""
    global_queue.push(item)

def get_queue_size():
    return global_queue.size()
