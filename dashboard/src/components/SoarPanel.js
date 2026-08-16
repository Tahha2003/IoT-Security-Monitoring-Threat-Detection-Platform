import React, { useState, useEffect, useCallback } from "react";
import { fetchSoarLog, fetchPlaybookStatus, togglePlaybook } from "../services/api";

const DARK   = "#080812";
const CARD   = "#0d0d1c";
const BORDER = "#16163a";
const ACCENT = "#00d4ff";
const RED    = "#e94560";
const GREEN  = "#4caf50";
const ORANGE = "#ff6b00";

// ── Playbook metadata ──────────────────────────────────────────────────────
const PLAYBOOKS = [
  {
    id:   "block_attacker",
    name: "Block Attacker",
    icon: "🚫",
    desc: "UFW deny rule on external attacker IPs with CRITICAL risk",
    color: "#ff2d2d",
  },
  {
    id:   "camera_defense",
    name: "Camera Defense",
    icon: "📷",
    desc: "Rate-limit and log attacks targeting the IP camera",
    color: ORANGE,
  },
  {
    id:   "quarantine_device",
    name: "Quarantine Device",
    icon: "🔒",
    desc: "Isolate compromised IoT device — allow backend traffic only",
    color: "#ffd700",
  },
  {
    id:   "scan_detection",
    name: "Scan Detection",
    icon: "🔍",
    desc: "Detect and log port scan activity from any source",
    color: ACCENT,
  },
];

// ── Action badge colours ────────────────────────────────────────────────────
const ACTION_COLORS = {
  BLOCKED:           { bg: "#ff2d2d18", border: "#ff2d2d",  text: "#ff2d2d"  },
  RATE_LIMITED:      { bg: "#ff6b0018", border: "#ff6b00",  text: "#ff6b00"  },
  QUARANTINED:       { bg: "#ffd70018", border: "#ffd700",  text: "#ffd700"  },
  LOGGED:            { bg: "#00d4ff18", border: "#00d4ff",  text: "#00d4ff"  },
  SCAN_DETECTED:     { bg: "#4caf5018", border: "#4caf50",  text: "#4caf50"  },
  ALREADY_QUARANTINED: { bg: "#88888818", border: "#888",   text: "#888"     },
  COOLDOWN:          { bg: "#33333318", border: "#555",     text: "#555"     },
  SKIPPED:           { bg: "#11111118", border: "#333",     text: "#444"     },
  ERROR:             { bg: "#ff000018", border: "#f00",     text: "#f00"     },
};

function ActionBadge({ action }) {
  const c = ACTION_COLORS[action] || ACTION_COLORS.LOGGED;
  return (
    <span style={{
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      padding: "2px 7px", borderRadius: 4, fontSize: 10,
      fontWeight: 700, letterSpacing: 0.8, display: "inline-block",
      whiteSpace: "nowrap",
    }}>
      {action}
    </span>
  );
}

// ── Toggle switch ──────────────────────────────────────────────────────────
function Toggle({ enabled, onChange, loading }) {
  return (
    <button
      onClick={() => !loading && onChange(!enabled)}
      title={enabled ? "Click to disable" : "Click to enable"}
      style={{
        width: 42, height: 22, borderRadius: 11,
        background: enabled ? GREEN : "#1a1a35",
        border: `1px solid ${enabled ? GREEN : "#333"}`,
        cursor: loading ? "wait" : "pointer",
        position: "relative",
        transition: "background 0.3s ease, border-color 0.3s ease",
        outline: "none",
        boxShadow: enabled ? `0 0 8px ${GREEN}44` : "none",
        flexShrink: 0,
      }}
    >
      <div style={{
        position: "absolute",
        top: 2,
        left: enabled ? 21 : 2,
        width: 16, height: 16, borderRadius: "50%",
        background: "#fff",
        transition: "left 0.25s cubic-bezier(0.34,1.56,0.64,1)",
        boxShadow: "0 1px 4px #0006",
      }} />
    </button>
  );
}

// ── Playbook card ──────────────────────────────────────────────────────────
function PlaybookCard({ pb, enabled, onToggle, toggling }) {
  return (
    <div style={{
      background: enabled ? "#0f0f20" : "#09090f",
      border: `1px solid ${enabled ? pb.color + "44" : BORDER}`,
      borderRadius: 10,
      padding: "12px 14px",
      display: "flex",
      alignItems: "center",
      gap: 12,
      transition: "all 0.3s ease",
      boxShadow: enabled ? `0 0 14px ${pb.color}18` : "none",
      opacity: enabled ? 1 : 0.55,
    }}>
      <span style={{ fontSize: 22, lineHeight: 1 }}>{pb.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            color: enabled ? pb.color : "#555",
            fontWeight: 700, fontSize: 12, letterSpacing: 0.5,
            transition: "color 0.3s ease",
          }}>
            {pb.name}
          </span>
          <span style={{
            fontSize: 9, letterSpacing: 1, fontWeight: 700,
            color: enabled ? GREEN : "#444",
            border: `1px solid ${enabled ? GREEN + "55" : "#222"}`,
            borderRadius: 3, padding: "1px 5px",
            transition: "all 0.3s ease",
          }}>
            {enabled ? "ACTIVE" : "DISABLED"}
          </span>
        </div>
        <div style={{ color: "#444", fontSize: 10, marginTop: 3, lineHeight: 1.4 }}>
          {pb.desc}
        </div>
      </div>
      <Toggle enabled={enabled} onChange={onToggle} loading={toggling} />
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
export default function SoarPanel() {
  const [pbStatus, setPbStatus]     = useState({
    block_attacker: true, camera_defense: true,
    quarantine_device: true, scan_detection: true,
  });
  const [toggling, setToggling]     = useState({});
  const [log, setLog]               = useState([]);
  const [loadingLog, setLoadingLog] = useState(true);
  const [logError, setLogError]     = useState(null);

  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchPlaybookStatus();
      setPbStatus(data.playbooks || {});
    } catch (_) {}
  }, []);

  const loadLog = useCallback(async () => {
    setLoadingLog(true);
    setLogError(null);
    try {
      const data = await fetchSoarLog();
      setLog(data.log || []);
    } catch (e) {
      setLogError(e.message);
    } finally {
      setLoadingLog(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadLog();
    const interval = setInterval(loadLog, 10000); // refresh log every 10s
    return () => clearInterval(interval);
  }, [loadStatus, loadLog]);

  const handleToggle = async (id, newEnabled) => {
    setToggling(t => ({ ...t, [id]: true }));
    try {
      await togglePlaybook(id, newEnabled);
      setPbStatus(s => ({ ...s, [id]: newEnabled }));
    } catch (e) {
      console.error("Toggle failed:", e);
    } finally {
      setToggling(t => ({ ...t, [id]: false }));
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* ── Playbook toggles ── */}
      <div>
        <div style={{
          color: RED, fontWeight: 700, fontSize: 10, letterSpacing: 2.5,
          marginBottom: 12, display: "flex", alignItems: "center", gap: 8,
          textTransform: "uppercase",
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: RED, display: "inline-block",
            boxShadow: `0 0 8px ${RED}`,
            animation: "glowPulse 2s infinite",
          }} />
          SOAR Playbooks
          <span style={{ color: "#333", fontSize: 9, letterSpacing: 1, fontWeight: 400 }}>
            — toggle to enable / disable at runtime
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {PLAYBOOKS.map(pb => (
            <PlaybookCard
              key={pb.id}
              pb={pb}
              enabled={pbStatus[pb.id] ?? true}
              onToggle={(v) => handleToggle(pb.id, v)}
              toggling={toggling[pb.id] || false}
            />
          ))}
        </div>
      </div>

      {/* ── Playbook execution log ── */}
      <div>
        <div style={{
          color: ACCENT, fontWeight: 700, fontSize: 10, letterSpacing: 2.5,
          marginBottom: 10, display: "flex", alignItems: "center",
          justifyContent: "space-between", textTransform: "uppercase",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: ACCENT, display: "inline-block",
              boxShadow: `0 0 8px ${ACCENT}`,
            }} />
            Playbook Execution Log
          </div>
          <button onClick={loadLog} title="Refresh" style={{
            background: "transparent", border: `1px solid ${BORDER}`,
            color: "#444", cursor: "pointer", borderRadius: 5,
            padding: "2px 8px", fontSize: 12,
          }}>⟳</button>
        </div>

        {logError && (
          <div style={{ color: RED, fontSize: 12, padding: "8px 0" }}>{logError}</div>
        )}

        <div style={{
          overflowY: "auto", maxHeight: 360,
          border: `1px solid ${BORDER}`, borderRadius: 8,
          background: "#08080f",
        }}>
          {loadingLog && log.length === 0 ? (
            <div style={{ color: "#333", textAlign: "center", padding: 30, fontSize: 12 }}>
              Loading…
            </div>
          ) : log.length === 0 ? (
            <div style={{
              color: "#2a2a45", textAlign: "center", padding: 40, fontSize: 12,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            }}>
              <span style={{ fontSize: 26 }}>⚡</span>
              <span>No playbooks triggered yet</span>
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead style={{
                position: "sticky", top: 0,
                background: "#0a0a16", zIndex: 1,
              }}>
                <tr style={{ color: "#444", fontSize: 9, letterSpacing: 1 }}>
                  <th style={th}>TIME</th>
                  <th style={th}>SRC IP</th>
                  <th style={th}>RISK</th>
                  <th style={th}>PLAYBOOK</th>
                  <th style={th}>ACTION</th>
                  <th style={th}>DETAIL</th>
                </tr>
              </thead>
              <tbody>
                {log.map((entry, ei) =>
                  // Expand each playbook result as its own row
                  (entry.results && entry.results.length > 0
                    ? entry.results
                    : [{ playbook: "—", action: "NO_ACTION", message: "" }]
                  ).map((r, ri) => (
                    <tr
                      key={`${ei}-${ri}`}
                      style={{
                        borderBottom: "1px solid #0c0c1a",
                        background: ei % 2 === 0 ? "transparent" : "#09090f",
                      }}
                    >
                      {ri === 0 && (
                        <>
                          <td
                            style={{ ...td, color: "#444", fontFamily: "monospace", fontSize: 10 }}
                            rowSpan={Math.max(entry.results?.length || 1, 1)}
                          >
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleTimeString()
                              : "—"}
                          </td>
                          <td
                            style={{ ...td, color: ACCENT, fontFamily: "monospace" }}
                            rowSpan={Math.max(entry.results?.length || 1, 1)}
                          >
                            {entry.src_ip}
                          </td>
                          <td
                            style={{
                              ...td,
                              color: (entry.risk || 0) >= 0.85
                                ? "#ff2d2d"
                                : (entry.risk || 0) >= 0.65
                                ? ORANGE
                                : "#ffd700",
                              fontFamily: "monospace", fontWeight: 700,
                            }}
                            rowSpan={Math.max(entry.results?.length || 1, 1)}
                          >
                            {((entry.risk || 0) * 100).toFixed(0)}%
                          </td>
                        </>
                      )}
                      <td style={{ ...td, color: "#888" }}>
                        <PlaybookNameBadge name={r.playbook} />
                      </td>
                      <td style={td}><ActionBadge action={r.action || "—"} /></td>
                      <td style={{ ...td, color: "#555", fontSize: 10, maxWidth: 280 }}>
                        <span title={r.message} style={{
                          display: "block", overflow: "hidden",
                          textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {r.message || "—"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function PlaybookNameBadge({ name }) {
  const meta = PLAYBOOKS.find(p => p.id === name);
  if (!meta) return <span style={{ color: "#444", fontSize: 10 }}>{name}</span>;
  return (
    <span style={{
      color: meta.color, fontSize: 10, fontWeight: 600,
      display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap",
    }}>
      {meta.icon} {meta.name}
    </span>
  );
}

const th = {
  padding: "7px 10px", textAlign: "left", fontWeight: 600,
  borderBottom: "1px solid #1a1a35", userSelect: "none",
};
const td = { padding: "5px 10px", color: "#ccc", verticalAlign: "top" };
