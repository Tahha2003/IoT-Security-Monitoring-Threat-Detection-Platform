import os
import sys
import joblib

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

# --------------------------
# FIX PROJECT ROOT PATH
# --------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

# --------------------------
# IMPORT DATASET
# --------------------------
from ml.training.dataset_preparer import X, y

# --------------------------
# IMPORT PREPROCESSOR
# --------------------------
from ml.features.feature_preprocessor import FeaturePreprocessor

# --------------------------
# STEP 1: TRAIN-TEST SPLIT (CRITICAL)
# --------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.3,
    random_state=42,
    stratify=y
)

# --------------------------
# STEP 2: PREPROCESSOR
# --------------------------
pp = FeaturePreprocessor()
pp.fit(X_train)

os.makedirs("models", exist_ok=True)

joblib.dump(pp, "ml/training/models/preprocessor.pkl")
print("[✔] Preprocessor saved")

# --------------------------
# STEP 3: TRANSFORM DATA
# --------------------------
X_train_p = pp.transform_batch(X_train)
X_test_p = pp.transform_batch(X_test)

# --------------------------
# STEP 4: RANDOM FOREST (IMPROVED)
# --------------------------
rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=18,
    min_samples_split=5,
    random_state=42,
    class_weight="balanced_subsample"
)

rf.fit(X_train_p, y_train)
rf_pred = rf.predict(X_test_p)

# --------------------------
# STEP 5: ISOLATION FOREST (TUNED FOR IoT)
# --------------------------
iso = IsolationForest(
    n_estimators=250,
    contamination=0.15,   # IoT anomaly assumption
    random_state=42
)

iso.fit(X_train_p)
iso_pred = iso.predict(X_test_p)

# --------------------------
# STEP 6: COMBINED ENGINE
# --------------------------
final_preds = []

for i in range(len(X_test_p)):
    is_rf_attack = rf_pred[i] == 1
    is_iso_anomaly = iso_pred[i] == -1

    if is_rf_attack or is_iso_anomaly:
        final_preds.append(1)
    else:
        final_preds.append(0)

# --------------------------
# STEP 7: EVALUATION (REAL)
# --------------------------
print("\n[🔥 FINAL MODEL PERFORMANCE]\n")
print(classification_report(y_test, final_preds))

# --------------------------
# STEP 8: SAVE MODELS
# --------------------------
joblib.dump(rf, "ml/training/models/rf_model.pkl")
joblib.dump(iso, "ml/training/models/iso_model.pkl")

print("\n[✔] Models saved successfully")