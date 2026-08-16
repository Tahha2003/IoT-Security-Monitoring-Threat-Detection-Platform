import React, { useEffect, useState } from "react";
import { fetchAlerts } from "../services/api";

const KNOWN_DEVICES = {
  // ── Real IoT Devices (192.168.50.x) ──────────────────
  "192.168.50.10":  { name: "IP Camera",     icon: "📷", type: "IP Camera"        },
  "192.168.50.40":  { name: "BYOD Mobile",   icon: "📱", type: "BYOD Android"     },
  // ── Backend ───────────────────────────────────────────
  "192.168.1.43":   { name: "Backend",       icon: "🖥️", type: "Detection Engine" },
  "192.168.10.120": { name: "Backend (old)", icon: "🖥️", type: "Detection Engine" },
  // ── Known Attacker ────────────────────────────────────
  "192.168.10.130": { name: "Kali Linux",    icon: "💀", type: "Attack Source"    },
};

function RiskMeter({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "#ff2d2d"
    : pct >= 65 ? "#ff6b00"
    : pct >= 40 ? "#ffd700"
    : "#4caf50";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <div style={{ width: 36, height: 3, background: "#1a1a35", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          width: `${pct}%`, height: "100%",
          background: color,
          boxShadow: `0 0 4px ${color}`,
          borderRadius: 2,
          transition: "width 0.5s ease",
        }} />
      </div>
      <span style={{ fontSize: 10, color, fontFamily: "monospace", fontWeight: 700 }}>{pct}%</span>
    </div>
  );
}

export default function DevicesPanel() {
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchAlerts(500);
        const seen = {};
        res.alerts.forEach(a => {
          if (!a.src_ip) return;
          if (!seen[a.src_ip]) {
            seen[a.src_ip] = { ip: a.src_ip, lastSeen: a.timestamp, alerts: 0, maxRisk: 0 };
          }
          seen[a.src_ip].alerts++;
          seen[a.src_ip].maxRisk = Math.max(seen[a.src_ip].maxRisk, a.risk_score);
          if (a.timestamp > seen[a.src_ip].lastSeen) seen[a.src_ip].lastSeen = a.timestamp;
        });
        setDevices(Object.values(seen).sort((a, b) => b.alerts - a.alerts).slice(0, 8));
      } catch (_) {}
    }
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ maxHeight: 200, overflowY: "auto" }}>
      {devices.map((d, i) => {
        const known = KNOWN_DEVICES[d.ip];
        const riskColor = d.maxRisk >= 0.85 ? "#ff2d2d"
          : d.maxRisk >= 0.65 ? "#ff6b00"
          : d.maxRisk >= 0.40 ? "#ffd700"
          : "#4caf50";

        return (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "7px 0",
            borderBottom: "1px solid #0f0f1e",
            transition: "background 0.2s ease",
          }}
            onMouseEnter={e => e.currentTarget.style.background = "#ffffff05"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            {/* Icon */}
            <div style={{
              width: 32, height: 32, borderRadius: 8, flexShrink: 0,
              background: `${riskColor}18`,
              border: `1px solid ${riskColor}44`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16,
            }}>
              {known?.icon || "🔌"}
            </div>

            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, color: "#ddd", fontWeight: 700, marginBottom: 2 }}>
                {known?.name || d.ip}
              </div>
              <div style={{ fontSize: 10, color: "#444" }}>
                {known?.type || "Unknown"} • <span style={{ color: "#00d4ff88", fontFamily: "monospace" }}>{d.ip}</span>
              </div>
            </div>

            {/* Stats */}
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div style={{
                fontSize: 11, color: riskColor, fontWeight: 700, marginBottom: 3,
              }}>
                {d.alerts} alerts
              </div>
              <RiskMeter score={d.maxRisk} />
            </div>
          </div>
        );
      })}

      {devices.length === 0 && (
        <div style={{
          color: "#2a2a45", fontSize: 12, textAlign: "center", padding: 24,
          display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
        }}>
          <span style={{ fontSize: 24 }}>📡</span>
          <span>No devices detected yet</span>
        </div>
      )}
    </div>
  );
}
