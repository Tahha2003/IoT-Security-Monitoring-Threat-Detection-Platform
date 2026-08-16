import React, { useState, useEffect } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import AlertFeed from "./components/AlertFeed";
import AttackTimeline from "./components/AttackTimeline";
import AnomalyGauge from "./components/AnomalyGauge";
import TopAttackers from "./components/TopAttackers";
import SeverityPie from "./components/SeverityPie";
import SystemHealth from "./components/SystemHealth";
import DevicesPanel from "./components/DevicesPanel";
import StatsBar from "./components/StatsBar";
import ToastManager from "./components/ToastManager";
import AllAlertsModal from "./components/AllAlertsModal";
import SoarPanel from "./components/SoarPanel";
import SystemControl from "./components/SystemControl";
import NetworkTopology from "./components/NetworkTopology";

const DARK   = "#080812";
const CARD   = "#0d0d1c";
const BORDER = "#16163a";
const ACCENT = "#00d4ff";
const RED    = "#e94560";

function Panel({ title, children, style, accent, noPad }) {
  return (
    <div style={{
      background: CARD,
      border: `1px solid ${accent ? `${ACCENT}55` : BORDER}`,
      borderRadius: 12,
      padding: noPad ? 0 : "14px 16px",
      boxShadow: accent
        ? `0 0 20px ${ACCENT}18, inset 0 1px 0 ${ACCENT}22`
        : `0 2px 12px #00000044, inset 0 1px 0 #ffffff06`,
      transition: "box-shadow 0.3s ease",
      ...style,
    }}>
      {title && (
        <div style={{
          color: accent ? ACCENT : RED,
          fontWeight: 700,
          fontSize: 10,
          letterSpacing: 2.5,
          marginBottom: 14,
          textTransform: "uppercase",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: noPad ? "14px 16px 0" : 0,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: accent ? ACCENT : RED,
            display: "inline-block",
            boxShadow: `0 0 8px ${accent ? ACCENT : RED}`,
            animation: "glowPulse 2s infinite",
          }} />
          {title}
        </div>
      )}
      <div style={noPad ? { padding: "0 16px 14px" } : {}}>
        {children}
      </div>
    </div>
  );
}

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span style={{ color: "#888", fontSize: 12, fontFamily: "monospace" }}>
      {now.toLocaleString()}
    </span>
  );
}

function Uptime() {
  const [start] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [start]);
  const h = Math.floor(elapsed / 3600);
  const m = Math.floor((elapsed % 3600) / 60);
  const s = elapsed % 60;
  return (
    <span style={{ color: "#4caf50", fontSize: 12, fontFamily: "monospace" }}>
      {String(h).padStart(2,"0")}:{String(m).padStart(2,"0")}:{String(s).padStart(2,"0")}
    </span>
  );
}

export default function App() {
  const { messages, connected } = useWebSocket();
  const [mounted, setMounted] = useState(false);
  const [showAllAlerts, setShowAllAlerts] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{
      background: DARK,
      minHeight: "100vh",
      color: "#ddd",
      fontFamily: "'Courier New', monospace",
      padding: "12px 16px",
      opacity: mounted ? 1 : 0,
      transition: "opacity 0.5s ease",
    }}>
      {/* ── Header ── */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 14,
        borderBottom: `1px solid ${BORDER}`,
        paddingBottom: 12,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: `linear-gradient(135deg, ${RED}, ${ACCENT})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 20, fontWeight: "bold", color: "#fff",
            boxShadow: `0 0 16px ${RED}44`,
          }}>⚡</div>
          <div>
            <div style={{
              fontSize: 17, fontWeight: "bold", color: "#fff", letterSpacing: 1.5,
              textShadow: `0 0 20px ${ACCENT}44`,
            }}>
              IoT Threat Detection System
            </div>
            <div style={{ fontSize: 10, color: "#333", letterSpacing: 3 }}>
              REAL-TIME NETWORK SECURITY DASHBOARD
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 9, color: "#333", marginBottom: 2, letterSpacing: 1 }}>SYSTEM TIME</div>
            <LiveClock />
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 9, color: "#333", marginBottom: 2, letterSpacing: 1 }}>UPTIME</div>
            <Uptime />
          </div>
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            background: connected ? "#001a00" : "#1a0000",
            border: `1px solid ${connected ? "#4caf5066" : "#e9456066"}`,
            borderRadius: 20, padding: "5px 14px",
            boxShadow: connected ? "0 0 12px #4caf5022" : "0 0 12px #e9456022",
            transition: "all 0.5s ease",
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: connected ? "#4caf50" : RED,
              boxShadow: `0 0 10px ${connected ? "#4caf50" : RED}`,
              animation: connected ? "glowPulse 2s infinite" : "none",
            }} />
            <span style={{
              fontSize: 11, color: connected ? "#4caf50" : RED, fontWeight: 800, letterSpacing: 1,
            }}>
              {connected ? "LIVE" : "OFFLINE"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Stats Bar ── */}
      <StatsBar messages={messages} />

      {/* ── System Control Section ── */}
      <div style={{ marginTop: 12 }}>
        <Panel title="System Control" accent noPad={false}>
          <SystemControl />
        </Panel>
      </div>

      {/* ── Network Topology ── */}
      <div style={{ marginTop: 12 }}>
        <Panel title="Live Network Topology" noPad={false} style={{
          border: `1px solid #00d4ff33`,
          boxShadow: `0 0 24px #00d4ff08, inset 0 1px 0 #00d4ff12`,
        }}>
          <NetworkTopology />
        </Panel>
      </div>

      {/* ── Main Grid ── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr 1fr",
        gridTemplateRows: "auto auto auto",
        gap: 12,
        marginTop: 12,
      }}>
        {/* Live Alert Feed */}
        <Panel title="Live Alert Feed" style={{ gridRow: "1 / 3" }}>
          <AlertFeed messages={messages} onViewAll={() => setShowAllAlerts(true)} />
        </Panel>

        {/* Anomaly Score */}
        <Panel title="Anomaly Score" accent>
          <AnomalyGauge messages={messages} />
        </Panel>

        {/* System Health */}
        <Panel title="System Health">
          <SystemHealth />
        </Panel>

        {/* Severity Pie */}
        <Panel title="Severity Distribution">
          <SeverityPie />
        </Panel>

        {/* Devices */}
        <Panel title="Connected Devices">
          <DevicesPanel />
        </Panel>

        {/* Attack Timeline */}
        <Panel title="Attack Timeline" style={{ gridColumn: "1 / 4" }}>
          <AttackTimeline />
        </Panel>

        {/* Top Attackers */}
        <Panel title="Top Attacker IPs" style={{ gridColumn: "1 / 4" }}>
          <TopAttackers />
        </Panel>
      </div>

      {/* ── SOAR Section ── */}
      <div style={{ marginTop: 12 }}>
        <Panel title="SOAR — Automated Response Engine" noPad={false} style={{
          border: `1px solid #e9456044`,
          boxShadow: `0 0 24px #e9456010, inset 0 1px 0 #e9456018`,
        }}>
          <SoarPanel />
        </Panel>
      </div>

      <div style={{
        textAlign: "center", color: "#1a1a35", fontSize: 10, marginTop: 20,
        letterSpacing: 2,
      }}>
        IoT IDS FYP — Phase 7 Dashboard • {new Date().getFullYear()}
      </div>

      {/* Toast + Quarantine system */}
      <ToastManager messages={messages} />

      {/* All Alerts Modal */}
      {showAllAlerts && (
        <AllAlertsModal onClose={() => setShowAllAlerts(false)} />
      )}

      <style>{`
        @keyframes glowPulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 6px currentColor; }
          50% { opacity: 0.5; box-shadow: 0 0 12px currentColor; }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1a1a35; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: #2a2a55; }
      `}</style>
    </div>
  );
}
