# Device IP Mapping

## Network Details
SSID: RaspberryPi-AP
Gateway IP: 192.168.10.110  # removed........
Subnet: 192.168.10.0/24

---

## Devices

### ESP32 + DHT22
Role: Monitored IoT Endpoint
Hostname: esp32-iot-node
IP Address: 192.168.50.4=30

---

### Raspberry Pi
Role: AP + Edge Monitor
Hostname: rpi-edge-node
AP Interface IP: 192.168.1.10
Switch Port: G0/1

---

### Backend Machine / Laptop
Role: Detection + Dashboard Server
Hostname: backend-server
IP Address: 192.168.1.20
Switch Port: G0/3
SPAN Role: Destination Port

---

### Kali Machine
Role: Traffic Simulation / Controlled Attack Source
Hostname: kali-lab-node
IP Address: 192.168.1.30
Switch Port: G0/2
SPAN Role: Source Port

---

## Optional Module

### Pi Camera
Role: Contextual Visual Monitoring Module
Connection Type: Attached to Raspberry Pi CSI/Camera Interface

---

## Notes
- ESP32 connects only through Raspberry Pi AP
- Raspberry Pi and Kali are mirrored to Backend via SPAN
- Backend receives mirrored raw Ethernet traffic on switch destination port
This now matches your roadmap.
