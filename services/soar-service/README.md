# SOAR Service — Security Orchestration, Automation and Response

The SOAR service evaluates every alert produced by the detection pipeline and automatically executes defensive playbooks when threat conditions are met. It runs inline inside the main pipeline (called from Thread 5) and responds to confirmed threats in under 5 seconds from detection.

---

## Role in the Pipeline

```
T5 DPI Worker → _build_and_queue_alert()
                        │
                        └──→ soar_evaluate(src_ip, dst_ip, risk_score, alert)
                                        │
                                  IP validation
                                  Risk threshold check (≥ 0.80)
                                  Rolling window check (3+ events / 60s)
                                  Cooldown check (60s per IP)
                                  Playbook flags check (playbook_flags.json)
                                        │
                                  ┌─────┴──────┐
                               NO_ACTION    TRIGGER
                                             │
                                  Route to matching playbooks:
                                  PB1: Block Attacker
                                  PB2: Camera Defense
                                  PB3: Device Quarantine
                                  PB4: Scan Detection
```

---

## Structure

```
soar-service/
├── engine/
│   └── soar_engine.py                   # evaluate() + playbook routing + flag file reader
├── rules/
│   ├── playbook_block_attacker.py       # PB1 — UFW block rule
│   ├── playbook_camera_defense.py       # PB2 — iptables rate limit on camera traffic
│   ├── playbook_quarantine_device.py    # PB3 — network isolation of IoT device
│   └── playbook_scan_detection.py       # PB4 — port scan throttling
└── __init__.py
```

---

## Trigger Conditions

All four conditions must be met for a playbook to fire:

| Condition | Value |
|-----------|-------|
| Risk score | ≥ 0.80 |
| Events from same source in rolling window | ≥ 3 within 60 seconds |
| Cooldown since last trigger for this IP | > 60 seconds |
| Playbook enabled in `playbook_flags.json` | `true` |

This prevents false-positive playbook executions and alert flooding from a single active attacker.

---

## IP Validation

Before any playbook executes, `src_ip` is validated with `ipaddress.ip_address()`. Invalid or malformed IP strings are rejected and logged — this prevents command-injection attacks reaching `ufw` or `iptables` via a crafted `src_ip` value in an alert.

---

## Config Centralization

All device IPs (`IOT_DEVICES`, `CAMERA_IP`, `BACKEND_IP`) are loaded from one location:

```python
from shared.utils.config_loader import ConfigLoader
cfg = ConfigLoader.load()

IOT_DEVICES = set(cfg['network']['iot_devices'])
CAMERA_IP   = cfg['network']['camera_ip']
BACKEND_IP  = cfg['network']['backend_ip']
```

No IP is hardcoded in `soar_engine.py` or any playbook file. Previously each playbook had its own duplicate hardcoded sets — all replaced by `config_loader` in Session 1.

To update monitored device IPs: edit `shared/config/system_config.yaml` and restart the pipeline.

---

## Playbooks

### PB1 — Block Attacker (`playbook_block_attacker.py`)

```
Trigger:  CRITICAL alert from external IP (src_ip NOT in IOT_DEVICES)
Action:   sudo ufw insert 1 deny from <ip> to any
Result:   All traffic from attacker dropped at OS firewall level
Revert:   Dashboard "UNBLOCK" button → POST /api/soar/unblock/<ip> → ufw delete rule
Log:      logs/siem/soar_engine.log + logs/soar/block_attacker.log
```

### PB2 — Camera Defense (`playbook_camera_defense.py`)

```
Trigger:  Any alert where dst_ip == CAMERA_IP (192.168.50.10)
Action:   iptables rate-limit rule throttling attacker traffic to camera
Result:   Camera remains operational; attacker's bandwidth to camera is throttled
Revert:   bash infrastructure/scripts/reset_firewall.sh
Log:      logs/soar/camera_defense.log
```

### PB3 — Device Quarantine (`playbook_quarantine_device.py`)

```
Trigger:  CRITICAL alert where src_ip IN IOT_DEVICES (compromised device scenario)
Action:   sudo iptables -I FORWARD -s <device_ip> -j DROP
Result:   Compromised IoT device cannot communicate with rest of network
Revert:   Dashboard "RELEASE" button → POST /api/soar/unblock/<ip> → iptables rule removal
Log:      logs/soar/quarantine.log
```

### PB4 — Scan Detection (`playbook_scan_detection.py`)

```
Trigger:  20+ unique destination ports accessed from same source within 30 seconds
Action:   iptables rate-limit + connection throttle on scanning source
Result:   Scanning activity slowed significantly; analyst alerted via dashboard toast
Revert:   bash infrastructure/scripts/reset_firewall.sh
Log:      logs/soar/scan_detection.log
```

---

## Playbook Routing Logic

Multiple playbooks can fire for a single trigger event:

```python
# PB1 — external attacker (not an IoT device)
if src_ip not in IOT_DEVICES:
    if playbook_enabled("block_attacker"):
        pb_block.run(src_ip, risk_score)

# PB2 — attack targeting the camera
if dst_ip == CAMERA_IP:
    if playbook_enabled("camera_defense"):
        pb_camera.run(src_ip, dst_ip, risk_score)

# PB3 — traffic sourced from a compromised IoT device
if src_ip in IOT_DEVICES:
    if playbook_enabled("quarantine_device"):
        pb_quarantine.run(src_ip, risk_score)

# PB4 — always evaluated at trigger threshold
if playbook_enabled("scan_detection"):
    pb_scan.run(src_ip, risk_score)
```

**Example cascade:** A BYOD mobile scanning the camera triggers PB3 (quarantine BYOD) + PB2 (camera defense) + PB4 (scan throttle) simultaneously.

---

## Runtime Playbook Toggle

Each playbook can be enabled or disabled live from the dashboard **SOAR Panel** without restarting the pipeline.

**Mechanism:**
1. Dashboard toggle → `POST /api/soar/playbooks/{name}` → API updates in-memory state
2. API writes current state to `logs/soar/playbook_flags.json`
3. `soar_engine.py` calls `playbook_enabled(name)` on every alert evaluation, which re-reads this file
4. Change takes effect on the next alert — no restart required

```json
// logs/soar/playbook_flags.json
{
  "block_attacker":    true,
  "camera_defense":    true,
  "quarantine_device": true,
  "scan_detection":    false
}
```

If the flags file does not exist (e.g., fresh install), all playbooks default to **enabled**.

---

## In-Memory Playbook Log

The engine keeps the last 500 playbook execution records in `_playbook_log` (in-memory). This is served by the API at `GET /api/soar/log` and displayed in the dashboard SOAR panel. Each entry:

```json
{
  "timestamp": "2026-08-17T14:22:01Z",
  "src_ip":    "192.168.2.130",
  "risk":      0.91,
  "results": [
    {"playbook": "block_attacker",  "action": "BLOCKED",   "message": "UFW rule added"},
    {"playbook": "scan_detection",  "action": "THROTTLED", "message": "Rate limit applied"}
  ]
}
```

---

## Quarantined Devices List

The engine maintains a `_quarantined_ips` set (in-memory). The API serves this at `GET /api/soar/quarantined` — the dashboard uses it to show the quarantine icon on device cards and to display the RELEASE button.

When an IP is unblocked via `POST /api/soar/unblock/{ip}`, it is removed from `_quarantined_ips` and the iptables FORWARD DROP rule is deleted.

---

## Logs

| Log File | Contents |
|----------|----------|
| `logs/siem/soar_engine.log` | Trigger events, playbook routing decisions, IP validation rejections |
| `logs/soar/block_attacker.log` | UFW block/unblock actions with timestamps |
| `logs/soar/camera_defense.log` | Camera rate-limit events |
| `logs/soar/quarantine.log` | Device quarantine/release events |
| `logs/soar/scan_detection.log` | Scan throttling actions |
| `logs/soar/playbook_flags.json` | Current runtime enable/disable state |

---

## Dependencies

- **UFW** — for PB1 block rules. Requires `sudo ufw` without password (configured by `setup_sudo.sh`)
- **iptables** — for PB2, PB3, PB4 rules. Requires `sudo iptables` without password
- **Python stdlib** — `ipaddress`, `json`, `time`, `threading`
- **config_loader** — `shared/utils/config_loader.py`
