#!/bin/bash
# ============================================================
# IoT IDS — Firewall Reset Script
# Removes all SOAR-added block/quarantine rules
# Run this before starting a new test session
# ============================================================

echo "[*] Resetting SOAR firewall rules..."

# ── Remove UFW deny rules (block_attacker playbook) ──────────
echo "[1] Removing UFW deny rules..."
sudo ufw delete deny from 192.168.10.130 to any 2>/dev/null && echo "    [✔] Kali unblocked" || echo "    [-] No Kali block found"
sudo ufw delete deny from 192.168.10.101 to any 2>/dev/null && echo "    [✔] Camera unblocked" || echo "    [-] No Camera block found"
sudo ufw delete deny from 192.168.10.102 to any 2>/dev/null && echo "    [✔] BYOD unblocked" || echo "    [-] No BYOD block found"
sudo ufw delete deny from 192.168.10.1   to any 2>/dev/null && echo "    [✔] Router unblocked" || echo "    [-] No Router block found"

# ── Remove iptables FORWARD DROP rules (quarantine playbook) ─
echo "[2] Removing iptables quarantine rules..."
sudo iptables -D FORWARD -s 192.168.10.101 -j DROP 2>/dev/null && echo "    [✔] Camera quarantine removed" || echo "    [-] No Camera quarantine"
sudo iptables -D FORWARD -s 192.168.10.102 -j DROP 2>/dev/null && echo "    [✔] BYOD quarantine removed" || echo "    [-] No BYOD quarantine"
sudo iptables -D FORWARD -s 192.168.10.130 -j DROP 2>/dev/null && echo "    [✔] Kali quarantine removed" || echo "    [-] No Kali quarantine"

# ── Remove iptables rate limit rules (camera_defense playbook) ─
echo "[3] Removing rate limit rules..."
sudo iptables -D FORWARD -s 192.168.10.130 -d 192.168.10.101 -j DROP 2>/dev/null || true
sudo iptables -D INPUT -s 192.168.10.130 -m state --state NEW -j ACCEPT 2>/dev/null || true

# ── Remove iptables INPUT throttle rules (scan_detection) ────
echo "[4] Removing scan throttle rules..."
sudo iptables -D INPUT -s 192.168.10.130 -m state --state NEW -m limit --limit 5/sec --limit-burst 10 -j ACCEPT 2>/dev/null || true

echo ""
echo "[✔] Firewall reset complete — all SOAR rules removed"
echo "[✔] Devices can now communicate freely"
echo ""
echo "Current UFW status:"
sudo ufw status | grep -E "DENY|DROP|Kali|10\.10" || echo "  No block rules active"
