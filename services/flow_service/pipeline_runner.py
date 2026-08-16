"""
Pipeline Runner — Phase 3 (monitor dashboard only)
This is the LIGHTWEIGHT runner used during development/testing.
For production use main_pipeline.py via start_pipeline.sh.
"""

import threading
import logging
import time
import os
import sys
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.flow_service.packet_listener import packet_listener
from services.flow_service.zeek_feeder import zeek_feeder
from services.flow_service.zeek_parser import zeek_parser_loop
from services.flow_service.monitor import PipelineMonitor, start_dashboard
from services.flow_service.core.bridge import FlowBridge
from services.flow_service.state import ML_QUEUE
from services.flow_service.configs.config import ensure_dirs

ensure_dirs()
os.makedirs("logs/pipeline", exist_ok=True)

_h = RotatingFileHandler("logs/pipeline/pipeline_runner.log", maxBytes=5*1024*1024, backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger("pipeline_runner")
logger.addHandler(_h)
logger.setLevel(logging.INFO)


def ml_worker(bridge):
    logger.info("[*] ML Worker started")
    while True:
        try:
            if len(ML_QUEUE) > 0:
                flow   = ML_QUEUE.popleft()
                event  = bridge.process(flow)
                result = event["result"]
                print(f"\n[DETECTION] status={result['status']} rf={result['rf']} iso={result['iso']} proba={result.get('rf_proba', '?'):.3f}")
                print("-" * 50)
            else:
                time.sleep(0.2)
        except Exception as e:
            logger.error(f"[!] ML Worker error: {e}")
            time.sleep(1)


def start_thread(target_fn, name, *args):
    def wrapper():
        logger.info(f"[*] {name} started")
        try:
            target_fn(*args)
        except Exception as e:
            logger.error(f"[!] {name} crashed: {e}")
        finally:
            logger.warning(f"[!] {name} stopped")
    t = threading.Thread(target=wrapper, daemon=True, name=name)
    t.start()
    return t


def main():
    logger.info("Starting Pipeline Runner (dev mode)")
    monitor = PipelineMonitor()
    bridge  = FlowBridge()

    threads = [
        start_thread(packet_listener,  "T1-packet_listener"),
        start_thread(zeek_feeder,      "T2-zeek_feeder"),
        start_thread(zeek_parser_loop, "T3-zeek_parser"),
        start_thread(ml_worker,        "T4-ml_worker", bridge),
    ]

    monitor.threads = {t.name: t for t in threads}

    threading.Thread(target=start_dashboard, args=(monitor,), daemon=True).start()

    logger.info("[+] All pipeline components started")

    try:
        while True:
            time.sleep(2)
            for t in threads:
                if not t.is_alive():
                    logger.error(f"[!] {t.name} died")
    except KeyboardInterrupt:
        logger.info("[*] Shutdown")


if __name__ == "__main__":
    main()
