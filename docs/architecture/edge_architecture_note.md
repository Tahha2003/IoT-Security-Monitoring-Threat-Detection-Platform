# Edge Architecture Note

## Purpose
This document explains the role of the Raspberry Pi in the IoT threat detection platform.

---

## Raspberry Pi Role Summary

The Raspberry Pi serves as:

1. Controlled Access Point (AP)
2. Edge Traffic Visibility Node
3. IoT Gateway
4. Pi Camera Host
5. Future Packet Capture Source

---

## Why Raspberry Pi is Used as AP

Using Raspberry Pi as the access point ensures:

- controlled traffic routing
- direct visibility into IoT device communication
- easier packet capture
- safer local lab simulation
- consistent traffic observation point

---

## Traffic Path

ESP32 → Raspberry Pi AP → Backend Machine

This ensures the monitored IoT endpoint is always observed through the edge node.

---

## Phase 1 Scope

In Phase 1, Raspberry Pi is only required to:
- host AP successfully
- allow ESP32 connection
- maintain backend communication
- remain stable as the edge node

Packet capture and forwarding implementation will begin in later phases.
