"""
SIEM Batch Writer — Phase 6
Queues alert dicts in-memory, flushes to PostgreSQL every 2 seconds.
Decouples pipeline from DB write latency.
"""

import time
import logging
import os
from collections import deque
from datetime import datetime

import psycopg2

# Load IoT device set from shared config — not hardcoded
try:
    from shared.utils.config_loader import IOT_DEVICES as _IOT_DEVICES
except Exception:
    _IOT_DEVICES = set()

# ---------------------------
# Logging
# ---------------------------
os.makedirs("logs/siem", exist_ok=True)
logging.basicConfig(
    filename="logs/siem/batch_writer.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("siem.batch_writer")

# ---------------------------
# In-memory queue
# ---------------------------
_alert_queue: deque = deque(maxlen=10000)

# ---------------------------
# DB config — update via env or config file on your backend
# ---------------------------
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "fyp_security"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "postgres"),
}

INSERT_SQL = """
    INSERT INTO alerts
        (timestamp, src_ip, dst_ip, dst_port, protocol,
         risk_score, severity, attack_type, packet_count, byte_count)
    VALUES
        (%(timestamp)s, %(src_ip)s, %(dst_ip)s, %(dst_port)s, %(protocol)s,
         %(risk_score)s, %(severity)s, %(attack_type)s, %(packet_count)s, %(byte_count)s)
"""


def queue_alert(d: dict):
    """Called from pipeline — non-blocking."""
    _alert_queue.append(d)


def _get_conn():
    return psycopg2.connect(**DB_CONFIG)


def batch_loop():
    """Background thread — flush every 2 seconds."""
    logger.info("[*] Batch writer started")

    while True:
        time.sleep(2)

        if not _alert_queue:
            continue

        # drain current batch
        batch = []
        while _alert_queue:
            batch.append(_alert_queue.popleft())

        try:
            conn = _get_conn()
            cur  = conn.cursor()

            rows = []
            for d in batch:
                # Skip NORMAL traffic — except from known IoT devices
                if d.get("attack_type") == "NORMAL" and d.get("src_ip") not in _IOT_DEVICES:
                    continue
                rows.append({
                    "timestamp":    d.get("timestamp", datetime.utcnow().isoformat()),
                    "src_ip":       d.get("src_ip", "0.0.0.0"),
                    "dst_ip":       d.get("dst_ip", "0.0.0.0"),
                    "dst_port":     d.get("dst_port", 0),
                    "protocol":     d.get("protocol", "-"),
                    "risk_score":   d.get("risk_score", 0.0),
                    "severity":     d.get("severity", "LOW"),
                    "attack_type":  d.get("attack_type", "UNKNOWN"),
                    "packet_count": d.get("packet_count", 0),
                    "byte_count":   d.get("byte_count", 0),
                })

            if not rows:
                continue

            cur.executemany(INSERT_SQL, rows)
            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"[+] Inserted {len(rows)} alerts")

        except Exception as e:
            logger.error(f"[!] DB write failed: {e}")
            # put back in queue so we don't lose data
            for d in batch:
                _alert_queue.appendleft(d)
