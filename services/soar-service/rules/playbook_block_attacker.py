"""
Playbook 1 — Block Attacker
Trigger : CRITICAL risk (>= 0.85) from any IP
Action  : iptables DROP rule via UFW + log
Cooldown: 300s per IP (avoid duplicate blocks)
"""

import subprocess
import logging
import time
import os

os.makedirs("logs/siem", exist_ok=True)
logger = logging.getLogger("soar.playbook.block_attacker")

# Load backend IP from shared config — not hardcoded
try:
    from shared.utils.config_loader import BACKEND_IP
    WHITELIST = {BACKEND_IP, "127.0.0.1", "192.168.50.1"}
except Exception:
    WHITELIST = {"127.0.0.1", "192.168.50.1"}

_blocked_ips: dict = {}   # ip -> timestamp when blocked
BLOCK_COOLDOWN = 300       # 5 minutes


def run(src_ip: str, risk: float, alert: dict) -> dict:
    """
    Returns: {success, action, message}
    """
    if src_ip in WHITELIST:
        return {"success": False, "action": "SKIPPED", "message": f"{src_ip} is whitelisted"}

    # Check if already blocked recently
    last_blocked = _blocked_ips.get(src_ip, 0)
    if time.time() - last_blocked < BLOCK_COOLDOWN:
        return {"success": False, "action": "COOLDOWN", "message": f"{src_ip} already blocked"}

    try:
        # Use UFW to block — persistent across reboots
        result = subprocess.run(
            ["sudo", "ufw", "deny", "from", src_ip, "to", "any"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            _blocked_ips[src_ip] = time.time()
            msg = f"BLOCKED {src_ip} via UFW (risk={risk:.2f})"
            logger.warning(f"[BLOCK] {msg}")
            return {"success": True, "action": "BLOCKED", "message": msg}
        else:
            # Fallback to iptables directly
            subprocess.run(
                ["sudo", "iptables", "-I", "INPUT", "-s", src_ip, "-j", "DROP"],
                capture_output=True, timeout=10
            )
            _blocked_ips[src_ip] = time.time()
            msg = f"BLOCKED {src_ip} via iptables (risk={risk:.2f})"
            logger.warning(f"[BLOCK] {msg}")
            return {"success": True, "action": "BLOCKED", "message": msg}

    except Exception as e:
        logger.error(f"[BLOCK] Failed to block {src_ip}: {e}")
        return {"success": False, "action": "ERROR", "message": str(e)}


def unblock(src_ip: str) -> dict:
    """Remove block rule — called from dashboard quarantine release"""
    try:
        subprocess.run(
            ["sudo", "ufw", "delete", "deny", "from", src_ip, "to", "any"],
            capture_output=True, timeout=10
        )
        _blocked_ips.pop(src_ip, None)
        logger.info(f"[UNBLOCK] {src_ip} unblocked")
        return {"success": True, "message": f"{src_ip} unblocked"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def is_blocked(src_ip: str) -> bool:
    return src_ip in _blocked_ips
