# Phase 1 Execution Checklist

## Hardware Setup
- [ ] ESP32 available
- [ ] DHT22 attached to ESP32
- [ ] Raspberry Pi available
- [ ] Pi Camera attached to Raspberry Pi
- [ ] Backend machine ready
- [ ] Kali machine ready

## Static IP Lock
- [ ] Raspberry Pi static IP set to 192.168.1.10
- [ ] Backend static IP set to 192.168.1.20
- [ ] Kali static IP set to 192.168.1.30
- [ ] ESP32 target IP locked as 192.168.1.10
- [ ] ESP32 operational IP planned as 192.168.1.40

## Network Setup
- [ ] Raspberry Pi hostapd AP working
- [ ] ESP32 can connect to Pi AP
- [ ] Raspberry Pi connected to managed switch
- [ ] Backend connected to managed switch
- [ ] Kali connected to managed switch

## Connectivity Verification
- [ ] Backend can ping Raspberry Pi
- [ ] Raspberry Pi can ping backend
- [ ] Kali can ping Raspberry Pi
- [ ] Kali can ping backend
- [ ] ESP32 AP connection confirmed

## SPAN / Port Mirroring
- [ ] Switch SPAN session configured
- [ ] Source port 1 = G0/1 (Pi)
- [ ] Source port 2 = G0/2 (Kali)
- [ ] Destination port = G0/3 (Backend)
- [ ] `show monitor session 1` confirms exactly 2 source ports

## Device Live Verification
- [ ] ESP32 HTTP POST flow confirmed
- [ ] Pi Camera initialized
- [ ] Pi Camera local stream confirmed

## Documentation
- [ ] phase1_topology.md completed
- [ ] device_ip_map.md completed
- [ ] edge_architecture_note.md completed
- [ ] phase1_execution_checklist.md completed

## Lock
- [ ] No hardware changes after this
- [ ] Phase 1 Complete
This is now much closer to your roadmap.
