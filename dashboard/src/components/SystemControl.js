import React, { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

const BORDER = "#16163a";
const ACCENT = "#00d4ff";
const RED    = "#e94560";
const GREEN  = "#4caf50";
const ORANGE = "#ff6b00";
const YELLOW = "#ffd700";

function StatusDot({ ok, pulse }) {
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: ok ? GREEN : RED,
      boxShadow: `0 0 8px ${ok ? GREEN : RED}`,
      animation: (ok && pulse) ? "glowPulse 2s infinite" : "none",
      flexShrink: 0,
    }} />
  );
}

function Pill({ label, ok, unknown }) {
  const color = unknown ? "#555" : ok ? GREEN : RED;
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 6,
      background: `${color}12`, border: `1px solid ${color}44`,
      borderRadius: 8, padding: "5px 10px",
    }}>
      <StatusDot ok={ok} pulse={ok} />
      <span style={{ color, fontSize: 10, fontWeight: 700, letterSpacing: 0.8 }}>
        {label}
      </span>
    </div>
  );
}

function Btn({ children, onClick, color, disabled, loading, style }) {
  const [hover, setHover] = useState(false);
  const c = color || ACCENT;
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: hover && !disabled ? `${c}22` : `${c}12`,
        border: `1px solid ${disabled ? "#222" : hover ? c : `${c}55`}`,
        color: disabled ? "#333" : c,
        borderRadius: 7, padding: "7px 16px",
        fontSize: 11, fontWeight: 700, letterSpacing: 1,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "all 0.2s ease",
        boxShadow: hover && !disabled ? `0 0 12px ${c}33` : "none",
        display: "flex", alignItems: "center", gap: 6,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {loading ? <Spinner color={c} /> : null}
      {children}
    </button>
  );
}

function Spinner({ color }) {
  return (
    <span style={{
      display: "inline-block", width: 10, height: 10,
      border: `2px solid ${color}33`,
      borderTop: `2px solid ${color}`,
      borderRadius: "50%",
      animation: "spin 0.7s linear infinite",
    }} />
  );
}

// ── Log viewer ─────────────────────────────────────────────────────────────
const LOG_TABS = [
  { id: "startup",  label: "Startup" },
  { id: "pipeline", label: "Pipeline" },
  { id: "ml",       label: "ML" },
  { id: "zeek",     label: "Zeek" },
  { id: "parser",   label: "Parser" },
  { id: "soar",     label: "SOAR" },
  { id: "api",      label: "API" },
  { id: "training", label: "Training" },
];

function LogViewer() {
  const [tab, setTab]       = useState("startup");
  const [lines, setLines]   = useState([]);
  const [path, setPath]     = useState("");
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const bottomRef = useRef(null);

  const load = useCallback(async (service) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/system/logs/${service}?lines=60`);
      const data = await res.json();
      setLines(data.lines || []);
      setPath(data.path || "");
    } catch {
      setLines(["[error] Could not fetch log"]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(tab); }, [tab, load]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => load(tab), 3000);
    return () => clearInterval(id);
  }, [autoRefresh, tab, load]);

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const lineColor = (line) => {
    if (/error|exception|failed|crash/i.test(line)) return "#ff2d2d";
    if (/warn(?:ing)?/i.test(line))                 return YELLOW;
    if (/✔|started|running|success|loaded/i.test(line)) return GREEN;
    if (/trigger|soar|playbook/i.test(line))         return ORANGE;
    if (line.startsWith("["))                        return "#aaa";
    return "#555";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Tab bar */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
        {LOG_TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            background: tab === t.id ? `${ACCENT}18` : "transparent",
            border: `1px solid ${tab === t.id ? ACCENT : "#1a1a35"}`,
            color: tab === t.id ? ACCENT : "#444",
            borderRadius: 5, padding: "3px 10px", fontSize: 10,
            cursor: "pointer", fontWeight: tab === t.id ? 700 : 400,
            letterSpacing: 0.8, transition: "all 0.15s ease",
          }}>
            {t.label}
          </button>
        ))}
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
            <span style={{ fontSize: 9, color: "#444", letterSpacing: 1 }}>AUTO</span>
            <div
              onClick={() => setAutoRefresh(a => !a)}
              style={{
                width: 30, height: 16, borderRadius: 8,
                background: autoRefresh ? GREEN : "#1a1a35",
                border: `1px solid ${autoRefresh ? GREEN : "#333"}`,
                position: "relative", cursor: "pointer",
                transition: "all 0.25s ease",
                boxShadow: autoRefresh ? `0 0 6px ${GREEN}44` : "none",
              }}
            >
              <div style={{
                position: "absolute", top: 1,
                left: autoRefresh ? 14 : 1,
                width: 12, height: 12, borderRadius: "50%",
                background: "#fff", transition: "left 0.2s ease",
              }} />
            </div>
          </label>
          <button onClick={() => load(tab)} style={{
            background: "transparent", border: `1px solid ${BORDER}`,
            color: "#444", borderRadius: 5, padding: "3px 8px",
            fontSize: 12, cursor: "pointer",
          }}>⟳</button>
        </div>
      </div>

      {/* Log area */}
      <div style={{
        background: "#04040c",
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "10px 12px",
        height: 200,
        overflowY: "auto",
        fontFamily: "monospace",
        fontSize: 11,
      }}>
        {loading && lines.length === 0 ? (
          <span style={{ color: "#333" }}>Loading…</span>
        ) : lines.length === 0 ? (
          <span style={{ color: "#222" }}>No log entries yet — {path}</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} style={{ color: lineColor(line), lineHeight: 1.6, wordBreak: "break-all" }}>
              {line || "\u00a0"}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
      {path && <div style={{ color: "#1a1a35", fontSize: 9, letterSpacing: 1 }}>{path}</div>}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
export default function SystemControl() {
  const [status, setStatus]         = useState(null);
  const [busy, setBusy]             = useState({});
  const [feedback, setFeedback]     = useState("");
  const [feedbackOk, setFeedbackOk] = useState(true);
  const [ifaces, setIfaces]         = useState([]);
  const [selectedIface, setSelectedIface] = useState("wlxe009bf6913de");
  const [sudoNote, setSudoNote]     = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const res  = await fetch(`${API_BASE}/api/system/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      setStatus(null);
    }
  }, []);

  const loadIfaces = useCallback(async () => {
    try {
      const res  = await fetch(`${API_BASE}/api/system/interfaces`);
      const data = await res.json();
      setIfaces(data.interfaces || []);
      // auto-select first UP interface that isn't loopback
      const upIface = (data.interfaces || []).find(i => i.state === "UP");
      if (upIface) setSelectedIface(upIface.name);
    } catch {}
  }, []);

  useEffect(() => {
    loadStatus();
    loadIfaces();
    const id = setInterval(loadStatus, 4000);
    return () => clearInterval(id);
  }, [loadStatus, loadIfaces]);

  const showFeedback = (msg, ok = true) => {
    setFeedback(msg); setFeedbackOk(ok);
    setTimeout(() => setFeedback(""), 6000);
  };

  const call = async (key, url, method = "POST", extraParams = "") => {
    setBusy(b => ({ ...b, [key]: true }));
    try {
      const fullUrl = extraParams ? `${API_BASE}${url}?${extraParams}` : `${API_BASE}${url}`;
      const res  = await fetch(fullUrl, { method });
      const data = await res.json();
      showFeedback(data.message || (data.ok ? "Done" : "Failed"), data.ok !== false);
      setTimeout(loadStatus, 1500);
    } catch (e) {
      showFeedback(`Error: ${e.message}`, false);
    } finally {
      setBusy(b => ({ ...b, [key]: false }));
    }
  };

  const pipelineUp = status?.pipeline;
  const dbOk       = status?.database;
  const modelsOk   = status?.models;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* ── Sudo note banner — shown until dismissed ── */}
      {sudoNote === false && (
        <div style={{
          background: "#ffd70010", border: "1px solid #ffd70033",
          borderRadius: 8, padding: "8px 14px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          gap: 12,
        }}>
          <div style={{ fontSize: 11, color: "#ffd700", lineHeight: 1.5 }}>
            <strong>First time?</strong> Run this once in terminal to enable passwordless sudo for Zeek/PostgreSQL/Suricata:
            <code style={{
              display: "block", marginTop: 4,
              background: "#04040c", borderRadius: 4, padding: "4px 8px",
              color: "#00d4ff", fontSize: 11, letterSpacing: 0.5,
            }}>
              bash infrastructure/scripts/setup_sudo.sh
            </code>
          </div>
          <button onClick={() => setSudoNote(true)} style={{
            background: "transparent", border: "none", color: "#555",
            cursor: "pointer", fontSize: 16, flexShrink: 0,
          }}>✕</button>
        </div>
      )}

      {/* ── Status pills row ── */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <Pill label="PIPELINE"  ok={pipelineUp} unknown={!status} />
        <Pill label="ZEEK"      ok={status?.zeek} unknown={!status} />
        <Pill label="DATABASE"  ok={dbOk} unknown={!status} />
        <Pill label="ML MODELS" ok={modelsOk} unknown={!status} />

        {status && (
          <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: "#333", fontSize: 9, letterSpacing: 1 }}>TOTAL ALERTS</div>
              <div style={{ color: ACCENT, fontFamily: "monospace", fontWeight: 700, fontSize: 14 }}>
                {status.total_alerts?.toLocaleString()}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: "#333", fontSize: 9, letterSpacing: 1 }}>LAST 5 MIN</div>
              <div style={{
                fontFamily: "monospace", fontWeight: 700, fontSize: 14,
                color: status.recent_alerts > 0 ? ORANGE : "#444",
              }}>
                {status.recent_alerts}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── NIC selector + control buttons ── */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>

        {/* Network Interface picker */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: "#444", fontSize: 10, letterSpacing: 1, whiteSpace: "nowrap" }}>
            ZEEK NIC
          </span>
          <select
            value={selectedIface}
            onChange={e => setSelectedIface(e.target.value)}
            style={{
              background: "#0f0f22", border: `1px solid ${BORDER}`,
              color: ACCENT, borderRadius: 5, padding: "5px 8px",
              fontSize: 11, fontFamily: "monospace", cursor: "pointer",
              outline: "none",
            }}
          >
            {ifaces.length > 0
              ? ifaces.map(i => (
                  <option key={i.name} value={i.name}>
                    {i.name} {i.state === "UP" ? "●" : "○"}
                  </option>
                ))
              : <option value={selectedIface}>{selectedIface}</option>
            }
          </select>
          <button
            onClick={loadIfaces}
            title="Refresh interfaces"
            style={{
              background: "transparent", border: `1px solid ${BORDER}`,
              color: "#444", borderRadius: 5, padding: "4px 7px",
              fontSize: 11, cursor: "pointer",
            }}
          >⟳</button>
        </div>

        <div style={{ width: 1, background: BORDER, alignSelf: "stretch" }} />

        {/* Start */}
        <Btn
          color={GREEN}
          disabled={pipelineUp}
          loading={busy.start}
          onClick={() => call("start", "/api/system/start", "POST", `zeek_interface=${selectedIface}`)}
        >
          ▶ Start Pipeline
        </Btn>

        {/* Stop */}
        <Btn
          color={RED}
          disabled={!pipelineUp}
          loading={busy.stop}
          onClick={() => call("stop", "/api/system/stop")}
        >
          ■ Stop Pipeline
        </Btn>

        <div style={{ width: 1, background: BORDER, alignSelf: "stretch" }} />

        {/* Train models */}
        <Btn
          color={YELLOW}
          disabled={modelsOk}
          loading={busy.train}
          onClick={() => call("train", "/api/system/train")}
          style={{ opacity: modelsOk ? 0.45 : 1 }}
        >
          🧠 Train Models
        </Btn>

        {/* Reset firewall */}
        <Btn
          color={ORANGE}
          loading={busy.firewall}
          onClick={() => call("firewall", "/api/system/reset-firewall")}
        >
          🔥 Reset Firewall
        </Btn>

        {/* Clear DB */}
        <Btn
          color="#888"
          loading={busy.cleardb}
          onClick={() => {
            if (window.confirm("Clear ALL alerts from database? This cannot be undone.")) {
              call("cleardb", "/api/system/clear-db");
            }
          }}
        >
          🗑 Clear DB
        </Btn>

        <button
          onClick={loadStatus}
          style={{
            marginLeft: "auto",
            background: "transparent", border: `1px solid ${BORDER}`,
            color: "#444", borderRadius: 6, padding: "6px 10px",
            fontSize: 12, cursor: "pointer",
          }}
        >⟳</button>
      </div>

      {/* ── Feedback bar ── */}
      {feedback && (
        <div style={{
          background: feedbackOk ? `${GREEN}12` : `${RED}12`,
          border: `1px solid ${feedbackOk ? GREEN : RED}44`,
          color: feedbackOk ? GREEN : RED,
          borderRadius: 7, padding: "8px 14px",
          fontSize: 12, fontFamily: "monospace",
          animation: "fadeIn 0.2s ease",
        }}>
          {feedbackOk ? "✔" : "✗"}  {feedback}
        </div>
      )}

      {/* ── Log viewer ── */}
      <LogViewer />

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes glowPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
    </div>
  );
}
