# Phase 1 — Controlled IoT Edge Network & Hardware Infrastructure

## Objective
This document defines the physical and logical deployment topology of the IoT Device Security Monitoring and Threat Detection Platform.

---

## Final System Topology

ESP32 + DHT22
        │
        │  (Wi-Fi via Raspberry Pi hostapd AP)
        ▼
Raspberry Pi (AP + Edge Node + Pi Camera)
        │
        │  Ethernet
        ▼
Managed Switch
   ├── G0/1 = Raspberry Pi
   ├── G0/2 = Kali Machine
   └── G0/3 = Backend Machine (SPAN Destination)
        ▼
Backend Machine (Detection + Dashboard + Storage)

---

## Hardware Components

### 1. ESP32 + DHT22
Role: Real IoT endpoint under monitoring

Purpose:
- Generates legitimate IoT telemetry
- Sends JSON telemetry to Raspberry Pi via HTTP POST
- Used for both normal and abnormal behavioral simulation

Sensor Attached:
- DHT22

---

### 2. Raspberry Pi
Role: Controlled IoT access point and monitored edge node

Purpose:
- Hosts local AP using hostapd
- Receives ESP32 traffic
- Hosts Pi Camera
- Generates mirrored traffic to switch source port for backend observation

---

### 3. Pi Camera
Role: Contextual visual monitoring module

Purpose:
- Provides optional visual context of IoT lab
- Runs local MJPEG stream on Raspberry Pi
- Used for dashboard/demo enhancement
- Not part of primary anomaly detection pipeline in MVP

---

### 4. Backend Machine / Laptop
Role: Central anomaly detection and dashboard server

Purpose:
- Receives mirrored traffic from SPAN destination port
- Runs analysis pipeline
- Stores alerts/logs
- Hosts dashboard/backend services
- Runs future ML-based detection pipeline

---

### 5. Kali Machine
Role: Controlled traffic simulation / attack generation node

Purpose:
- Generates controlled suspicious or test traffic inside the isolated lab
- Included in SPAN source ports for backend capture

---

## Detection Model

### Primary Detection Layer
Network Behavioral Anomaly Detection

### Secondary Context Layer
Telemetry Behavior Monitoring

### Optional Context Layer
Visual Monitoring via Pi Camera

---

## Security Boundary

All anomaly simulation and suspicious traffic generation must remain inside the isolated local lab environment only.

No public targets, external systems, or unauthorized third-party networks are permitted.

---

## Status
Phase 1 Status: LOCKED
Now your topology is roadmap-correct.
