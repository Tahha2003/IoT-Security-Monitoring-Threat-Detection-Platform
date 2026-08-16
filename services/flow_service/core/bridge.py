import sys
import os
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from ml.features.feature_builder import FeatureBuilder
from services.flow_service.core.inference_engine import InferenceEngine


class FlowBridge:
    """
    Phase 3→4 bridge.
    process() returns the event dict — does NOT push to any queue.
    Queue management is handled by main_pipeline.py (T4-ml_inference).
    """

    def __init__(self):
        self.feature_builder = FeatureBuilder()
        self.engine = InferenceEngine()
        print("[✔] FlowBridge Initialized")

    def process(self, raw_zeek_record: dict) -> dict:
        """
        Returns:
            {
                "input":    raw_zeek_record,
                "features": feature_dict,
                "result":   {label, status, rf, iso},
                "timestamp": float
            }
        """

        features = self.feature_builder.build_features(raw_zeek_record)

        # 🔷 FIX 5: REAL-TIME PIPELINE VALIDATION
        if not features or len(features) != len(self.feature_builder.feature_keys):
            return None

        result = self.engine.predict(features)

        return {
            "input":     raw_zeek_record,
            "features":  features,
            "result":    result,          # {label, status, rf, iso}
            "timestamp": time.time(),
        }

    def process_batch(self, records: list) -> list:
        return [self.process(r) for r in records if self.process(r) is not None]