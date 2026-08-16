"""
Evaluation Metrics — Testing Week
Run after all 5 Kali attack scenarios.
Prints Precision, Recall, F1, ROC-AUC, False Positive Rate.
"""

import sys
import os
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)


def evaluate(y_true, y_pred, y_score=None):
    """
    y_true  : ground truth binary labels (0=normal, 1=attack)
    y_pred  : system binary output
    y_score : continuous risk scores (for ROC-AUC)
    """
    print("\n" + "=" * 55)
    print("  IoT IDS — Evaluation Metrics")
    print("=" * 55)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall    = recall_score(y_true, y_pred, zero_division=0)
    f1        = f1_score(y_true, y_pred, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    print(f"  Precision          : {precision:.4f}")
    print(f"  Recall             : {recall:.4f}")
    print(f"  F1 Score           : {f1:.4f}")
    print(f"  False Positive Rate: {fpr:.4f}")

    if y_score is not None:
        try:
            auc = roc_auc_score(y_true, y_score)
            print(f"  ROC-AUC            : {auc:.4f}")
        except Exception as e:
            print(f"  ROC-AUC            : N/A ({e})")

    print("\n  Confusion Matrix:")
    print(f"    TP={tp}  FP={fp}")
    print(f"    FN={fn}  TN={tn}")

    print("\n  Classification Report:")
    print(classification_report(y_true, y_pred, target_names=["NORMAL", "ATTACK"]))
    print("=" * 55)

    return {"precision": precision, "recall": recall, "f1": f1, "fpr": fpr}


# ---------------------------
# Example usage (replace with real data)
# ---------------------------
if __name__ == "__main__":
    # Replace these with actual ground truth from your test scenarios
    y_true  = [0, 0, 1, 1, 1, 0, 1, 0, 1, 1]
    y_pred  = [0, 0, 1, 1, 0, 0, 1, 1, 1, 1]
    y_score = [0.1, 0.2, 0.9, 0.85, 0.4, 0.15, 0.95, 0.7, 0.88, 0.92]

    evaluate(y_true, y_pred, y_score)
