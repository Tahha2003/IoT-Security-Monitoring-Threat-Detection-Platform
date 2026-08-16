import time
from services.flow_service.state import QUEUE_1, ML_QUEUE, RESULT_QUEUE

while True:
    print("\n--- QUEUE STATUS ---")
    print("QUEUE_1      :", len(QUEUE_1))
    print("ML_QUEUE     :", len(ML_QUEUE))          # FIX: deque has no .qsize()
    print("RESULT_QUEUE :", RESULT_QUEUE.qsize())   # Queue() has .qsize()
    time.sleep(2)
