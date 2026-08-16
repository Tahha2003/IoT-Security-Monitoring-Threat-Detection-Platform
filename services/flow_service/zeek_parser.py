import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler

# Absolute import — works regardless of where pipeline is launched from
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.flow_service.state import ML_QUEUE
from services.flow_service.configs.config import (
    CONN_LOG_PATH, PARSER_INTERVAL, LOG_FORMAT, LOG_LEVEL
)

os.makedirs("logs/pipeline", exist_ok=True)
_h = RotatingFileHandler("logs/pipeline/zeek_parser.log", maxBytes=5*1024*1024, backupCount=3)
_h.setFormatter(logging.Formatter(LOG_FORMAT))
logger = logging.getLogger("zeek_parser")
logger.addHandler(_h)
logger.setLevel(getattr(logging, LOG_LEVEL))

# ---------------------------
# Known device registry — loaded from config, not hardcoded
# Add/change IPs here or in shared/config/system_config.yaml.
# No IP is blocked from monitoring — unknown devices are tagged "Unknown".
# ---------------------------
try:
    import yaml
    _cfg_path = os.path.join(PROJECT_ROOT, "shared", "config", "system_config.yaml")
    with open(_cfg_path) as _f:
        _sys_cfg = yaml.safe_load(_f)
    _net = _sys_cfg.get("network", {})
    KNOWN_DEVICES: dict = {
        ip: label
        for label, ips in [
            ("IP-Camera",    _net.get("iot_devices", [])[:1]),
            ("Android-BYOD", _net.get("iot_devices", [])[-1:]),
        ]
        for ip in ips
    }
    # Also label the camera_ip explicitly
    _cam = _net.get("camera_ip")
    if _cam:
        KNOWN_DEVICES[_cam] = "IP-Camera"
except Exception:
    # Fallback — still monitor everything, just no labels
    KNOWN_DEVICES = {}

logger.info(f"[*] Known devices: {KNOWN_DEVICES}")


def zeek_parser_loop():
    logger.info(f"[*] Zeek parser started — watching {CONN_LOG_PATH}")
    zeek_mode = os.getenv("ZEEK_MODE", "live")
    last_position = 0
    last_inode = None
    partial_buffer = ""  # For true streaming partial line handling

    while True:
        try:
            if not os.path.exists(CONN_LOG_PATH):
                time.sleep(2)
                continue

            current_inode = os.stat(CONN_LOG_PATH).st_ino
            if current_inode != last_inode:
                if zeek_mode == "live":
                    # Live mode: Zeek appends to the same file — only reset on
                    # actual file replacement (e.g. Zeek restart), never on
                    # normal appends. Use file size as a lower bound so we never
                    # seek backwards.
                    if last_inode is not None:
                        logger.info("[*] conn.log replaced (Zeek restarted) — resetting position")
                        last_position = 0
                    last_inode = current_inode
                    partial_buffer = ""
                else:
                    # PCAP mode: Zeek rewrites the file every batch run
                    last_position = 0
                    last_inode = current_inode
                    partial_buffer = ""
                    logger.info("[*] New conn.log detected — resetting position")

            with open(CONN_LOG_PATH, "r", encoding='utf-8', errors='replace') as f:
                f.seek(last_position)
                chunk = f.read(4096)  # Stream 4KB chunks instead of all lines
                last_position = f.tell()

            if not chunk:
                time.sleep(PARSER_INTERVAL)
                continue

            # True streaming: handle partial lines properly
            lines = (partial_buffer + chunk).split("\n")
            partial_buffer = lines.pop()  # Last line is potentially partial

            pushed = 0
            for line in lines:
                try:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split("\t")
                    # Zeek conn.log columns (0-indexed):
                    # 0=ts 1=uid 2=id.orig_h 3=id.orig_p 4=id.resp_h 5=id.resp_p
                    # 6=proto 7=service 8=duration 9=orig_bytes 10=resp_bytes
                    # 11=conn_state 12=local_orig 13=local_resp 14=missed_bytes
                    # 15=history 16=orig_pkts 17=orig_ip_bytes 18=resp_pkts
                    # 19=resp_ip_bytes 20=tunnel_parents 21=ip_proto
                    if len(parts) < 20:
                        continue

                    # Parse using header-aware column names (robust to extra cols)
                    def _int(v):  return int(v)   if v not in ("-","(empty)","") else 0
                    def _flt(v):  return float(v) if v not in ("-","(empty)","") else 0.0

                    flow = {
                        "ts":           _flt(parts[0]),
                        "uid":          parts[1],
                        "src_ip":       parts[2],
                        "dst_ip":       parts[4],
                        "dst_port":     _int(parts[5]),
                        "proto":        parts[6],
                        "service":      parts[7],
                        "duration":     _flt(parts[8]),
                        "orig_bytes":   _int(parts[9]),
                        "resp_bytes":   _int(parts[10]),
                        "conn_state":   parts[11],
                        "missed_bytes": _int(parts[14]),
                        "orig_pkts":    _int(parts[16]),
                        "orig_ip_bytes":_int(parts[17]),
                        "resp_pkts":    _int(parts[18]),
                        "resp_ip_bytes":_int(parts[19]),
                    }

                    # Tag known devices — monitor ALL traffic, no IP filter
                    # Unknown devices are tagged "Unknown" and still processed
                    flow["device_label"] = KNOWN_DEVICES.get(flow["src_ip"], "Unknown")

                    ML_QUEUE.append(flow)
                    pushed += 1

                except Exception as e:
                    logger.warning(f"Skipped malformed line: {e}")
                    continue

            if pushed:
                logger.debug(f"[+] Pushed {pushed} flows → ML_QUEUE={len(ML_QUEUE)}")

            # Shorter interval for true streaming
            time.sleep(PARSER_INTERVAL * 0.2)

        except Exception as e:
            logger.error(f"[!] Parser error: {e}")
            time.sleep(0.1)


if __name__ == "__main__":
    zeek_parser_loop()
