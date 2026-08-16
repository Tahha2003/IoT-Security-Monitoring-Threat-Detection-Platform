import threading
import time

from services.flow_service.pipeline_runner import main as phase3_main
from services.flow_service.core.bridge import FlowBridge
from services.flow_service.state import ML_QUEUE

# ---------------------------
# PHASE 4 WORKER INSIDE SAME SYSTEM
# ---------------------------
class MLProcessor:

    def __init__(self):
        self.bridge = FlowBridge()

    def run(self):
        print("[✔] ML Processor Started")

        while True:
            try:
                # FIX: deque has no .empty() or .get() — use len() and .popleft()
                if len(ML_QUEUE) > 0:
                    flow = ML_QUEUE.popleft()

                    result = self.bridge.process(flow)

                    print("\n[ML INPUT]", flow)
                    print("[ML OUTPUT]", result["result"])
                    print("-" * 50)

                else:
                    time.sleep(0.5)

            except Exception as e:
                print("[ML ERROR]", e)
                time.sleep(1)


# ---------------------------
# START EVERYTHING
# ---------------------------
def main():

    print("[✔] UNIFIED PIPELINE STARTING...")

    # Phase 3 (network + zeek + parser + dashboard)
    threading.Thread(target=phase3_main, daemon=True).start()

    # Phase 4 (ML inference)
    ml = MLProcessor()
    threading.Thread(target=ml.run, daemon=True).start()

    # keep alive
    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()
