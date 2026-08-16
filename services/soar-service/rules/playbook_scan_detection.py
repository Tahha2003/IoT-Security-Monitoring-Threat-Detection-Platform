"""
Playbook 4 — Port Scan Detection & Response
Trigger : ML_CLASSIFIED attack with multiple dst_ports in short time
Action  : Log scan details + throttle scanner
"""

import logging
import time
import os
import subprocess
from collections import defaultdict, deque

os.makedirs("logs/soar", exist_ok=True)
logger = logging.getLogger("soar.playbook.scan_detection")

# Track ports seen per src_ip in rolling window
_port_tracker: defaultdict = defaultdict(deque)
_throttled: dict = {}

SCAN_WINDOW    = 30    # seconds
SCAN_THRESHOLD = 20    # unique ports in window = scan
THROTTLE_COOLDOWN = 180  # 3 minutes


def run(src_ip: str, risk: float, alert: dict) -> dict:
    """
    Detect port scanning behavior and throttle.
    """
    attack_type = alert.get("attack_type", "")
    dst_port    = alert.get("dst_port", 0)

    if attack_type not in ("ML_CLASSIFIED", "ML_CONFIRMED"):
        return {"success": False, "action": "SKIPPED", "message": "Not a scan pattern"}

    now = time.time()

    # Track this port
    ports = _port_tracker[src_ip]
    ports.append((now, dst_port))

    # Prune old entries
    while ports and (now - ports[0][0]) > SCAN_WINDOW:
        ports.popleft()

    unique_ports = len(set(p[1] for p in ports))

    if unique_ports >= SCAN_THRESHOLD:
        # Scan detected
        last_throttle = _throttled.get(src_ip, 0)
        if now - last_throttle > THROTTLE_COOLDOWN:
            try:
                # Throttle: limit to 5 new connections per second
                subprocess.run([
                    "sudo", "iptables", "-I", "INPUT",
                    "-s", src_ip,
                    "-m", "state", "--state", "NEW",
                    "-m", "limit", "--limit", "5/sec", "--limit-burst", "10",
                    "-j", "ACCEPT"
                ], capture_output=True, timeout=10)

                _throttled[src_ip] = now

                with open("logs/soar/scan_detection.log", "a") as f:
                    f.write(
                        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} | "
                        f"SCANNER={src_ip} | UNIQUE_PORTS={unique_ports} | "
                        f"RISK={risk:.2f} | ACTION=THROTTLED\n"
                    )

                msg = f"Port scan detected from {src_ip} ({unique_ports} ports) — throttled"
                logger.warning(f"[SCAN] {msg}")
                return {"success": True, "action": "THROTTLED", "message": msg, "ports_scanned": unique_ports}

            except Exception as e:
                logger.error(f"[SCAN] Throttle failed: {e}")

        return {
            "success": True, "action": "SCAN_DETECTED",
            "message": f"Scan from {src_ip}: {unique_ports} ports",
            "ports_scanned": unique_ports
        }

    return {"success": False, "action": "MONITORING", "message": f"{src_ip}: {unique_ports} ports so far"}
