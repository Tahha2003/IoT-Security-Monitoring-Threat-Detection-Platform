"""
Shared Config Loader
Loads shared/config/system_config.yaml once and exposes typed helpers.
All services import from here — no hardcoded IPs anywhere else.
"""

import os
import yaml

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "shared", "config", "system_config.yaml")

# ── Load once at import time ───────────────────────────────────────────────
try:
    with open(_CONFIG_PATH) as _f:
        _cfg = yaml.safe_load(_f)
except FileNotFoundError:
    _cfg = {}

_net = _cfg.get("network", {})
_db  = _cfg.get("database", {})

# ── Public API ─────────────────────────────────────────────────────────────

# Set of all IoT device IPs (camera + BYOD etc.)
IOT_DEVICES: set = set(_net.get("iot_devices", []))

# IP of the primary camera (used by camera_defense playbook)
CAMERA_IP: str = _net.get("camera_ip", "")

# IP of the backend/detection host (used by block/quarantine playbooks)
BACKEND_IP: str = _net.get("backend_ip", "")

# All IPs that should never be blocked (infrastructure)
BLOCK_WHITELIST: set = {BACKEND_IP, "127.0.0.1"} | IOT_DEVICES - set()
# Note: IoT devices may be quarantined separately — they are NOT in BLOCK_WHITELIST
BLOCK_WHITELIST = {BACKEND_IP, "127.0.0.1", "192.168.50.1"}

# Human-readable labels for known devices (for tagging flows in the parser)
KNOWN_DEVICES: dict = {}
for _ip in _net.get("iot_devices", []):
    KNOWN_DEVICES[_ip] = "IoT-Device"
if CAMERA_IP:
    KNOWN_DEVICES[CAMERA_IP] = "IP-Camera"

# Quarantine: full label map  ip -> name  (used by quarantine playbook)
IOT_DEVICE_NAMES: dict = {
    ip: KNOWN_DEVICES.get(ip, f"IoT-{ip}")
    for ip in IOT_DEVICES
}
