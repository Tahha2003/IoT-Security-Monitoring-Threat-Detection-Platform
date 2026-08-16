import os
import sys
import pandas as pd

# --------------------------
# FIX PYTHON PATH
# --------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --------------------------
# IMPORTS
# --------------------------
from ml.features.feature_builder import FeatureBuilder
from ml.configs.feature_contract import LOCKED_FEATURE_KEYS

# --------------------------
# DATA PATH (UPDATED)
# --------------------------
DATA_PATH = "/home/tahha/iot-threat-detection/ml/datasets/balanced_dataset.csv"

# --------------------------
# LOAD DATASET
# --------------------------
df = pd.read_csv(DATA_PATH)

# Drop completely empty rows
df = df.dropna(how="all")

fb = FeatureBuilder()

X = []
y = []

valid_rows = 0
skipped_rows = 0

# --------------------------
# LABEL NORMALIZATION
# --------------------------
def normalize_label(label):
    if str(label).strip().upper() in ["1", "MALICIOUS", "ATTACK"]:
        return 1
    return 0


# --------------------------
# BUILD DATASET
# --------------------------
for _, row in df.iterrows():

    try:
        label = normalize_label(row.get("label"))

        # ---- build features ----
        features = fb.build_features(row.to_dict())

        # ---- sanity check ----
        if not isinstance(features, dict) or len(features) == 0:
            skipped_rows += 1
            continue

        # ---- enforce feature contract (CRITICAL) ----
        clean_features = {}
        for key in LOCKED_FEATURE_KEYS:
            clean_features[key] = features.get(key, 0)

        # ✅ STRICT VALIDATION (NEW)
        if any(v is None for v in clean_features.values()):
            skipped_rows += 1
            continue

        X.append(clean_features)
        y.append(label)

        valid_rows += 1

    except Exception as e:
        skipped_rows += 1
        continue


# --------------------------
# DATASET VALIDATION
# --------------------------
if valid_rows == 0:
    raise Exception("❌ No valid rows — dataset is broken!")

# --------------------------
# DATASET STATS
# --------------------------
total = len(df)
malicious = sum(y)
normal = len(y) - malicious

print("\n[📊 DATASET SUMMARY]")
print(f"Total rows       : {total}")
print(f"Valid rows       : {valid_rows}")
print(f"Skipped rows     : {skipped_rows}")
print(f"Normal samples   : {normal}")
print(f"Malicious samples: {malicious}")

if len(y) > 0:
    ratio = malicious / len(y)
    print(f"Malicious Ratio  : {ratio:.2f}")

# --------------------------
# FEATURE CONSISTENCY CHECK
# --------------------------
if len(X) > 0:
    feature_len = len(X[0])
    expected_len = len(LOCKED_FEATURE_KEYS)

    print("\n[🔍 FEATURE CHECK]")
    print(f"Feature length   : {feature_len}")
    print(f"Expected length  : {expected_len}")

    if feature_len != expected_len:
        raise Exception("❌ Feature mismatch — contract broken!")

# --------------------------
# DISTRIBUTION CHECK (NEW)
# --------------------------
import collections

proto_dist = collections.Counter([x["proto"] for x in X])
service_dist = collections.Counter([x["service"] for x in X])

print("\n[📡 PROTO DISTRIBUTION]")
print(proto_dist)

print("\n[📡 SERVICE DISTRIBUTION]")
print(service_dist)

# --------------------------
# FINAL OUTPUT
# --------------------------
print(f"\n[✔] Features built successfully: {len(X)} samples")
