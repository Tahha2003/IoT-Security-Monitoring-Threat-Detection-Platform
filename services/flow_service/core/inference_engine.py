"""
Inference Engine — Phase 4
Loads RF + Isolation Forest models and runs predictions.
Models are loaded once at startup and reused for every flow.
Hot-swap: retrain.py overwrites .pkl files — next predict() call loads new models
          (handled by reload() method called from main_pipeline on SIGHUP if needed).
"""

import os
import sys
import joblib
import numpy as np

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", )
)
sys.path.insert(0, PROJECT_ROOT)

MODELS_DIR = os.path.join(PROJECT_ROOT, "ml", "training", "models")


class InferenceEngine:

    def __init__(self):
        self._load_models()

    def _load_models(self):
        rf_path  = os.path.join(MODELS_DIR, "rf_model.pkl")
        iso_path = os.path.join(MODELS_DIR, "iso_model.pkl")
        pp_path  = os.path.join(MODELS_DIR, "preprocessor.pkl")

        for p in [rf_path, iso_path, pp_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(
                    f"[InferenceEngine] Model not found: {p}\n"
                    f"Run: python3 ml/training/model_training.py first"
                )

        self.rf           = joblib.load(rf_path)
        self.iso          = joblib.load(iso_path)
        self.preprocessor = joblib.load(pp_path)
        print(f"[✔] InferenceEngine loaded models from {MODELS_DIR}")

    def reload(self):
        """Hot-swap models after retrain — no pipeline restart needed."""
        self._load_models()
        print("[✔] InferenceEngine: models hot-swapped")

    def predict(self, feature_dict: dict) -> dict:
        """
        Returns:
            {label: 0|1, status: NORMAL|ATTACK, rf: 0|1, iso: 1|-1,
             rf_proba: float}  ← rf_proba used by risk_scorer
        """
        X = self.preprocessor.transform_batch([feature_dict])

        rf_pred  = self.rf.predict(X)[0]
        iso_pred = self.iso.predict(X)[0]

        # get probability for risk scoring (more granular than 0/1)
        try:
            rf_proba = float(self.rf.predict_proba(X)[0][1])
        except Exception:
            rf_proba = float(rf_pred)

        is_attack = (rf_pred == 1) or (iso_pred == -1)

        return {
            "label":    int(is_attack),
            "status":   "ATTACK" if is_attack else "NORMAL",
            "rf":       int(rf_pred),
            "iso":      int(iso_pred),
            "rf_proba": rf_proba,   # continuous 0.0–1.0
        }

    def predict_batch(self, feature_list: list) -> list:
        return [self.predict(f) for f in feature_list]
