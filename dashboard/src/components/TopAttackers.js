import React, { useEffect, useState } from "react";
import { fetchAlerts } from "../services/api";

// Human-readable labels for known IPs
const KNOWN = {
  "192.168.50.10":  "IP Camera",
  "192.168.50.40":  "BYOD Mobile",
  "192.168.50.1":   "Pi Gateway",
  "192.168.1.43":   "Backend (self)",
  "192.168.10.120": "Backend (old)",
};

// These are our own infrastructure — exclude from attacker list
const INFRASTRUCTURE_IPS = new Set([
  "192.168.2.101",   // backend (current)
  "192.168.1.43",    // backend (previous WiFi)
  "192.168.10.120",  // stale backend IP still in DB
  "192.168.10.1",    // old router
]);

export default function TopAttackers() {
  const [data, setData] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchAlerts(1000);
        const counts = {};
        const risks  = {};
        res.alerts.forEach(a => {
          if (!a.src_ip) return;
          if (INFRASTRUCTURE_IPS.has(a.src_ip)) return;  // skip self-traffic
          counts[a.src_ip] = (counts[a.src_ip] || 0) + 1;
          risks[a.src_ip]  = Math.max(risks[a.src_ip] || 0, a.risk_score);
        });
        setData(
          Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 7)
            .map(([ip, count]) => ({ ip, count, risk: risks[ip] || 0 }))
        );
      } catch (_) {}
    }
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const max = data[0]?.count || 1;

  return (
    <div>
      {data.map((d, i) => {
        const riskColor = d.risk >= 0.85 ? "#ff2d2d"
          : d.risk >= 0.65 ? "#ff8c00"
          : d.risk >= 0.40 ? "#ffd700" : "#4caf50";
        const barPct = (d.count / max) * 100;
        return (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <div>
                <span style={{ color: "#00d4ff", fontFamily: "monospace", fontSize: 12 }}>{d.ip}</span>
                {KNOWN[d.ip] && (
                  <span style={{ color: "#555", fontSize: 10, marginLeft: 8 }}>({KNOWN[d.ip]})</span>
                )}
              </div>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <span style={{ color: riskColor, fontSize: 11, fontWeight: "bold" }}>
                  risk {(d.risk * 100).toFixed(0)}%
                </span>
                <span style={{ color: "#aaa", fontSize: 12, fontWeight: "bold", minWidth: 40, textAlign: "right" }}>
                  {d.count.toLocaleString()}
                </span>
              </div>
            </div>
            <div style={{ background: "#1a1a35", borderRadius: 3, height: 5 }}>
              <div style={{
                width: `${barPct}%`, height: "100%", borderRadius: 3,
                background: `linear-gradient(90deg, ${riskColor}88, ${riskColor})`,
                boxShadow: `0 0 6px ${riskColor}44`,
                transition: "width 0.5s ease",
              }} />
            </div>
          </div>
        );
      })}
      {data.length === 0 && (
        <div style={{ color: "#333", fontSize: 12, textAlign: "center", padding: 20 }}>
          No attacker data yet
        </div>
      )}
    </div>
  );
}
