import time
import random

from services.flow_service.core.bridge import FlowBridge
from services.flow_service.state import ML_QUEUE

class RealtimePipeline:

    def __init__(self):

        self.bridge = FlowBridge()

        print("[✔] Realtime Pipeline Started")

    # --------------------------
    # SIMULATED STREAM (REPLACE LATER WITH ZEEK INPUT)
    # --------------------------
    def generate_fake_zeek(self):

        return {
            "duration": round(random.uniform(0.01, 5.0), 2),
            "proto": random.choice(["tcp", "udp"]),
            "service": random.choice(["http", "dns", "mqtt", "-"]),
            "orig_bytes": random.randint(10, 5000),
            "resp_bytes": random.randint(10, 5000),
            "conn_state": random.choice(["SF", "S0", "REJ"]),
            "missed_bytes": 0,
            "orig_pkts": random.randint(1, 20),
            "resp_pkts": random.randint(1, 20),
            "orig_ip_bytes": random.randint(50, 8000)
        }

    # --------------------------
    # RUN LOOP
    # --------------------------
    def run(self):

        print("[✔] Streaming started...\n")

        while True:

            # FIX: deque has no .empty() or .get() — use len() and .popleft()
            if len(ML_QUEUE) > 0:

                zeek_record = ML_QUEUE.popleft()

                output = self.bridge.process(zeek_record)

                print("ZEEK INPUT:", zeek_record)
                print("ML OUTPUT:", output["result"])
                print("-" * 60)

            else:
                time.sleep(1)


# --------------------------
# MAIN ENTRY
# --------------------------
if __name__ == "__main__":

    pipeline = RealtimePipeline()
    pipeline.run()
