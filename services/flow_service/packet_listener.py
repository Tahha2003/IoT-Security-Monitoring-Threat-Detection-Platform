import socket
import threading
import logging
import time
import os
import sys
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.flow_service.configs.config import HOST, PORT, BUFFER_SIZE, QUEUE_MAXLEN
from services.flow_service.state import QUEUE_1

os.makedirs("logs/pipeline", exist_ok=True)
_h = RotatingFileHandler("logs/pipeline/packet_listener.log", maxBytes=5*1024*1024, backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger("packet_listener")
logger.addHandler(_h)
logger.setLevel(logging.INFO)

received_packets  = 0
dropped_packets   = 0
backpressure_events = 0


def apply_backpressure(queue_size: int) -> float:
    if queue_size < QUEUE_MAXLEN * 0.5:
        return 0.0
    elif queue_size < QUEUE_MAXLEN * 0.8:
        return 0.01
    else:
        return 0.05


def handle_client(conn, addr):
    global received_packets, dropped_packets, backpressure_events

    logger.info(f"[+] Client connected: {addr}")
    conn.settimeout(120)  # 2 min timeout — handles slow IoT traffic periods

    # Pi sends valid pcap stream — open fresh file, Pi's header comes first
    live_pcap = os.getenv("LIVE_PCAP", "/tmp/live.pcap")
    try:
        # truncate file so Pi's pcap header is always at byte 0
        open(live_pcap, "wb").close()
        logger.info(f"[+] Fresh pcap file ready: {live_pcap}")
    except Exception as e:
        logger.warning(f"[!] Could not truncate pcap: {e}")  # 30s timeout — Pi stream ke liye kaafi

    try:
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                logger.warning(f"[!] Disconnected: {addr}")
                break

            received_packets += 1
            qsize = len(QUEUE_1)

            delay = apply_backpressure(qsize)
            if delay > 0:
                backpressure_events += 1
                time.sleep(delay)

            QUEUE_1.append(data)

    except socket.timeout:
        pass
    except Exception as e:
        logger.error(f"[!] Client error {addr}: {e}")
    finally:
        conn.close()
        logger.info(f"[-] Connection closed: {addr}")


def packet_listener():
    logger.info(f"[*] Listening on {HOST}:{PORT}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)

    try:
        server.bind((HOST, PORT))
        server.listen(20)
        logger.info("[*] Ready for high-throughput IoT streams...")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    except Exception as e:
        logger.critical(f"[!] Listener crashed: {e}")
    finally:
        server.close()


def get_packet_stats():
    return {
        "received":    received_packets,
        "dropped":     dropped_packets,
        "backpressure": backpressure_events,
        "queue_size":  len(QUEUE_1),
    }


if __name__ == "__main__":
    packet_listener()