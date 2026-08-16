"""
DPI Engine — Phase 5 + Process Pooling
Runs Suricata ONLY on ML-flagged flows (send_to_dpi=True).
Parses eve.json for alerts and returns structured results.
"""

import os
import json
import time
import logging
import tempfile
import subprocess
import struct
import threading
from queue import Queue, Empty

os.makedirs("logs/dpi", exist_ok=True)
logging.basicConfig(
    filename="logs/dpi/dpi_engine.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("dpi.engine")

# Path to suricata binary — update if different on your backend
SURICATA_BIN  = os.getenv("SURICATA_BIN", "/usr/bin/suricata")
SURICATA_CONF = os.getenv("SURICATA_CONF", "/etc/suricata/suricata.yaml")

# Suricata Process Pool (fixes overhead issue)
DPI_WORKER_COUNT = max(2, os.cpu_count() or 2)
dpi_queue = Queue(maxsize=1000)
result_queue = Queue()
_workers = []
_pool_initialized = False
_pool_lock = threading.Lock()


def _dpi_worker():
    """Worker thread for Suricata process reuse"""
    while True:
        try:
            job_id, packets = dpi_queue.get(timeout=1)
            
            if not packets:
                result_queue.put((job_id, []))
                continue
                
            tmp_dir  = tempfile.mkdtemp(prefix="dpi_")
            pcap_path = os.path.join(tmp_dir, "flow.pcap")
            eve_path  = os.path.join(tmp_dir, "eve.json")
            
            try:
                # write pcap — prepend global header if raw bytes passed
                with open(pcap_path, "wb") as f:
                    if not packets[:4] == b'\xd4\xc3\xb2\xa1':
                        # add minimal pcap global header
                        f.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
                    f.write(packets)

                result = subprocess.run(
                    [
                        SURICATA_BIN,
                        "-r", pcap_path,
                        "-c", SURICATA_CONF,
                        "--set", f"outputs.1.eve-log.filename={eve_path}",
                        "-l", tmp_dir,
                        "--runmode", "single",
                    ],
                    capture_output=True,
                    timeout=5,
                )

                alerts = []
                if os.path.exists(eve_path):
                    with open(eve_path) as f:
                        for line in f:
                            try:
                                ev = json.loads(line)
                                if ev.get("event_type") == "alert":
                                    alerts.append({
                                        "sig":      ev["alert"].get("signature", ""),
                                        "cat":      ev["alert"].get("category", ""),
                                        "severity": ev["alert"].get("severity", 3),
                                    })
                            except Exception:
                                continue
                                
                result_queue.put((job_id, alerts))
                
            finally:
                # cleanup temp files
                try:
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
                    
        except Empty:
            continue
        except Exception as e:
            logger.error(f"[DPI] Worker error: {e}")
            time.sleep(0.1)


def _init_pool():
    """Initialize DPI worker pool once"""
    global _pool_initialized
    with _pool_lock:
        if _pool_initialized:
            return
            
        for i in range(DPI_WORKER_COUNT):
            t = threading.Thread(target=_dpi_worker, daemon=True, name=f"dpi-worker-{i}")
            t.start()
            _workers.append(t)
            
        _pool_initialized = True
        logger.info(f"[DPI] Initialized {DPI_WORKER_COUNT} worker threads")


def run_dpi(packets: bytes) -> list:
    """
    Called only when send_to_dpi=True.
    packets: raw bytes (pcap format expected by suricata -r)
    Returns list of {sig, cat, severity} dicts.
    """
    if not _pool_initialized:
        _init_pool()
        
    if not packets:
        return []
        
    import uuid
    job_id = str(uuid.uuid4())   # unique per call — fixes memory address reuse collision
    dpi_queue.put((job_id, packets))
    
    # Wait for result with timeout
    start = time.time()
    while time.time() - start < 8:
        try:
            res_id, alerts = result_queue.get(timeout=0.1)
            if res_id == job_id:
                logger.debug(f"[DPI] {len(alerts)} alerts from suricata")
                return alerts
            else:
                # Not our result, put back
                result_queue.put((res_id, alerts))
        except Empty:
            continue
            
    logger.warning("[DPI] Suricata timeout")
    return []
