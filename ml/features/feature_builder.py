"""
Feature Builder - Production Version (v3 aligned)
- Fully aligned with feature_contract v3.0.0
- Removes EWMA smoothing (critical for IDS accuracy)
- Adds derived behavioral features
- Maintains backward compatibility
"""

from typing import Dict, Any, List
from ml.configs.feature_contract import LOCKED_FEATURE_KEYS, DEFAULTS


class FeatureBuilder:

    def __init__(self, debug: bool = False):
        self.feature_keys = LOCKED_FEATURE_KEYS
        self.debug = debug

    # ------------------------------
    # MAIN ENTRY
    # ------------------------------
    def build_features(self, zeek_record: Dict[str, Any]) -> Dict[str, Any]:

        try:
            features = self._extract_features(zeek_record)
            return self._enforce_contract(features)

        except Exception as e:
            if self.debug:
                print("[ERROR] Feature build failed:", e)
                print("Record:", zeek_record)

            return DEFAULTS.copy()

    # ------------------------------
    # CORE EXTRACTION + DERIVED FEATURES
    # ------------------------------
    def _extract_features(self, r: Dict[str, Any]) -> Dict[str, Any]:

        # ---- Raw extraction ----
        duration = self._safe_float(r.get("duration"))

        # ---- Behavior normalization (SAFE - no contract impact) ----
        if duration <= 0:
            duration = 0.0001  # prevents zero-duration instability

        proto = self._normalize_str(r.get("proto"))
        service = self._normalize_str(r.get("service"))
        conn_state = self._normalize_str(r.get("conn_state"))

        src_bytes = self._safe_int(r.get("orig_bytes"))
        dst_bytes = self._safe_int(r.get("resp_bytes"))

        missed_bytes = self._safe_int(r.get("missed_bytes"))

        src_pkts = self._safe_int(r.get("orig_pkts"))
        dst_pkts = self._safe_int(r.get("resp_pkts"))

        src_ip_bytes = self._safe_int(r.get("orig_ip_bytes"))
        dst_ip_bytes = self._safe_int(r.get("resp_ip_bytes"))

        # ---- Derived features (CRITICAL) ----
        total_bytes = src_bytes + dst_bytes

        byte_ratio = src_bytes / (dst_bytes + 1)  # avoid division by zero
        pkt_ratio = src_pkts / (dst_pkts + 1)

        return {
            "duration": duration,
            "proto": proto,
            "service": service,

            "src_bytes": src_bytes,
            "dst_bytes": dst_bytes,
            "total_bytes": total_bytes,

            "byte_ratio": byte_ratio,

            "conn_state": conn_state,

            "missed_bytes": missed_bytes,

            "src_pkts": src_pkts,
            "dst_pkts": dst_pkts,
            "pkt_ratio": pkt_ratio,

            "src_ip_bytes": src_ip_bytes,
            "dst_ip_bytes": dst_ip_bytes
        }

    # ------------------------------
    # CONTRACT ENFORCEMENT
    # ------------------------------
    def _enforce_contract(self, features: Dict[str, Any]) -> Dict[str, Any]:

        final = {}

        for key in self.feature_keys:
            val = features.get(key)

            if val in [None, "", "-"]:
                final[key] = DEFAULTS.get(key, 0)
            else:
                final[key] = val

        if self.debug:
            self._debug_check(final)

        return final

    # ------------------------------
    # DEBUG VALIDATION
    # ------------------------------
    def _debug_check(self, features: Dict[str, Any]):

        if set(features.keys()) != set(self.feature_keys):
            print("[WARNING] Feature mismatch detected")

    # ------------------------------
    # SAFE HELPERS
    # ------------------------------
    def _safe_float(self, value: Any) -> float:
        try:
            if value in [None, "", "-"]:
                return 0.0
            return float(value)
        except:
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            if value in [None, "", "-"]:
                return 0
            return int(float(value))
        except:
            return 0

    def _normalize_str(self, value: Any) -> str:
        if value in [None, "", "-"]:
            return "unknown"
        return str(value).lower()


# ------------------------------
# BATCH MODE
# ------------------------------
def build_feature_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    builder = FeatureBuilder()
    return [builder.build_features(r) for r in records]


# ------------------------------
# TEST
# ------------------------------
if __name__ == "__main__":

    sample = {
        "duration": "0.11",
        "proto": "tcp",
        "service": "http",
        "orig_bytes": "1200",
        "resp_bytes": "3000",
        "conn_state": "SF",
        "orig_pkts": "10",
        "resp_pkts": "12",
        "orig_ip_bytes": "1400",
        "resp_ip_bytes": "3200",
        "missed_bytes": "0"
    }

    fb = FeatureBuilder(debug=True)
    print(fb.build_features(sample))