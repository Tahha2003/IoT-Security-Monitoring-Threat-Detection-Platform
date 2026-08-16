"""
Feature Preprocessor - Production Version (v3 aligned)
- Converts FeatureBuilder output → ML vector
- Handles encoding + scaling
- Fully aligned with feature_contract v3.0.0
"""

from typing import Dict, List, Any
import joblib
import math
from ml.configs.feature_contract import LOCKED_FEATURE_KEYS


class FeaturePreprocessor:

    def __init__(self):
        self.feature_keys = LOCKED_FEATURE_KEYS

        # learned mappings
        self.proto_map = {}
        self.service_map = {}
        self.conn_state_map = {}

        # stats for scaling
        self.means = {}
        self.stds = {}

        self.fitted = False

    # --------------------------
    # FIT (TRAINING ONLY)
    # --------------------------
    def fit(self, X: List[Dict[str, Any]]):

        numeric_keys = [
            "duration",
            "src_bytes",
            "dst_bytes",
            "total_bytes",
            "byte_ratio",
            "missed_bytes",
            "src_pkts",
            "dst_pkts",
            "pkt_ratio",
            "src_ip_bytes",
            "dst_ip_bytes"
        ]

        # ---- categorical encoding build ----
        proto_set = set()
        service_set = set()
        conn_set = set()

        for row in X:
            proto_set.add(row.get("proto", "unknown"))
            service_set.add(row.get("service", "unknown"))
            conn_set.add(row.get("conn_state", "unknown"))

        # ✅ CRITICAL: ensure "unknown" always exists
        proto_set.add("unknown")
        service_set.add("unknown")
        conn_set.add("unknown")

        self.proto_map = {v: i for i, v in enumerate(sorted(proto_set), start=1)}
        self.service_map = {v: i for i, v in enumerate(sorted(service_set), start=1)}
        self.conn_state_map = {v: i for i, v in enumerate(sorted(conn_set), start=1)}

        # ---- compute mean/std (robust) ----
        for key in numeric_keys:
            values = [self._safe_float(row.get(key, 0)) for row in X]

            if len(values) == 0:
                self.means[key] = 0.0
                self.stds[key] = 1.0
                continue

            mean = sum(values) / len(values)
            var = sum((x - mean) ** 2 for x in values) / len(values)

            self.means[key] = mean
            self.stds[key] = math.sqrt(var) if var > 0 else 1.0

        self.fitted = True

    # --------------------------
    # TRANSFORM SINGLE SAMPLE
    # --------------------------
    def transform(self, row: Dict[str, Any]) -> List[float]:

        if not self.fitted:
            raise Exception("Preprocessor not fitted!")

        vector = []

        for key in self.feature_keys:

            val = row.get(key, 0)

            # ---- categorical (SAFE FALLBACK FIX) ----
            if key == "proto":
                vector.append(self.proto_map.get(val, self.proto_map.get("unknown", 0)))

            elif key == "service":
                vector.append(self.service_map.get(val, self.service_map.get("unknown", 0)))

            elif key == "conn_state":
                vector.append(self.conn_state_map.get(val, self.conn_state_map.get("unknown", 0)))

            # ---- numeric (scaled) ----
            else:
                mean = self.means.get(key, 0)
                std = self.stds.get(key, 1)

                try:
                    val = self._safe_float(val)
                    scaled = (val - mean) / std
                except:
                    scaled = 0.0

                vector.append(scaled)

        return vector

    # --------------------------
    # BATCH TRANSFORM
    # --------------------------
    def transform_batch(self, X: List[Dict[str, Any]]) -> List[List[float]]:
        return [self.transform(x) for x in X]

    # --------------------------
    # SAFE FLOAT HELPER
    # --------------------------
    def _safe_float(self, value: Any) -> float:
        try:
            if value in [None, "", "-"]:
                return 0.0
            return float(value)
        except:
            return 0.0


# --------------------------
# SAVE / LOAD (IMPORTANT)
# --------------------------
def save_preprocessor(preprocessor, path="preprocessor.pkl"):
    joblib.dump(preprocessor, path)


def load_preprocessor(path="preprocessor.pkl"):
    return joblib.load(path)