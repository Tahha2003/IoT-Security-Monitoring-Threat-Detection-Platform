"""
Playbook 2 — Camera Defense
Trigger : Attack targeting IP Camera (192.168.10.101), CRITICAL/HIGH
Action  : Log detailed alert + rate limit attacker + notify dashboard
"""

import logging
import time
import os
import subprocess

os.makedirs("logs/siem", exist_ok=True)
os.makedirs("logs/soar", exist_ok=True)

logger = logging.getLogger("soar.playbook.camera_defense")

# Load camera IP from shared config — not hardcoded
try:
    from shared.utils.config_loader import CAMERA_IP
except Exception:
    CAMERA_IP = ""
_rate_limited: dict = {}
RATE_LIMIT_COOLDOWN = 120  # 2 minutes


def run(src_ip: str, risk: float, alert: dict) -> dict:
    """
    Triggered when attack targets camera.
    """
    dst_ip = alert.get("dst_ip", "")
    if dst_ip != CAMERA_IP:
        return {"success": False, "action": "SKIPPED", "message": "Not targeting camera"}

    attack_type = alert.get("attack_type", "UNKNOWN")
    severity    = alert.get("severity", "UNKNOWN")

    # Log to dedicated camera defense log
    with open("logs/soar/camera_defense.log", "a") as f:
        f.write(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} | "
            f"ATTACKER={src_ip} | TARGET={CAMERA_IP} | "
            f"SEVERITY={severity} | TYPE={attack_type} | RISK={risk:.2f}\n"
        )

    # Rate limit attacker if CRITICAL
    if risk >= 0.85:
        last = _rate_limited.get(src_ip, 0)
        if time.time() - last > RATE_LIMIT_COOLDOWN:
            try:
                # Rate limit: max 10 packets/sec from attacker to camera
                subprocess.run([
                    "sudo", "iptables", "-I", "FORWARD",
                    "-s", src_ip, "-d", CAMERA_IP,
                    "-m", "limit", "--limit", "10/sec",
                    "-j", "ACCEPT"
                ], capture_output=True, timeout=10)

                subprocess.run([
                    "sudo", "iptables", "-I", "FORWARD",
                    "-s", src_ip, "-d", CAMERA_IP,
                    "-j", "DROP"
                ], capture_output=True, timeout=10)

                _rate_limited[src_ip] = time.time()
                msg = f"Rate limited {src_ip} → Camera (risk={risk:.2f})"
                logger.warning(f"[CAMERA] {msg}")
                return {"success": True, "action": "RATE_LIMITED", "message": msg}

            except Exception as e:
                logger.error(f"[CAMERA] Rate limit failed: {e}")

    msg = f"Camera attack logged: {src_ip} → {CAMERA_IP} ({severity})"
    logger.info(f"[CAMERA] {msg}")
    return {"success": True, "action": "LOGGED", "message": msg}
