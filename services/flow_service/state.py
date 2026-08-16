# services/flow-service/state.py

import threading
import time
from collections import deque
from queue import Queue

# ---------------------------
# Packet Queue (Thread-safe custom deque)
# ---------------------------
class PacketQueue:
    def __init__(self, maxlen=50000):
        self.queue = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def append(self, data):
        with self.lock:
            self.queue.append(data)

    def popleft(self):
        with self.lock:
            if len(self.queue) > 0:
                return self.queue.popleft()
            return None

    def pop_all(self):
        with self.lock:
            data = list(self.queue)
            self.queue.clear()
            return data

    def __len__(self):
        with self.lock:
            return len(self.queue)

    def __bool__(self):
        with self.lock:
            return len(self.queue) > 0


# ---------------------------
# GLOBAL QUEUES (SOURCE OF TRUTH)
# ---------------------------

# Raw packet ingestion (PCAP chunks)
QUEUE_1 = PacketQueue(maxlen=50000)

# ML pipeline queue (THREAD SAFE)
ML_QUEUE = PacketQueue(maxlen=50000)

# Final SIEM / results queue
RESULT_QUEUE = Queue(maxsize=100000)


# ---------------------------
# SYSTEM STATE
# ---------------------------
class SystemState:
    def __init__(self):
        self._lock = threading.Lock()
        self.running = True
        self.last_zeek_run = 0.0

    def set_running(self, value: bool):
        with self._lock:
            self.running = value

    def get_running(self):
        with self._lock:
            return self.running

    def update_last_zeek_run(self, ts: float):
        with self._lock:
            self.last_zeek_run = ts

    def get_last_zeek_run(self):
        return self.last_zeek_run


# ---------------------------
# Packet Recall Buffer (Flow → Packet mapping)
# ---------------------------
class PacketRecallBuffer:
    def __init__(self, max_flows=10000, ttl_seconds=300):
        self.buffer = {}
        self.max_flows = max_flows
        self.ttl = ttl_seconds
        self.lock = threading.Lock()
        
    def store_flow_packets(self, flow_uid: str, raw_packets: bytes):
        """Store raw packets associated with a flow UID"""
        with self.lock:
            self.buffer[flow_uid] = {
                "packets": raw_packets,
                "timestamp": time.time()
            }
            # Evict oldest if over max
            if len(self.buffer) > self.max_flows:
                oldest = min(self.buffer.keys(), key=lambda k: self.buffer[k]["timestamp"])
                del self.buffer[oldest]
    
    def get_flow_packets(self, flow_uid: str) -> bytes:
        """Retrieve raw packets for a flow UID"""
        with self.lock:
            entry = self.buffer.get(flow_uid)
            if entry and time.time() - entry["timestamp"] < self.ttl:
                return entry["packets"]
            # Clean up expired entries
            if entry:
                del self.buffer[flow_uid]
            return b""
    
    def cleanup_expired(self):
        """Remove expired entries"""
        with self.lock:
            now = time.time()
            expired = [uid for uid, entry in self.buffer.items() 
                      if now - entry["timestamp"] > self.ttl]
            for uid in expired:
                del self.buffer[uid]


PACKET_RECALL_BUFFER = PacketRecallBuffer()
SYSTEM_STATE = SystemState()
