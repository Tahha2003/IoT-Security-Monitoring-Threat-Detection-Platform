"""
Zeek Feeder — Phase 3
Two modes:
  MODE A (default): Zeek runs on live interface (-i) — started ONCE by start_pipeline.sh
                    This feeder just monitors that conn.log is being written.
  MODE B (pcap):    Receives raw bytes from packet_listener via QUEUE_1,
                    writes to /tmp/live.pcap, runs Zeek -r on it every 2s.

On your backend: MODE A is correct for live traffic.
MODE B is for testing without a live interface.
Set env ZEEK_MODE=pcap to use MODE B.
"""

import os
import sys
import time
import subprocess
import logging
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.flow_service.state import QUEUE_1
from services.flow_service.configs.config import (
    LIVE_PCAP, ZEEK_OUTPUT_DIR, ZEEK_BINARY, ZEEK_RUN_INTERVAL
)

os.makedirs("logs/pipeline", exist_ok=True)
_h = RotatingFileHandler("logs/pipeline/zeek_feeder.log", maxBytes=5*1024*1024, backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger("zeek_feeder")
logger.addHandler(_h)
logger.setLevel(logging.INFO)

ZEEK_MODE = os.getenv("ZEEK_MODE", "live")


# --------------------------------------------------
# MODE A: Live interface — Zeek already running
# This thread just confirms conn.log is being written
# --------------------------------------------------
def zeek_feeder_live():
    from services.flow_service.configs.config import CONN_LOG_PATH
    logger.info(f"[*] Zeek feeder (LIVE MODE) — monitoring {CONN_LOG_PATH}")

    warned = False
    while True:
        try:
            if os.path.exists(CONN_LOG_PATH):
                size = os.path.getsize(CONN_LOG_PATH)
                logger.info(f"[+] conn.log exists, size={size} bytes")
                warned = False
            else:
                if not warned:
                    logger.warning(f"[!] conn.log not found at {CONN_LOG_PATH} — is Zeek running?")
                    warned = True
            time.sleep(10)
        except Exception as e:
            logger.error(f"[!] feeder error: {e}")
            time.sleep(5)


# --------------------------------------------------
# MODE B: PCAP mode — write chunks to file, run Zeek -r
# Used for testing or when Pi streams raw pcap bytes
# --------------------------------------------------
_zeek_proc = None

def _run_zeek_on_pcap():
    global _zeek_proc

    # kill previous Zeek if still running
    if _zeek_proc and _zeek_proc.poll() is None:
        _zeek_proc.terminate()
        try:
            _zeek_proc.wait(timeout=3)
        except Exception:
            _zeek_proc.kill()

    # snapshot current pcap to a temp file — avoids reading while Pi writes
    snap = LIVE_PCAP + ".snap"
    try:
        import shutil
        shutil.copy2(LIVE_PCAP, snap)
    except Exception as e:
        logger.error(f"[!] Snapshot failed: {e}")
        return

    try:
        os.makedirs(ZEEK_OUTPUT_DIR, exist_ok=True)
        _zeek_proc = subprocess.Popen(
            ["sudo", ZEEK_BINARY, "-C", "-r", snap, "local"],
            cwd=ZEEK_OUTPUT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        # wait for completion so conn.log is fully written
        try:
            out, err = _zeek_proc.communicate(timeout=15)
            if err:
                err_str = err.decode(errors="ignore").strip()
                if err_str:
                    logger.warning(f"[Zeek stderr] {err_str[:200]}")
        except subprocess.TimeoutExpired:
            _zeek_proc.kill()
        logger.info(f"[+] Zeek finished on {snap}")
    except FileNotFoundError:
        logger.error(f"[!] Zeek binary not found at {ZEEK_BINARY}")
    except Exception as e:
        logger.error(f"[!] Zeek launch failed: {e}")


def zeek_feeder_pcap():
    logger.info("[*] Zeek feeder (PCAP MODE) started")
    buffer = []

    # ensure pcap file exists with valid pcap global header
    if not os.path.exists(LIVE_PCAP) or os.path.getsize(LIVE_PCAP) < 24:
        import struct
        with open(LIVE_PCAP, "wb") as f:
            # pcap global header: magic, ver_major, ver_minor, thiszone, sigfigs, snaplen, network
            f.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
        logger.info(f"[+] Created fresh {LIVE_PCAP} with pcap header")

    last_zeek_run = 0.0

    while True:
        try:
            # drain QUEUE_1
            while len(QUEUE_1) > 0:
                chunk = QUEUE_1.popleft()
                if chunk:
                    buffer.append(chunk)

            now = time.time()

            # flush buffer to pcap file — append mode (Pi's header already at start)
            if buffer:
                with open(LIVE_PCAP, "ab") as f:
                    for chunk in buffer:
                        f.write(chunk)
                logger.info(f"[+] Wrote {len(buffer)} chunks to {LIVE_PCAP}")
                buffer.clear()

            # run Zeek every ZEEK_RUN_INTERVAL seconds
            if (now - last_zeek_run) >= ZEEK_RUN_INTERVAL:
                pcap_size = os.path.getsize(LIVE_PCAP)
                pcap_age  = now - os.path.getmtime(LIVE_PCAP)

                # Only run Zeek if pcap has data AND was updated recently (Pi connected)
                if pcap_size > 24 and pcap_age < 30:
                    _run_zeek_on_pcap()
                    last_zeek_run = now
                elif pcap_age >= 30:
                    logger.debug(f"[*] pcap stale ({pcap_age:.0f}s) — Pi disconnected, skipping Zeek")

            time.sleep(0.05)

        except Exception as e:
            logger.error(f"[!] feeder error: {e}")
            time.sleep(0.2)


# --------------------------------------------------
# ENTRY — picks mode from env
# --------------------------------------------------
def zeek_feeder():
    # re-read at runtime so env var set by main_pipeline.py takes effect
    mode = os.getenv("ZEEK_MODE", "live")
    if mode == "pcap":
        zeek_feeder_pcap()
    else:
        zeek_feeder_live()


if __name__ == "__main__":
    zeek_feeder()