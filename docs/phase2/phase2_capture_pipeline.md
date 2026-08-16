# Phase 2 — Raspberry Pi Capture Pipeline

## Objective
This phase establishes the Raspberry Pi as a lightweight packet capture and forwarding node.

---

## Responsibilities of Raspberry Pi
- Capture live packets from network interface
- Apply kernel-level BPF filtering
- Forward raw PCAP byte stream to backend over TCP
- Perform zero packet parsing or analysis
- Perform zero local PCAP disk writes

---

## Capture Flow

Network Interface (Pi)
        ↓
tcpdump (kernel-level BPF)
        ↓
stdout binary PCAP stream
        ↓
netcat TCP pipe
        ↓
Backend:9000

---

## Design Rules
- No .pcap files stored on Pi SD card
- No packet transformation on Pi
- No analysis on Pi
- Reconnect automatically if backend is unavailable

---

## Output Format
Raw binary PCAP stream:
- libpcap global header
- per-packet headers
- packet payload bytes

---

## Failure Handling
If backend connection drops:
- tcpdump + netcat pipeline must auto-restart
- reconnect loop must retry every 2 seconds

---

## Status
Phase 2 Status: ACTIVE
