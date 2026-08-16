# Phase 1 Data Format Lock

## ESP32 → Raspberry Pi Telemetry Format

Protocol: HTTP POST  
Destination: Raspberry Pi  
Port: 80  
Content-Type: application/json

### JSON Body
```json
{
  "device_id": "esp32-001",
  "temperature": 28.5,
  "humidity": 64.2,
  "timestamp": "2026-03-27T15:30:00Z"
}
