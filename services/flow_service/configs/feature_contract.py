# /configs/feature_contract.py

"""
Production Feature Contract (v3.0.0)
- Backward compatible with existing pipeline
- Extended for modern IoT attack detection
- Supports derived behavioral features
"""

from typing import List, Dict

# ------------------------------
# Zeek Log Fields (SOURCE OF TRUTH)
# ------------------------------
ZEEK_FEATURES: Dict[str, List[str]] = {
    "conn": [
        "ts", "uid",
        "id.orig_h", "id.orig_p",
        "id.resp_h", "id.resp_p",
        "proto", "service",
        "duration",
        "orig_bytes", "resp_bytes",
        "conn_state",
        "local_orig", "local_resp",
        "missed_bytes",
        "orig_pkts", "resp_pkts",
        "orig_ip_bytes", "resp_ip_bytes"
    ]
}

# ------------------------------
# LOCKED FEATURES (MODEL INPUT ORDER)
# ⚠️ DO NOT REORDER (MODEL DEPENDS ON THIS)
# ------------------------------
LOCKED_FEATURE_KEYS: List[str] = [

    # ---- Core Flow Features ----
    "duration",
    "proto",
    "service",

    # ---- Traffic Volume ----
    "src_bytes",
    "dst_bytes",
    "total_bytes",        # NEW

    # ---- Behavioral Ratios ----
    "byte_ratio",         # NEW

    # ---- Connection State ----
    "conn_state",

    # ---- Reliability ----
    "missed_bytes",

    # ---- Packet-Level ----
    "src_pkts",
    "dst_pkts",
    "pkt_ratio",          # NEW

    # ---- IP-Level Volume ----
    "src_ip_bytes",
    "dst_ip_bytes"        # NEW
]

# ------------------------------
# DEFAULT VALUES (SAFE FALLBACKS)
# ------------------------------
DEFAULTS: Dict[str, object] = {

    # ---- Core ----
    "duration": 0.0,
    "proto": "unknown",
    "service": "unknown",

    # ---- Volume ----
    "src_bytes": 0,
    "dst_bytes": 0,
    "total_bytes": 0,

    # ---- Ratios ----
    "byte_ratio": 0.0,

    # ---- State ----
    "conn_state": "unknown",

    # ---- Reliability ----
    "missed_bytes": 0,

    # ---- Packets ----
    "src_pkts": 0,
    "dst_pkts": 0,
    "pkt_ratio": 0.0,

    # ---- IP Volume ----
    "src_ip_bytes": 0,
    "dst_ip_bytes": 0
}

# ------------------------------
# FEATURE GROUPING (OPTIONAL - FOR DEBUG / FUTURE USE)
# ------------------------------
FEATURE_GROUPS = {
    "core": ["duration", "proto", "service"],
    "volume": ["src_bytes", "dst_bytes", "total_bytes"],
    "ratios": ["byte_ratio", "pkt_ratio"],
    "state": ["conn_state"],
    "reliability": ["missed_bytes"],
    "packets": ["src_pkts", "dst_pkts"],
    "ip_volume": ["src_ip_bytes", "dst_ip_bytes"]
}

# ------------------------------
# VERSIONING (IMPORTANT FOR MODEL COMPATIBILITY)
# ------------------------------
FEATURE_CONTRACT_VERSION = "3.0.0"