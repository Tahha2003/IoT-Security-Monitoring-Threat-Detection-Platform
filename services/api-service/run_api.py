"""
API Service launcher — avoids hyphenated module path issue.
Called by start_pipeline.sh
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Import app from hyphenated folder via file path
import importlib.util
spec = importlib.util.spec_from_file_location(
    "api_main",
    os.path.join(os.path.dirname(__file__), "app", "main.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
