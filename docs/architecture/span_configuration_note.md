# SPAN Configuration Note

## Objective
This document records the switch SPAN (port mirroring) setup used in the IoT threat detection lab.

---

## SPAN Session

### Source Ports
- G0/1 = Raspberry Pi
- G0/11 = Kali Machine

### Destination Port
- G0/3 = Backend Machine

---

## Purpose

The SPAN session mirrors traffic from the Raspberry Pi and Kali machine to the backend machine for packet capture and analysis.

This enables the backend to observe raw Layer 2 traffic without being inline in the forwarding path.

---

## Verification Command

```bash
show monitor session 1
