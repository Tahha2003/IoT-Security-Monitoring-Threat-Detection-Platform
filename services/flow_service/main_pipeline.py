"""
Main Pipeline — Phase 10
7-thread hardened pipeline with adaptive backpressure.
Start ONLY via start_pipeline.sh — never run directly.
"""

import threading
import logging
import time
import os
import sys
import requests
from logging.handlers import RotatingFileHandler
from collections import deque

# ---------------------------
# Path setup
# ---------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# ZEEK_MODE is set by start_pipeline.sh — do NOT override it here.
# live  = Zeek runs on interface (default, low latency)
# pcap  = Zeek runs on pcap file batches (testing/offline)
os.environ.setdefault("LIVE_PCAP", "/tmp/live.pcap")
# ---------------------------
# Logging
# ---------------------------
os.makedirs("logs/pipeline", exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = RotatingFileHandler(
            f"logs/pipeline/{name}.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger

logger = get_logger("main_pipeline")

# ---------------------------
# Imports (after path setup)
# ---------------------------
from services.flow_service.state import QUEUE_1, ML_QUEUE, RESULT_QUEUE, SYSTEM_STATE
from services.flow_service.packet_listener import packet_listener
from services.flow_service.zeek_feeder import zeek_feeder
from services.flow_service.zeek_parser import zeek_parser_loop
from services.flow_service.core.bridge import FlowBridge
from services.flow_service.core.risk_scorer import score as risk_score

# Load known IoT devices from shared config — no hardcoded IPs in pipeline
try:
    import yaml as _yaml
    with open(os.path.join(PROJECT_ROOT, "shared", "config", "system_config.yaml")) as _f:
        _sys_cfg = _yaml.safe_load(_f)
    IOT_DEVICES: set = set(_sys_cfg.get("network", {}).get("iot_devices", []))
except Exception:
    IOT_DEVICES = set()  # safe fallback — all devices treated as non-IoT

# DPI engine — hyphenated folder, use importlib
import importlib.util, pathlib

def _load_module(rel_path, name):
    p = pathlib.Path(PROJECT_ROOT) / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {name} from {p}")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_dpi    = _load_module("services/dpi-service/parser/dpi_engine.py",       "dpi_engine")
_soar   = _load_module("services/soar-service/engine/soar_engine.py",     "soar_engine")
_siem   = _load_module("services/siem-service/writer/batch_writer.py",    "batch_writer")

run_dpi       = _dpi.run_dpi
soar_evaluate = _soar.evaluate
queue_alert   = _siem.queue_alert
batch_loop    = _siem.batch_loop

from infrastructure.monitoring.metrics import (
    update_queue_depth, update_inference_ms,
    update_packet_loss, inc_alerts, update_backpressure,
    start_metrics_server
)

# ---------------------------
# Backpressure thresholds
# ---------------------------
BP_FULL      = 300
BP_SAMPLE_50 = 800
BP_SAMPLE_33 = 2000

_flow_counter = 0


def should_process(src_ip: str) -> bool:
    """3-mode adaptive backpressure."""
    global _flow_counter
    _flow_counter += 1
    qsize = len(ML_QUEUE)

    if qsize < BP_FULL:
        update_backpressure(0)
        return True
    elif qsize < BP_SAMPLE_50:
        update_backpressure(1)
        return _flow_counter % 2 == 0
    elif qsize < BP_SAMPLE_33:
        update_backpressure(2)
        return _flow_counter % 3 == 0
    else:
        update_backpressure(3)
        # NEW_ONLY — only unseen IPs (simple heuristic: odd counter)
        return _flow_counter % 7 == 0


# ---------------------------
# T3 — ML Inference worker
# ---------------------------
def ml_inference_worker(bridge: FlowBridge):
    log = get_logger("ml_inference")
    log.info("[T3] ML inference worker started")

    while True:
        try:
            flow = ML_QUEUE.popleft()
            if flow is not None:

                src_ip = flow.get("src_ip", "0.0.0.0")

                if not should_process(src_ip):
                    continue

                import time as _time
                t0 = _time.perf_counter()
                event = bridge.process(flow)
                if event is None:
                    continue
                latency_ms = (_time.perf_counter() - t0) * 1000

                update_inference_ms(latency_ms)

                ml_result  = event["result"]   # {label, status, rf, iso, rf_proba}
                rf_proba   = float(ml_result.get("rf_proba", ml_result.get("rf", 0)))
                is_anomaly = ml_result.get("iso", 1) == -1
                # send to DPI if RF probability > 30% OR Isolation Forest flagged it
                send_to_dpi = rf_proba > 0.30 or is_anomaly

                RESULT_QUEUE.put({
                    "flow":        flow,
                    "ml_result":   ml_result,
                    "send_to_dpi": send_to_dpi,
                }, timeout=0.1)

            else:
                time.sleep(0.05)

        except Exception as e:
            log.error(f"[T3] error: {e}")
            time.sleep(0.1)


# ---------------------------
# T4 — Selective DPI worker
# ---------------------------
def dpi_worker():
    log = get_logger("dpi_worker")
    log.info("[T4] DPI worker started")

    while True:
        try:
            item = RESULT_QUEUE.get(timeout=1)
            if item is None:
                continue

            if not item.get("send_to_dpi"):
                # pass straight to alert builder
                _build_and_queue_alert(item, dpi_alerts=[])
                continue

            # run DPI on flagged flow
            raw_packets = item["flow"].get("raw_packets", b"")
            dpi_alerts  = run_dpi(raw_packets)

            log.info(f"[T4] DPI alerts: {len(dpi_alerts)}")
            _build_and_queue_alert(item, dpi_alerts)

        except Exception as e:
            if "Empty" not in str(type(e).__name__):
                log.error(f"[T4] error: {e}")


def _build_and_queue_alert(item: dict, dpi_alerts: list):
    """Build final alert dict and push to SIEM + WS broadcast.
    Only stores actual attacks (rf=1 or iso=-1) — filters out NORMAL traffic.
    """
    flow      = item["flow"]
    ml_result = item["ml_result"]

    src_ip = flow.get("src_ip", "0.0.0.0")
    scored = risk_score(src_ip, ml_result, dpi_alerts)

    # ── Filter: skip only pure NORMAL (rf=0 AND iso=1, no DPI) ───────────
    # Store everything ML flagged — including LOW severity attacks
    # Also always store traffic from IoT devices (camera + BYOD) for monitoring
    rf_label = int(ml_result.get("rf", 0))
    iso_pred = int(ml_result.get("iso", 1))
    src_ip   = flow.get("src_ip", "")

    is_iot = src_ip in IOT_DEVICES

    if not is_iot and rf_label == 0 and iso_pred == 1 and not dpi_alerts:
        return   # truly normal non-IoT traffic — skip
    # ──────────────────────────────────────────────────────────────────────

    # byte_count: prefer orig_ip_bytes+resp_ip_bytes (always set by Zeek)
    # fallback to orig_bytes+resp_bytes
    byte_count = (
        flow.get("orig_ip_bytes", 0) + flow.get("resp_ip_bytes", 0)
        or flow.get("orig_bytes", 0) + flow.get("resp_bytes", 0)
    )

    alert = {
        "timestamp":    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "src_ip":       src_ip,
        "dst_ip":       flow.get("dst_ip", "0.0.0.0"),
        "dst_port":     flow.get("dst_port", 0),
        "protocol":     flow.get("proto", "-"),
        "risk_score":   scored["risk_score"],
        "severity":     scored["severity"],
        "attack_type":  scored["attack_type"],
        "packet_count": flow.get("orig_pkts", 0) + flow.get("resp_pkts", 0),
        "byte_count":   byte_count,
    }

    # SIEM batch write
    queue_alert(alert)
    inc_alerts()

    # SOAR evaluation — pass full alert for playbook routing
    soar_result = soar_evaluate(src_ip, scored["risk_score"], alert)
    if soar_result == "TRIGGER":
        logger.warning(f"[SOAR] TRIGGER for {src_ip}")

    # WS broadcast (fire-and-forget via requests to avoid async complexity)
    try:
        requests.post(
            "http://localhost:8000/internal/broadcast",
            json=alert,
            headers={"x-internal-token": os.getenv("INTERNAL_TOKEN", "changeme-set-this-in-env")},
            timeout=0.2
        )
    except Exception:
        pass  # dashboard not critical for pipeline


# ---------------------------
# T7 — Metrics updater
# ---------------------------
def metrics_worker():
    log = get_logger("metrics_worker")
    log.info("[T7] Metrics worker started")

    while True:
        try:
            update_queue_depth(len(ML_QUEUE))
            time.sleep(1)
        except Exception as e:
            log.error(f"[T7] error: {e}")
            time.sleep(1)


# ---------------------------
# Thread launcher
# ---------------------------
def start_thread(fn, name, *args):
    def wrapper():
        logger.info(f"[*] {name} starting")
        try:
            fn(*args)
        except Exception as e:
            logger.error(f"[!] {name} crashed: {e}")

    t = threading.Thread(target=wrapper, daemon=True, name=name)
    t.start()
    logger.info(f"[+] {name} started")
    return t


# ---------------------------
# MAIN
# ---------------------------
def main():
    logger.info("=" * 60)
    logger.info("IoT IDS Main Pipeline Starting")
    logger.info("=" * 60)

    # Start Prometheus metrics server
    start_metrics_server(9091)

    bridge = FlowBridge()

    threads = [
        start_thread(packet_listener,      "T1-ingestion"),
        start_thread(zeek_feeder,          "T2-zeek_feeder"),
        start_thread(zeek_parser_loop,     "T3-zeek_parser"),
        start_thread(ml_inference_worker,  "T4-ml_inference", bridge),
        start_thread(dpi_worker,           "T5-dpi_worker"),
        start_thread(batch_loop,           "T6-db_writer"),
        start_thread(metrics_worker,       "T7-metrics"),
    ]

    logger.info("[✔] All 7 threads launched")
    print("\n[✔] IoT IDS Pipeline running")
    print("    Metrics  : http://localhost:9090/metrics")
    print("    API      : http://localhost:8000")
    print("    Dashboard: http://localhost:3000\n")

    thread_map = {
        "T1-ingestion": (packet_listener, []),
        "T2-zeek_feeder": (zeek_feeder, []),
        "T3-zeek_parser": (zeek_parser_loop, []),
        "T4-ml_inference": (ml_inference_worker, [bridge]),
        "T5-dpi_worker": (dpi_worker, []),
        "T6-db_writer": (batch_loop, []),
        "T7-metrics": (metrics_worker, []),
    }
    
    try:
        while SYSTEM_STATE.get_running():
            time.sleep(5)
            
            # Dead thread recovery
            for i, t in enumerate(threads):
                if not t.is_alive():
                    logger.error(f"[!] Thread {t.name} crashed - restarting")
                    fn, args = thread_map.get(t.name, (None, None))
                    if fn:
                        threads[i] = start_thread(fn, t.name, *args)
                        logger.info(f"[+] Restarted {t.name}")
                        
    except KeyboardInterrupt:
        logger.info("[*] Shutdown requested")
        SYSTEM_STATE.set_running(False)
        print("\n[*] Shutting down pipeline...")
        
        # Graceful shutdown: flush queues
        logger.info("[*] Flushing remaining queues...")
        time.sleep(2)


if __name__ == "__main__":
    main()
