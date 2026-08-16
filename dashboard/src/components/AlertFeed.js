import React, { useState, useRef, useEffect } from "react";

const SEV_COLOR = {
  CRITICAL: { bg: "#ff2d2d18", border: "#ff2d2d", text: "#ff2d2d", glow: "#ff2d2d" },
  HIGH:     { bg: "#ff6b0018", border: "#ff6b00", text: "#ff6b00", glow: "#ff6b00" },
  MEDIUM:   { bg: "#ffd70018", border: "#ffd700", text: "#ffd700", glow: "#ffd700" },
  LOW:      { bg: "#4caf5018", border: "#4caf50", text: "#4caf50", glow: "#4caf50" },
};

const FILTER_COLORS = {
  ALL:      { active: "#00d4ff" },
  CRITICAL: { active: "#ff2d2d" },
  HIGH:     { active: "#ff6b00" },
  MEDIUM:   { active: "#ffd700" },
  LOW:      { active: "#4caf50" },
};

function Badge({ severity }) {
  const c = SEV_COLOR[severity] || { bg: "#33333322", border: "#555", text: "#aaa", glow: "#555" };
  return (
    <span style={{
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      padding: "3px 8px", borderRadius: 4, fontSize: 10, fontWeight: 800,
      letterSpacing: 1, boxShadow: `0 0 6px ${c.glow}33`,
      display: "inline-block", minWidth: 64, textAlign: "center",
    }}>
      {severity}
    </span>
  );
}

function RiskBar({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "#ff2d2d" : pct >= 65 ? "#ff6b00" : pct >= 40 ? "#ffd700" : "#4caf50";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 40, height: 4, background: "#1a1a35", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          width: `${pct}%`, height: "100%", background: color,
          boxShadow: `0 0 6px ${color}`, borderRadius: 2, transition: "width 0.4s ease",
        }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, fontFamily: "monospace", minWidth: 28 }}>
        {pct}%
      </span>
    </div>
  );
}

function AlertRow({ alert, index, isNew }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const t = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(t);
  }, []);
  const c = SEV_COLOR[alert.severity] || SEV_COLOR.LOW;
  return (
    <tr style={{
      borderBottom: "1px solid #0f0f1e",
      background: isNew ? `${c.bg}` : index % 2 === 0 ? "transparent" : "#0a0a16",
      opacity: mounted ? 1 : 0,
      transform: mounted ? "translateY(0)" : "translateY(-8px)",
      transition: isNew
        ? "opacity 0.4s ease, transform 0.4s cubic-bezier(0.34,1.56,0.64,1), background 1.5s ease"
        : "opacity 0.3s ease, transform 0.3s ease",
    }}>
      <td style={td}><Badge severity={alert.severity} /></td>
      <td style={{ ...td, color: "#00d4ff", fontFamily: "monospace", fontSize: 11 }}>{alert.src_ip}</td>
      <td style={{ ...td, color: "#888", fontFamily: "monospace", fontSize: 11 }}>
        {alert.dst_ip}:{alert.dst_port}
      </td>
      <td style={{ ...td, color: "#666", fontSize: 11 }}>
        <span style={{ background: "#1a1a35", borderRadius: 3, padding: "1px 6px", fontSize: 10 }}>
          {alert.protocol?.toUpperCase()}
        </span>
      </td>
      <td style={{ ...td, color: "#e94560", fontSize: 11, fontWeight: 600 }}>{alert.attack_type}</td>
      <td style={td}><RiskBar score={alert.risk_score} /></td>
      <td style={{ ...td, color: "#444", fontSize: 10, fontFamily: "monospace" }}>
        {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : "—"}
      </td>
    </tr>
  );
}

export default function AlertFeed({ messages, onViewAll }) {
  const [filter, setFilter] = useState("ALL");
  const prevLengthRef = useRef(0);

  const filtered = filter === "ALL" ? messages : messages.filter(m => m.severity === filter);
  const newCount = messages.length - prevLengthRef.current;
  useEffect(() => { prevLengthRef.current = messages.length; }, [messages.length]);

  return (
    <div style={{ height: 380, display: "flex", flexDirection: "column" }}>
      {/* Filter bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 10, alignItems: "center", flexWrap: "wrap" }}>
        {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map(f => {
          const col = FILTER_COLORS[f].active;
          const active = filter === f;
          return (
            <button key={f} onClick={() => setFilter(f)} style={{
              background: active ? `${col}18` : "transparent",
              border: `1px solid ${active ? col : "#222"}`,
              color: active ? col : "#555",
              borderRadius: 5, padding: "3px 10px", fontSize: 10,
              cursor: "pointer", letterSpacing: 1,
              fontWeight: active ? 700 : 400,
              transition: "all 0.2s ease",
              boxShadow: active ? `0 0 8px ${col}33` : "none",
            }}>
              {f}
            </button>
          );
        })}

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          {newCount > 0 && (
            <span style={{
              background: "#ff2d2d22", border: "1px solid #ff2d2d", color: "#ff2d2d",
              borderRadius: 10, padding: "1px 8px", fontSize: 10, fontWeight: 700,
              animation: "pulseBadge 1s ease",
            }}>
              +{newCount} new
            </span>
          )}
          <span style={{ color: "#444", fontSize: 11 }}>{filtered.length} alerts</span>

          {/* View All button */}
          <button
            onClick={onViewAll}
            style={{
              background: "#00d4ff18", border: "1px solid #00d4ff44",
              color: "#00d4ff", borderRadius: 5, padding: "3px 11px",
              fontSize: 10, cursor: "pointer", letterSpacing: 1, fontWeight: 700,
              transition: "all 0.2s ease",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "#00d4ff28";
              e.currentTarget.style.boxShadow = "0 0 10px #00d4ff33";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "#00d4ff18";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            VIEW ALL ↗
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowY: "auto", flex: 1 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead style={{ position: "sticky", top: 0, background: "#0a0a14", zIndex: 1 }}>
            <tr style={{ color: "#444", fontSize: 10, letterSpacing: 1 }}>
              <th style={th}>SEVERITY</th>
              <th style={th}>SRC IP</th>
              <th style={th}>DST IP:PORT</th>
              <th style={th}>PROTO</th>
              <th style={th}>ATTACK TYPE</th>
              <th style={th}>RISK</th>
              <th style={th}>TIME</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => (
              <AlertRow
                key={`${m.src_ip}-${m.timestamp}-${i}`}
                alert={m} index={i} isNew={i < newCount}
              />
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div style={{
            textAlign: "center", color: "#2a2a45", padding: 40, fontSize: 13,
            display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          }}>
            <span style={{ fontSize: 28 }}>🛡️</span>
            <span>No alerts — monitoring live traffic...</span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulseBadge {
          0% { transform: scale(0.8); opacity: 0; }
          60% { transform: scale(1.1); }
          100% { transform: scale(1); opacity: 1; }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1a1a35; border-radius: 2px; }
      `}</style>
    </div>
  );
}

const th = {
  padding: "7px 10px", textAlign: "left", fontWeight: 600,
  borderBottom: "1px solid #1a1a35", userSelect: "none",
};
const td = { padding: "6px 10px", color: "#ccc" };
