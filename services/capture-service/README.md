# Capture Service

The capture service provides the queue infrastructure and helper scripts that sit alongside the main PCAP ingestion path. Raw packet capture from the network is handled by the Raspberry Pi edge node — the Pi runs `tcpdump` on its SPAN-connected `eth0` interface and streams the raw PCAP bytes to the backend over TCP port 9000.

---

## Role in the Architecture

```
Managed Switch (SPAN configured)
        │  mirrors all source-port traffic
        ▼
Raspberry Pi — eth0 (192.168.2.106)
        │  sudo tcpdump -i eth0 | socat → TCP:192.168.50.21:9000
        ▼
Backend PC — wlxe009bf6913de (192.168.50.21) — IOT-LAB IP
        │  TCP:9000
        ▼
packet_listener.py (flow_service T1) — writes /tmp/live.pcap → QUEUE_1
        │
        ▼
Capture Service (queue_writer, raw_logger, health_check)
```

The main PCAP ingestion is handled by `packet_listener.py` in `flow_service`. This service provides supporting infrastructure: the shared in-memory queue, raw disk logging, and health monitoring.

---

## Structure

```
capture-service/
├── configs/
│   └── capture_settings.yaml   # Queue settings, MQTT toggle (disabled)
├── scripts/
│   ├── queue_writer.py         # Thread-safe in-memory queue (shared across ingest)
│   ├── sensor_ingest.py        # Queue consumer loop (Phase 2 scaffold)
│   ├── mqtt_subscriber.py      # MQTT subscriber — disabled in current testbed
│   ├── raw_logger.py           # Writes raw captured bytes to disk
│   └── health_check.py         # Ingest pipeline health monitoring
└── README.md
```

---

## Scripts

### `queue_writer.py`
Thread-safe `collections.deque`-based queue acting as the buffer between the network ingest path and downstream consumers. Used by `sensor_ingest.py` and `raw_logger.py`. `maxlen` is configured via `capture_settings.yaml`.

### `sensor_ingest.py`
Consumer loop that polls the shared queue and processes items. Phase 2 scaffold — full processing is delegated to the main pipeline in `flow_service`. This module is retained for auxiliary queue consumers (e.g., secondary loggers or forwarding agents).

### `raw_logger.py`
Writes raw captured bytes from the queue to timestamped PCAP files on disk. Useful for recording attack traffic for offline ML retraining sessions. Output path: `logs/capture/raw/`.

### `health_check.py`
Monitors ingest pipeline health — checks queue depth, TCP connection status, and logs warnings if the stream from the Raspberry Pi drops or stalls.

### `mqtt_subscriber.py`
Placeholder for MQTT-based device ingest. **Disabled** in the current testbed (`mqtt.enabled: false` in `capture_settings.yaml`). The testbed uses direct PCAP streaming over TCP, not MQTT. Retained for future IoT protocol support.

---

## Configuration (`configs/capture_settings.yaml`)

```yaml
mqtt:
  enabled: false        # MQTT not used in current architecture

queue:
  maxlen: 10000         # Max items in the in-memory buffer before oldest are dropped
```

---

## Raspberry Pi Capture Setup

### How the Pi streams traffic to the backend

On the Raspberry Pi, `~/edge/capture/capture.sh` runs:

```bash
#!/bin/bash
# BACKEND_IP = backend's IOT-LAB interface IP (wlxe009bf6913de)
# Check with: ip addr show wlxe009bf6913de | grep inet
BACKEND_IP="192.168.50.21"
BACKEND_PORT="9000"
RECONNECT_DELAY="3"

sudo tc qdisc del dev eth0 ingress 2>/dev/null || true
sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[CAPTURE] SPAN eth0 → $BACKEND_IP:$BACKEND_PORT"
while true; do
    sudo tcpdump -i eth0 -B 4096 -s 0 -U -w - \
        'host 192.168.50.10 or host 192.168.50.40 or host 192.168.2.101' \
        2>/dev/null | \
    socat - TCP:$BACKEND_IP:$BACKEND_PORT,retry=999,interval=3,keepalive,keepidle=10,keepintvl=5,keepcnt=3
    sleep "$RECONNECT_DELAY"
done
```

**Key points:**
- `eth0` on the Pi is connected to the SPAN destination port of the managed switch — it receives a copy of all traffic from source ports
- `BACKEND_IP` must be the backend's **IOT-LAB IP** (`192.168.50.21`), not its wired IP, because the Pi reaches the backend via the IOT-LAB WiFi subnet
- The BPF filter `'host 192.168.50.10 or host 192.168.50.40 or host 192.168.2.101'` restricts the stream to monitored device traffic (Camera, BYOD, Backend). Update these IPs whenever devices change
- The `while true` loop with `socat retry=999` ensures the stream auto-reconnects if the TCP connection drops

### Finding BACKEND_IP

The backend has two relevant IPs:
- `192.168.2.101` — wired, reachable from the switch
- `192.168.50.21` — IOT-LAB WiFi, reachable from the Pi

The Pi connects via the IOT-LAB WiFi route, so `BACKEND_IP` must be the `192.168.50.21` address. Verify it before each session:

```bash
# On backend PC:
ip addr show wlxe009bf6913de | grep "inet "
```

---

## Monitored Devices

All traffic from the following devices flows through the SPAN port:

| Device | IP | Connection | Role |
|--------|----|------------|------|
| WiFi Camera | 192.168.50.10 | Wireless → Router → Switch | Monitored IoT device |
| BYOD Mobile | 192.168.50.40 | Wireless → Router → Switch | Monitored IoT device |
| Backend PC | 192.168.2.101 | Wired → Switch | Detection engine (mirrored source) |
| Kali Linux | 192.168.2.x | Wired → Switch | Testbed operator / attack node |
| WiFi Router | (uplink port) | Wired → Switch | Gateway (mirrored source) |

---

## Pi SSH Access

The Pi is reachable via the IOT-LAB WiFi subnet:

```bash
# Add route on backend if not present
sudo ip route add 192.168.50.0/24 dev wlxe009bf6913de

# SSH in
ssh pi@192.168.50.1

# Start capture
bash ~/edge/capture/capture.sh
```

---

## Logs

| Log File | Contents |
|----------|----------|
| `logs/capture/sensor_ingest.log` | Queue consumer activity |
| `logs/capture/raw/*.pcap` | Raw captured byte dumps (from raw_logger) |
| `logs/pipeline/packet_listener.log` | TCP connection events from the Pi (flow_service T1) |
