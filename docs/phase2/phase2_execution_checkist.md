# Phase 2 Execution Checklist

## Kernel Tuning
- [ ] net.core.rmem_max = 33554432 applied
- [ ] net.core.netdev_max_backlog = 5000 applied
- [ ] sysctl settings persisted

## Capture Pipeline
- [ ] BPF filter applied correctly
- [ ] tcpdump captures from correct interface
- [ ] raw PCAP bytes piped to backend:9000
- [ ] zero .pcap files written on Pi

## Reliability
- [ ] reconnect loop implemented
- [ ] reconnect confirmed after backend drop

## Performance
- [ ] Pi CPU under 40% during Kali test
- [ ] no packet file growth on SD card

## Verification
- [ ] backend receives live bytes
- [ ] tcpdump pipeline stable
- [ ] end-to-end stream confirmed

## Documentation
- [ ] phase2_capture_pipeline.md completed
- [ ] phase2_bpf_contract.md completed
- [ ] phase2_execution_checklist.md completed

## Lock
- [ ] Phase 2 Complete
