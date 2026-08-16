"""
DPI QUEUE (Phase 5 Input Queue)

Purpose:
- Receives ONLY suspicious flows (send_to_dpi=True)
- Feeds DPI Engine (Suricata)
- Handles slow processing safely
- Prevents overload of DPI system

Aligned with:
Phase 4 → Phase 5 pipeline
"""

from queue import Queue, Full, Empty
import time


class DPIQueue:

    def __init__(self, max_size=3000, timeout=10):
        """
        max_size: prevent overload
        timeout: max wait time for DPI processing
        """
        self.queue = Queue(maxsize=max_size)
        self.timeout = timeout

    # ------------------------------
    # ADD FLOW (FROM QUEUE 3)
    # ------------------------------
    def put(self, flow: dict):
        """
        Only suspicious flows should reach here
        """

        if not flow.get("send_to_dpi", False):
            return  # safety guard

        try:
            flow["dpi_enqueue_time"] = time.time()
            self.queue.put(flow, timeout=0.2)

        except Full:
            print("[WARNING] DPI_QUEUE FULL - dropping suspicious flow")

    # ------------------------------
    # GET FLOW (FOR DPI ENGINE)
    # ------------------------------
    def get(self):
        """
        Blocking fetch for DPI worker
        """

        try:
            flow = self.queue.get(timeout=1)

            # latency tracking
            now = time.time()
            flow["dpi_queue_delay"] = now - flow.get("dpi_enqueue_time", now)

            return flow

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
    # MONITORING
    # ------------------------------
    def size(self):
        return self.queue.qsize()

    def is_full(self):
        return self.queue.full()

    def is_empty(self):
        return self.queue.empty()
