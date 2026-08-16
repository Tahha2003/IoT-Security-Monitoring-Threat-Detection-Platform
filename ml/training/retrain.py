"""
Retrain — Phase 9
Loads base dataset + fp_dataset.csv, retrains both models, hot-swaps pkl files.
Pipeline picks up new models on next infer() call — no restart needed.
"""

import os
import sys
import joblib
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from ml.features.feature_builder import FeatureBuilder
from ml.features.feature_preprocessor import FeaturePreprocessor

BASE_CSV   = os.path.join(PROJECT_ROOT, "ml/datasets/balanced_dataset.csv")
FP_CSV     = os.path.join(PROJECT_ROOT, "ml/datasets/fp_dataset.csv")
MODELS_DIR = os.path.join(PROJECT_ROOT, "ml/training/models")

def load_data():
    df = pd.read_csv(BASE_CSV)

    # safely concat fp_dataset if non-empty
    if os.path.exists(FP_CSV):
        fp = pd.read_csv(FP_CSV)
        if len(fp) > 0:
            df = pd.concat([df, fp], ignore_index=True).drop_duplicates()
            print(f"[+] FP dataset merged: {len(fp)} rows")
        else:
            print("[*] fp_dataset.csv is empty — skipping merge")
    else:
        print("[*] fp_dataset.csv not found — skipping merge")

    return df


def main():
    print("[*] Retrain starting...")

    df = load_data()
    fb = FeatureBuilder()

    X, y = [], []
    for _, row in df.iterrows():
        features = fb.build_features(row.to_dict())
        X.append(features)
        y.append(int(row.get("label", 0)))

    print(f"[+] Dataset: {len(X)} samples")

    pp = FeaturePreprocessor()
    pp.fit(X)
    X_proc = pp.transform_batch(X)

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=12,
        random_state=42, class_weight="balanced"
    )
    rf.fit(X_proc, y)

    iso = IsolationForest(
        n_estimators=200, contamination=0.2, random_state=42
    )
    iso.fit(X_proc)

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(pp,  os.path.join(MODELS_DIR, "preprocessor.pkl"))
    joblib.dump(rf,  os.path.join(MODELS_DIR, "rf_model.pkl"))
    joblib.dump(iso, os.path.join(MODELS_DIR, "iso_model.pkl"))

    print("[✔] Models retrained and saved — pipeline will hot-swap on next infer()")


if __name__ == "__main__":
    main()
