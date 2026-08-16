"""
RESULT QUEUE (PIPELINE CONTRACT)
Handles flow transfer between Phase 4 → Phase 5

- Thread-safe
- Central pipeline bus
- Supports monitoring
"""

from queue import Queue, Empty, Full


class ResultQueue:

    def __init__(self, max_size=10000):
        self.queue = Queue(maxsize=max_size)

    # ------------------------------
    # ADD FLOW
    # ------------------------------
    def put(self, flow):

        try:
            self.queue.put(flow, timeout=0.2)
        except Full:
            print("[WARNING] RESULT_QUEUE FULL - dropping flow")

    # ------------------------------
    # GET FLOW
    # ------------------------------
    def get(self):

        try:
            return self.queue.get(timeout=0.5)
        except Empty:
            return None

    # ------------------------------
    # NON-BLOCKING GET
    # ------------------------------
    def get_nowait(self):

        try:
            return self.queue.get_nowait()
        except Empty:
            return None

    # ------------------------------
    # SIZE
    # ------------------------------
    def size(self):
        return self.queue.qsize()