"""
Prometheus Metrics — Phase 8
Exposes pipeline metrics on :9090
"""

import time
import threading
from prometheus_client import start_http_server, Gauge, Counter

# ---------------------------
# Metric definitions
# ---------------------------
QUEUE_DEPTH       = Gauge("pipeline_queue_depth",    "Current ML queue depth")
ALERTS_TOTAL      = Counter("alerts_total",           "Total alerts generated")
INFERENCE_MS      = Gauge("inference_latency_ms",    "Last ML inference latency (ms)")
PACKET_LOSS_PCT   = Gauge("packet_loss_pct",         "Estimated packet loss percentage")
BACKPRESSURE_MODE = Gauge("backpressure_mode",       "Current backpressure mode (0=FULL,1=50,2=33,3=NEW_ONLY)")


def update_queue_depth(val: int):
    QUEUE_DEPTH.set(val)


def update_inference_ms(val: float):
    INFERENCE_MS.set(val)


def update_packet_loss(val: float):
    PACKET_LOSS_PCT.set(val)


def inc_alerts():
    ALERTS_TOTAL.inc()


def update_backpressure(mode: int):
    BACKPRESSURE_MODE.set(mode)


def start_metrics_server(port: int = 9091):
    try:
        start_http_server(port)
        print(f"[✔] Prometheus metrics on :{port}")
    except OSError:
        # try next port if already in use
        try:
            start_http_server(port + 1)
            print(f"[✔] Prometheus metrics on :{port + 1}")
        except OSError as e:
            print(f"[!] Metrics server failed: {e} — continuing without metrics")