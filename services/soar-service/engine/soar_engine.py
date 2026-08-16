"""
SOAR Engine — Phase 6 (v2 — Real Playbooks)
Evaluates each alert and routes to appropriate playbook.

Playbooks:
  1. block_attacker      — CRITICAL from external attacker → UFW block
  2. camera_defense      — Attack targeting camera → rate limit + log
  3. quarantine_device   — Compromised IoT device → network isolate
  4. scan_detection      — Port scan → throttle

Trigger: risk >= 0.85, 3+ events in 60s rolling window, 60s cooldown
"""

import time
import logging
import os
import sys
from collections import defaultdict, deque

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

os.makedirs("logs/siem", exist_ok=True)
os.makedirs("logs/soar", exist_ok=True)

logging.basicConfig(
    filename="logs/siem/soar_engine.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("soar.engine")

# ── Load Playbooks ─────────────────────────────────────────────────────────
import importlib.util, pathlib

def _load_playbook(name):
    p = pathlib.Path(PROJECT_ROOT) / "services/soar-service/rules" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, p)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    pb_block     = _load_playbook("playbook_block_attacker")
    pb_camera    = _load_playbook("playbook_camera_defense")
    pb_quarantine= _load_playbook("playbook_quarantine_device")
    pb_scan      = _load_playbook("playbook_scan_detection")
    logger.info("[SOAR] All 4 playbooks loaded")
except Exception as e:
    logger.error(f"[SOAR] Playbook load failed: {e}")
    pb_block = pb_camera = pb_quarantine = pb_scan = None

# ── Trigger config ─────────────────────────────────────────────────────────
RISK_THRESHOLD  = 0.80
WINDOW_SECONDS  = 60
MIN_EVENTS      = 3
COOLDOWN        = 60

# Load IoT device IPs and camera IP from shared config — not hardcoded
try:
    from shared.utils.config_loader import IOT_DEVICES, CAMERA_IP
except Exception:
    IOT_DEVICES = set()
    CAMERA_IP   = ""

_ip_events:       defaultdict = defaultdict(deque)
_ip_last_trigger: dict        = {}

# ── Playbook results log ───────────────────────────────────────────────────
_playbook_log = []   # in-memory for API access


import ipaddress

def evaluate(src_ip: str, risk: float, alert: dict = None) -> str:
    """
    Main entry — called from main_pipeline._build_and_queue_alert()
    Returns: 'NO_ACTION' | 'COOLDOWN' | 'TRIGGER'
    """
    # Validate IP before any playbook can use it (prevents shell injection via ufw)
    try:
        ipaddress.ip_address(src_ip)
    except ValueError:
        logger.error(f"[SOAR] Invalid src_ip rejected: {src_ip!r}")
        return "NO_ACTION"

    if alert is None:
        alert = {}

    if risk < RISK_THRESHOLD:
        # Still run scan detection even for lower risk
        if pb_scan and alert.get("attack_type") in ("ML_CLASSIFIED", "ML_CONFIRMED"):
            pb_scan.run(src_ip, risk, alert)
        return "NO_ACTION"

    now = time.time()

    # Cooldown check
    last = _ip_last_trigger.get(src_ip, 0)
    if now - last < COOLDOWN:
        return "COOLDOWN"

    # Rolling window
    events = _ip_events[src_ip]
    events.append(now)
    while events and (now - events[0]) > WINDOW_SECONDS:
        events.popleft()

    if len(events) < MIN_EVENTS:
        return "NO_ACTION"

    # ── TRIGGER ────────────────────────────────────────────────────────────
    _ip_last_trigger[src_ip] = now
    _ip_events[src_ip].clear()

    logger.warning(f"[SOAR TRIGGER] src_ip={src_ip} risk={risk:.2f} attack={alert.get('attack_type','?')}")

    results = []

    # ── Check runtime playbook flags (set via dashboard toggles) ──────────
    import json as _json
    _flags = {}
    try:
        _flag_path = pathlib.Path(PROJECT_ROOT) / "logs/soar/playbook_flags.json"
        if _flag_path.exists():
            _flags = _json.loads(_flag_path.read_text())
    except Exception:
        pass

    def _pb_enabled(name: str) -> bool:
        return _flags.get(name, True)  # default: enabled

    # Route to playbooks based on context
    dst_ip     = alert.get("dst_ip", "")
    attack_type= alert.get("attack_type", "")

    # Playbook 1 — Block external attacker (not IoT devices)
    if src_ip not in IOT_DEVICES and pb_block and _pb_enabled("block_attacker"):
        r = pb_block.run(src_ip, risk, alert)
        results.append({"playbook": "block_attacker", **r})
        logger.info(f"[PB1] block_attacker → {r['action']}: {r['message']}")

    # Playbook 2 — Camera defense (attack targeting camera)
    if dst_ip == CAMERA_IP and pb_camera and _pb_enabled("camera_defense"):
        r = pb_camera.run(src_ip, risk, alert)
        results.append({"playbook": "camera_defense", **r})
        logger.info(f"[PB2] camera_defense → {r['action']}: {r['message']}")

    # Playbook 3 — Quarantine compromised IoT device
    if src_ip in IOT_DEVICES and pb_quarantine and _pb_enabled("quarantine_device"):
        r = pb_quarantine.run(src_ip, risk, alert)
        results.append({"playbook": "quarantine_device", **r})
        logger.info(f"[PB3] quarantine_device → {r['action']}: {r['message']}")

    # Playbook 4 — Scan detection (always run)
    if pb_scan and _pb_enabled("scan_detection"):
        r = pb_scan.run(src_ip, risk, alert)
        results.append({"playbook": "scan_detection", **r})

    # Store in memory log
    _playbook_log.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "src_ip":    src_ip,
        "risk":      risk,
        "results":   results,
    })
    if len(_playbook_log) > 500:
        _playbook_log.pop(0)

    return "TRIGGER"


def get_playbook_log() -> list:
    """For API endpoint — returns recent playbook executions"""
    return list(reversed(_playbook_log[-50:]))


def get_quarantined_devices() -> list:
    """For dashboard quarantine status"""
    if pb_quarantine:
        return pb_quarantine.get_quarantined()
    return []


def release_quarantine(src_ip: str) -> dict:
    """Called from dashboard UNQUARANTINE button"""
    if pb_quarantine:
        return pb_quarantine.release(src_ip)
    return {"success": False, "message": "Quarantine playbook not loaded"}


def unblock_ip(src_ip: str) -> dict:
    """Called from dashboard UNBLOCK button"""
    if pb_block:
        return pb_block.unblock(src_ip)
    return {"success": False, "message": "Block playbook not loaded"}
