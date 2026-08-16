"""
RESULT BUFFER
Acts as intermediate layer before RESULT_QUEUE
Prevents pipeline blocking under high load
"""

from queue import Queue, Full, Empty
import time


class ResultBuffer:

    def __init__(self, max_size=5000):
        self.buffer = Queue(maxsize=max_size)

    # ------------------------------
    # ADD RESULT
    # ------------------------------
    def add(self, flow):

        try:
            self.buffer.put(flow, timeout=0.1)
        except Full:
            print("[WARNING] ResultBuffer FULL - dropping flow")

    # ------------------------------
    # FETCH RESULT
    # ------------------------------
    def get(self):

        try:
            return self.buffer.get(timeout=0.5)
        except Empty:
            return None

    # ------------------------------
    # SIZE MONITOR
    # ------------------------------
    def size(self):
        return self.buffer.qsize()