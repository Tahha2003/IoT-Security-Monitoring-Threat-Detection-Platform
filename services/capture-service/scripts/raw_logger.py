# services/capture-service/scripts/raw_logger.py

"""
============================================================
Phase 2 - Backend Raw PCAP Receiver
Project: IoT Device Security Monitoring & Threat Detection
============================================================
"""

import socket
import time
import logging
from pathlib import Path

# ----------------------------
# CONFIGURATION
# ----------------------------
HOST = "0.0.0.0"
PORT = 9000
BUFFER_SIZE = 65536

# 🔥 Increased timeout for Phase 2 stability
SOCKET_TIMEOUT = 60

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG = LOG_DIR / "ingest_errors.log"

# ----------------------------
# LOGGING SETUP
# ----------------------------
logging.basicConfig(
    filename=ERROR_LOG,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

LOG_TAG = "[PHASE2-BACKEND]"

# ----------------------------
# SERVER SETUP
# ----------------------------
def start_server():
    print(f"{LOG_TAG} Starting raw PCAP receiver...")
    print(f"{LOG_TAG} Listening on {HOST}:{PORT}")
    print(f"{LOG_TAG} Waiting for Raspberry Pi connection...\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        while True:
            try:
                conn, addr = server.accept()
                client_ip, client_port = addr

                print(f"{LOG_TAG} [+] Client connected: {client_ip}:{client_port}")
                logging.info(f"Client connected: {client_ip}:{client_port}")

                # 🔥 Timeout fix applied
                conn.settimeout(SOCKET_TIMEOUT)

                total_bytes = 0
                chunk_count = 0
                start_time = time.time()
                last_report = start_time

                with conn:
                    while True:
                        try:
                            data = conn.recv(BUFFER_SIZE)

                            if not data:
                                print(f"{LOG_TAG} [!] Client disconnected cleanly.")
                                logging.info(f"Client disconnected cleanly: {client_ip}:{client_port}")
                                break

                            chunk_count += 1
                            total_bytes += len(data)

                            now = time.time()

                            # 🔥 Smooth progress reporting (every 2 sec)
                            if now - last_report >= 2:
                                elapsed = now - start_time
                                rate_kbps = (total_bytes / 1024) / elapsed if elapsed > 0 else 0

                                print(
                                    f"{LOG_TAG} Stream active | "
                                    f"chunks={chunk_count} | "
                                    f"bytes={total_bytes} | "
                                    f"avg={rate_kbps:.2f} KB/s"
                                )

                                last_report = now

                        except socket.timeout:
                            # 🔥 IMPORTANT: Do NOT kill connection on timeout
                            print(f"{LOG_TAG} [INFO] Waiting for data (no packets yet)...")
                            continue

            except KeyboardInterrupt:
                print(f"\n{LOG_TAG} Stopped by user.")
                logging.info("Receiver stopped by user.")
                break

            except Exception as e:
                print(f"{LOG_TAG} [ERROR] {e}")
                logging.exception(f"Unhandled receiver error: {e}")
                time.sleep(2)


# ----------------------------
# ENTRY POINT
# ----------------------------
if __name__ == "__main__":
    start_server()
