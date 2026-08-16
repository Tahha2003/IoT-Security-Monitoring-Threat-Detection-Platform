# services/flow-service/__init__.py

"""
Flow-Service Package Initialization

Provides clean access to shared objects across Phase 3 pipeline.
No side effects (no logging config here).
"""

# ---------------------------
# Expose shared core objects
# ---------------------------
from .state import QUEUE_1
from services.flow_service.state import ML_QUEUE
from ml.configs.feature_contract import LOCKED_FEATURE_KEYS
# ---------------------------
# Metadata
# ---------------------------
__version__ = "1.0.0"
__author__ = "FYP IoT Threat Detection Team"

# ---------------------------
# NOTE:
# Do NOT configure logging here.
# Logging must be handled inside each module independently.
# ---------------------------
