import React, { useState, useEffect, useCallback } from "react";
import { fetchAllAlerts } from "../services/api";

const DARK   = "#080812";
const CARD   = "#0d0d1c";
const BORDER = "#16163a";
const ACCENT = "#00d4ff";
const RED    = "#e94560";

const SEV_COLOR = {
  CRITICAL: { bg: "#ff2d2d18", border: "#ff2d2d", text: "#ff2d2d" },
  HIGH:     { bg: "#ff6b0018", border: "#ff6b00", text: "#ff6b00" },
  MEDIUM:   { bg: "#ffd70018", border: "#ffd700", text: "#ffd700" },
  LOW:      { bg: "#4caf5018", border: "#4caf50", text: "#4caf50" },
};

function Badge({ severity }) {
  const c = SEV_COLOR[severity] || { bg: "#33333322", border: "#555", text: "#aaa" };
  return (
    <span style={{
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      padding: "2px 8px", borderRadius: 4, fontSize: 10,
      fontWeight: 800, letterSpacing: 1, display: "inline-block",
      minWidth: 64, textAlign: "center",
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
      <div style={{ width: 44, height: 4, background: "#1a1a35", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, fontFamily: "monospace", minWidth: 28 }}>
        {pct}%
      </span>
    </div>
  );
}

export default function AllAlertsModal({ onClose }) {
  const [alerts, setAlerts]           = useState([]);
  const [total, setTotal]             = useState(0);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);

  // Filter state
  const [filterSev, setFilterSev]     = useState("ALL");
  const [filterType, setFilterType]   = useState("");
  const [filterIp, setFilterIp]       = useState("");
  const [inputType, setInputType]     = useState("");
  const [inputIp, setInputIp]         = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllAlerts({
        limit: 500,
        severity: filterSev === "ALL" ? undefined : filterSev,
        attackType: filterType || undefined,
        srcIp: filterIp || undefined,
      });
      setAlerts(data.alerts || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filterSev, filterType, filterIp]);

  useEffect(() => { load(); }, [load]);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const applyTextFilters = () => {
    setFilterType(inputType);
    setFilterIp(inputIp);
  };

  const clearFilters = () => {
    setFilterSev("ALL");
    setFilterType(""); setInputType("");
    setFilterIp(""); setInputIp("");
  };

  return (
    /* Backdrop */
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(4,4,12,0.88)",
        display: "flex", alignItems: "center", justifyContent: "center",
        backdropFilter: "blur(4px)",
        animation: "fadeIn 0.2s ease",
      }}
    >
      {/* Modal box */}
      <div style={{
        background: CARD, border: `1px solid ${ACCENT}44`,
        borderRadius: 14, width: "95vw", maxWidth: 1200,
        height: "88vh", display: "flex", flexDirection: "column",
        boxShadow: `0 0 60px ${ACCENT}18, 0 8px 40px #000a`,
        overflow: "hidden",
      }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 20px", borderBottom: `1px solid ${BORDER}`,
          background: "#0a0a18",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: ACCENT, boxShadow: `0 0 8px ${ACCENT}`,
              display: "inline-block",
            }} />
            <span style={{ color: ACCENT, fontWeight: 700, fontSize: 12, letterSpacing: 2.5 }}>
              ALL ALERTS
            </span>
            <span style={{
              background: "#00d4ff18", border: `1px solid ${ACCENT}55`,
              color: ACCENT, borderRadius: 10, padding: "1px 10px", fontSize: 11,
            }}>
              {total} total
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent", border: `1px solid ${BORDER}`,
              color: "#666", cursor: "pointer", borderRadius: 6,
              padding: "4px 12px", fontSize: 12,
              transition: "all 0.2s ease",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = RED; e.currentTarget.style.color = RED; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.color = "#666"; }}
          >
            ✕ Close
          </button>
        </div>

        {/* Filter bar */}
        <div style={{
          display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap",
          padding: "10px 20px", borderBottom: `1px solid ${BORDER}`,
          background: "#09091a",
        }}>
          {/* Severity pills */}
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map(s => {
            const colors = {
              ALL: ACCENT, CRITICAL: "#ff2d2d", HIGH: "#ff6b00",
              MEDIUM: "#ffd700", LOW: "#4caf50",
            };
            const active = filterSev === s;
            const col = colors[s];
            return (
              <button key={s} onClick={() => setFilterSev(s)} style={{
                background: active ? `${col}18` : "transparent",
                border: `1px solid ${active ? col : "#222"}`,
                color: active ? col : "#555",
                borderRadius: 5, padding: "3px 10px", fontSize: 10,
                cursor: "pointer", letterSpacing: 1, fontWeight: active ? 700 : 400,
                transition: "all 0.2s ease",
              }}>
                {s}
              </button>
            );
          })}

          <div style={{ width: 1, height: 20, background: BORDER, margin: "0 4px" }} />

          {/* Attack type */}
          <input
            value={inputType}
            onChange={e => setInputType(e.target.value)}
            onKeyDown={e => e.key === "Enter" && applyTextFilters()}
            placeholder="Attack type…"
            style={{
              background: "#0f0f22", border: `1px solid ${BORDER}`,
              color: "#ccc", borderRadius: 5, padding: "4px 10px",
              fontSize: 11, fontFamily: "monospace", width: 140,
              outline: "none",
            }}
          />

          {/* Src IP */}
          <input
            value={inputIp}
            onChange={e => setInputIp(e.target.value)}
            onKeyDown={e => e.key === "Enter" && applyTextFilters()}
            placeholder="Src IP…"
            style={{
              background: "#0f0f22", border: `1px solid ${BORDER}`,
              color: "#ccc", borderRadius: 5, padding: "4px 10px",
              fontSize: 11, fontFamily: "monospace", width: 130,
              outline: "none",
            }}
          />

          <button onClick={applyTextFilters} style={{
            background: `${ACCENT}18`, border: `1px solid ${ACCENT}55`,
            color: ACCENT, borderRadius: 5, padding: "4px 12px",
            fontSize: 11, cursor: "pointer", letterSpacing: 1,
          }}>
            Search
          </button>

          {(filterSev !== "ALL" || filterType || filterIp) && (
            <button onClick={clearFilters} style={{
              background: "transparent", border: "1px solid #333",
              color: "#555", borderRadius: 5, padding: "4px 10px",
              fontSize: 11, cursor: "pointer",
            }}>
              Clear
            </button>
          )}

          <span style={{ marginLeft: "auto", color: "#444", fontSize: 11 }}>
            {loading ? "Loading…" : `${alerts.length} shown`}
          </span>

          <button onClick={load} title="Refresh" style={{
            background: "transparent", border: `1px solid ${BORDER}`,
            color: "#555", cursor: "pointer", borderRadius: 5,
            padding: "4px 9px", fontSize: 13,
          }}>⟳</button>
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 4px" }}>
          {error && (
            <div style={{ color: RED, padding: 20, textAlign: "center", fontSize: 13 }}>
              {error}
            </div>
          )}
          {!error && (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead style={{ position: "sticky", top: 0, background: "#0a0a16", zIndex: 1 }}>
                <tr style={{ color: "#444", fontSize: 10, letterSpacing: 1 }}>
                  <th style={th}>#</th>
                  <th style={th}>SEVERITY</th>
                  <th style={th}>SRC IP</th>
                  <th style={th}>DST IP : PORT</th>
                  <th style={th}>PROTO</th>
                  <th style={th}>ATTACK TYPE</th>
                  <th style={th}>RISK</th>
                  <th style={th}>PKTS</th>
                  <th style={th}>BYTES</th>
                  <th style={th}>VERDICT</th>
                  <th style={th}>TIME</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a, i) => (
                  <tr key={a.id ?? i} style={{
                    borderBottom: "1px solid #0c0c1a",
                    background: i % 2 === 0 ? "transparent" : "#0a0a16",
                  }}>
                    <td style={{ ...td, color: "#333", fontSize: 10 }}>{a.id}</td>
                    <td style={td}><Badge severity={a.severity} /></td>
                    <td style={{ ...td, color: ACCENT, fontFamily: "monospace" }}>{a.src_ip}</td>
                    <td style={{ ...td, color: "#777", fontFamily: "monospace", fontSize: 11 }}>
                      {a.dst_ip}:{a.dst_port}
                    </td>
                    <td style={td}>
                      <span style={{
                        background: "#1a1a35", borderRadius: 3, padding: "1px 6px", fontSize: 10,
                      }}>
                        {a.protocol?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ ...td, color: RED, fontWeight: 600 }}>{a.attack_type}</td>
                    <td style={td}><RiskBar score={a.risk_score ?? 0} /></td>
                    <td style={{ ...td, color: "#888", fontFamily: "monospace", fontSize: 11 }}>
                      {a.packet_count}
                    </td>
                    <td style={{ ...td, color: "#666", fontFamily: "monospace", fontSize: 11 }}>
                      {a.byte_count?.toLocaleString()}
                    </td>
                    <td style={td}>
                      {a.verdict ? (
                        <span style={{
                          color: a.verdict === "TP" ? "#ff6b00" : "#4caf50",
                          fontWeight: 700, fontSize: 11, fontFamily: "monospace",
                        }}>
                          {a.verdict}
                        </span>
                      ) : (
                        <span style={{ color: "#333", fontSize: 11 }}>—</span>
                      )}
                    </td>
                    <td style={{ ...td, color: "#444", fontSize: 10, fontFamily: "monospace" }}>
                      {a.timestamp ? new Date(a.timestamp).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loading && !error && alerts.length === 0 && (
            <div style={{
              textAlign: "center", color: "#2a2a45", padding: 60,
              fontSize: 13, display: "flex", flexDirection: "column",
              alignItems: "center", gap: 10,
            }}>
              <span style={{ fontSize: 32 }}>🛡️</span>
              <span>No alerts match the current filters</span>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1a1a35; border-radius: 2px; }
      `}</style>
    </div>
  );
}

const th = {
  padding: "8px 10px", textAlign: "left", fontWeight: 600,
  borderBottom: "1px solid #1a1a35", userSelect: "none",
};
const td = { padding: "6px 10px", color: "#ccc" };
