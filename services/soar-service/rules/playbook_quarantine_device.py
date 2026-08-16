"""
Playbook 3 — Quarantine IoT Device
Trigger : IoT device (camera/BYOD) shows malicious behavior (risk >= 0.85)
Action  : Isolate device — block all traffic except to/from backend
          Used when IoT device itself is compromised
"""

import subprocess
import logging
import time
import os

os.makedirs("logs/soar", exist_ok=True)
logger = logging.getLogger("soar.playbook.quarantine")

# Load IoT device registry and backend IP from shared config — not hardcoded
try:
    from shared.utils.config_loader import IOT_DEVICE_NAMES as IOT_DEVICES, BACKEND_IP
except Exception:
    IOT_DEVICES = {}
    BACKEND_IP  = ""
_quarantined: dict = {}   # ip -> timestamp


def run(src_ip: str, risk: float, alert: dict) -> dict:
    """
    Quarantine an IoT device — only if it's in IOT_DEVICES.
    """
    if src_ip not in IOT_DEVICES:
        return {"success": False, "action": "SKIPPED", "message": f"{src_ip} not an IoT device"}

    if src_ip in _quarantined:
        return {"success": False, "action": "ALREADY_QUARANTINED", "message": f"{src_ip} already quarantined"}

    device_name = IOT_DEVICES[src_ip]

    try:
        # Allow traffic to/from backend only
        subprocess.run([
            "sudo", "iptables", "-I", "FORWARD",
            "-s", src_ip, "-d", BACKEND_IP, "-j", "ACCEPT"
        ], capture_output=True, timeout=10)

        subprocess.run([
            "sudo", "iptables", "-I", "FORWARD",
            "-s", BACKEND_IP, "-d", src_ip, "-j", "ACCEPT"
        ], capture_output=True, timeout=10)

        # Block all other traffic from this device
        subprocess.run([
            "sudo", "iptables", "-A", "FORWARD",
            "-s", src_ip, "-j", "DROP"
        ], capture_output=True, timeout=10)

        _quarantined[src_ip] = time.time()

        # Log quarantine event
        with open("logs/soar/quarantine.log", "a") as f:
            f.write(
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} | "
                f"QUARANTINED={src_ip} ({device_name}) | "
                f"RISK={risk:.2f} | ATTACK={alert.get('attack_type','?')}\n"
            )

        msg = f"QUARANTINED {device_name} ({src_ip}) — risk={risk:.2f}"
        logger.warning(f"[QUARANTINE] {msg}")
        return {"success": True, "action": "QUARANTINED", "message": msg, "device": device_name}

    except Exception as e:
        logger.error(f"[QUARANTINE] Failed: {e}")
        return {"success": False, "action": "ERROR", "message": str(e)}


def release(src_ip: str) -> dict:
    """Release quarantine — called from dashboard"""
    if src_ip not in _quarantined:
        return {"success": False, "message": f"{src_ip} not quarantined"}
    try:
        subprocess.run([
            "sudo", "iptables", "-D", "FORWARD",
            "-s", src_ip, "-j", "DROP"
        ], capture_output=True, timeout=10)

        _quarantined.pop(src_ip)
        logger.info(f"[QUARANTINE] Released {src_ip}")
        return {"success": True, "message": f"{src_ip} released from quarantine"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_quarantined() -> list:
    return list(_quarantined.keys())
