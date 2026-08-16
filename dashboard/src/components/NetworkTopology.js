import React, { useState, useEffect, useRef, useCallback } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ─── Colour palette ───────────────────────────────────────────────────────────
const C = {
  bg:       "#04040e",
  card:     "#0d0d1c",
  border:   "#16163a",
  accent:   "#00d4ff",
  green:    "#4caf50",
  red:      "#ff2d2d",
  orange:   "#ff6b00",
  yellow:   "#ffd700",
  purple:   "#9c27b0",
  text:     "#aaa",
  dim:      "#333",
};

// ─── Node definitions — positions are % of SVG viewBox 900×520 ────────────────
const NODES = {
  pi:       { id: "pi",       x: 80,  y: 260, label: "Raspberry Pi",   sub: "Capture Node",      icon: "🥧", color: C.green,  type: "capture"   },
  switch:   { id: "switch",   x: 280, y: 260, label: "Switch",         sub: "SPAN Port",          icon: "🔀", color: C.accent, type: "network"   },
  backend:  { id: "backend",  x: 490, y: 160, label: "Backend PC",     sub: "192.168.1.43",       icon: "🖥", color: C.accent, type: "backend"   },
  router:   { id: "router",   x: 490, y: 360, label: "WiFi Router",    sub: "192.168.1.1",        icon: "📡", color: C.accent, type: "network"   },
  kali:     { id: "kali",     x: 280, y: 420, label: "Kali Linux",     sub: "Attacker",           icon: "💀", color: C.red,    type: "attacker"  },
  camera:   { id: "camera",   x: 700, y: 200, label: "IP Camera",      sub: "192.168.50.10",      icon: "📷", color: C.yellow, type: "iot"       },
  byod:     { id: "byod",     x: 700, y: 360, label: "BYOD Mobile",    sub: "192.168.50.40",      icon: "📱", color: C.yellow, type: "iot"       },
  pipeline: { id: "pipeline", x: 490, y: 260, label: "IDS Pipeline",   sub: "7 Threads",          icon: "⚡", color: C.purple, type: "pipeline"  },
  analyst:  { id: "analyst",  x: 820, y: 100, label: "Analyst",        sub: "Dashboard User",     icon: "👤", color: C.text,   type: "user"      },
};

// ─── Edge definitions ─────────────────────────────────────────────────────────
// type: "wired" | "wireless" | "data" | "attack"
const EDGES = [
  { id: "pi-switch",      from: "pi",       to: "switch",   type: "wired",    label: "pcap stream"    },
  { id: "switch-backend", from: "switch",   to: "backend",  type: "wired",    label: "SPAN mirror"    },
  { id: "switch-kali",    from: "kali",     to: "switch",   type: "wired",    label: "eth"            },
  { id: "switch-router",  from: "switch",   to: "router",   type: "wired",    label: ""               },
  { id: "router-camera",  from: "router",   to: "camera",   type: "wireless", label: "WiFi"           },
  { id: "router-byod",    from: "router",   to: "byod",     type: "wireless", label: "WiFi"           },
  { id: "backend-pipeline",from:"backend",  to: "pipeline", type: "data",     label: "flows"          },
  { id: "pipeline-analyst",from:"pipeline", to: "analyst",  type: "data",     label: "alerts"         },
  { id: "kali-camera",    from: "kali",     to: "camera",   type: "attack",   label: "ATTACK",        attack: true },
  { id: "kali-byod",      from: "kali",     to: "byod",     type: "attack",   label: "ATTACK",        attack: true },
];

// ─── Packet animation ─────────────────────────────────────────────────────────
let _packetId = 0;
function makePacket(edgeId, color, label) {
  return { id: _packetId++, edgeId, color, label, t: 0, speed: 0.008 + Math.random() * 0.006 };
}

// ─── Node box component ───────────────────────────────────────────────────────
function NodeBox({ node, active, attacked, selected, onClick }) {
  const [hover, setHover] = useState(false);
  const w = 100, h = 64;
  const borderColor = attacked ? C.red : active ? node.color : C.border;
  const glowColor   = attacked ? C.red : node.color;

  return (
    <g
      transform={`translate(${node.x - w / 2}, ${node.y - h / 2})`}
      style={{ cursor: "pointer" }}
      onClick={() => onClick(node.id)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Glow */}
      {(active || attacked || hover) && (
        <rect x={-3} y={-3} width={w + 6} height={h + 6} rx={11}
          fill="none" stroke={glowColor} strokeWidth={1}
          opacity={0.25}
        />
      )}
      {/* Card */}
      <rect x={0} y={0} width={w} height={h} rx={8}
        fill={selected ? `${node.color}18` : "#0a0a18"}
        stroke={borderColor}
        strokeWidth={selected ? 2 : 1}
        style={{ filter: attacked ? `drop-shadow(0 0 8px ${C.red})` : hover ? `drop-shadow(0 0 6px ${node.color}66)` : "none" }}
      />
      {/* Status dot */}
      <circle cx={w - 10} cy={10} r={4}
        fill={attacked ? C.red : active ? C.green : C.dim}
        style={{ filter: active || attacked ? `drop-shadow(0 0 4px ${attacked ? C.red : C.green})` : "none" }}
      />
      {/* Icon */}
      <text x={w / 2} y={22} textAnchor="middle" fontSize="16">{node.icon}</text>
      {/* Label */}
      <text x={w / 2} y={38} textAnchor="middle" fill={attacked ? C.red : active ? "#fff" : C.text}
        fontSize="9" fontWeight="700" fontFamily="monospace" letterSpacing="0.3">
        {node.label}
      </text>
      {/* Sub */}
      <text x={w / 2} y={52} textAnchor="middle" fill={attacked ? `${C.red}aa` : C.dim}
        fontSize="7.5" fontFamily="monospace">
        {node.sub}
      </text>
    </g>
  );
}

// ─── Edge component ───────────────────────────────────────────────────────────
function Edge({ edge, packets, onClick }) {
  const from = NODES[edge.from];
  const to   = NODES[edge.to];

  const dx = to.x - from.x, dy = to.y - from.y;
  const len = Math.sqrt(dx * dx + dy * dy);

  // Shorten line so it doesn't overlap node boxes
  const pad = 54;
  const sx = from.x + (dx / len) * pad;
  const sy = from.y + (dy / len) * pad;
  const ex = to.x   - (dx / len) * pad;
  const ey = to.y   - (dy / len) * pad;

  // Mid-point for label
  const mx = (sx + ex) / 2, my = (sy + ey) / 2;

  const strokeColor =
    edge.type === "attack"    ? `${C.red}66`    :
    edge.type === "wireless"  ? `${C.yellow}44` :
    edge.type === "data"      ? `${C.purple}66` :
    `${C.accent}33`;

  const strokeDash =
    edge.type === "wireless"  ? "6 4" :
    edge.type === "attack"    ? "4 3" :
    edge.type === "data"      ? "3 3" :
    "none";

  return (
    <g onClick={() => onClick && onClick(edge.id)} style={{ cursor: "default" }}>
      {/* Edge line */}
      <line x1={sx} y1={sy} x2={ex} y2={ey}
        stroke={strokeColor}
        strokeWidth={edge.type === "attack" ? 2 : 1.5}
        strokeDasharray={strokeDash}
      />

      {/* Edge label */}
      {edge.label && (
        <text x={mx} y={my - 5} textAnchor="middle"
          fill={edge.type === "attack" ? `${C.red}cc` : `${C.accent}66`}
          fontSize="7" fontFamily="monospace" letterSpacing="0.5">
          {edge.label}
        </text>
      )}

      {/* Animated packets */}
      {packets.map(pkt => {
        const px = sx + (ex - sx) * pkt.t;
        const py = sy + (ey - sy) * pkt.t;
        return (
          <g key={pkt.id}>
            <circle cx={px} cy={py} r={5} fill={pkt.color} opacity={0.85}
              style={{ filter: `drop-shadow(0 0 4px ${pkt.color})` }}
            />
            <circle cx={px} cy={py} r={2} fill="#fff" opacity={0.9} />
          </g>
        );
      })}
    </g>
  );
}

// ─── Legend ───────────────────────────────────────────────────────────────────
function Legend() {
  const items = [
    { color: `${C.accent}66`, dash: "none",  label: "Wired"    },
    { color: `${C.yellow}66`, dash: "6 4",   label: "Wireless" },
    { color: `${C.purple}66`, dash: "3 3",   label: "Data"     },
    { color: `${C.red}88`,    dash: "4 3",   label: "Attack"   },
  ];
  return (
    <g transform="translate(20, 480)">
      {items.map((it, i) => (
        <g key={it.label} transform={`translate(${i * 110}, 0)`}>
          <line x1={0} y1={0} x2={30} y2={0}
            stroke={it.color} strokeWidth={2} strokeDasharray={it.dash} />
          <text x={36} y={4} fill={C.dim} fontSize="9" fontFamily="monospace">{it.label}</text>
        </g>
      ))}
    </g>
  );
}

// ─── Pipeline stage flow (bottom strip) ──────────────────────────────────────
const PIPELINE_STAGES = [
  { id: "t1", label: "T1 Packet\nListener",  color: C.accent  },
  { id: "t2", label: "T2 Zeek\nFeeder",      color: C.accent  },
  { id: "t3", label: "T3 Zeek\nParser",      color: C.accent  },
  { id: "t4", label: "T4 ML\nInference",     color: C.purple  },
  { id: "t5", label: "T5 DPI\nWorker",       color: C.orange  },
  { id: "t6", label: "T6 SIEM\nWriter",      color: C.yellow  },
  { id: "t7", label: "T7 Metrics",           color: C.green   },
];

function PipelineStrip({ activeStages }) {
  const W = 840, stageW = W / PIPELINE_STAGES.length;
  return (
    <div style={{
      background: "#06060f",
      border: `1px solid ${C.border}`,
      borderRadius: 10,
      padding: "10px 16px",
      marginTop: 10,
    }}>
      <div style={{
        color: C.red, fontSize: 9, fontWeight: 700, letterSpacing: 2.5,
        marginBottom: 10, display: "flex", alignItems: "center", gap: 6,
      }}>
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.red, display: "inline-block" }} />
        PIPELINE FLOW — 7 THREADS
      </div>
      <svg viewBox={`0 0 ${W} 60`} width="100%" style={{ overflow: "visible" }}>
        {PIPELINE_STAGES.map((st, i) => {
          const cx = stageW * i + stageW / 2;
          const active = activeStages.includes(st.id);
          return (
            <g key={st.id}>
              {/* Arrow between stages */}
              {i > 0 && (
                <line
                  x1={stageW * i - 10} y1={28}
                  x2={stageW * i + 4}  y2={28}
                  stroke={active ? st.color : C.border}
                  strokeWidth={1.5}
                  markerEnd="url(#arr)"
                />
              )}
              {/* Stage box */}
              <rect x={cx - 50} y={8} width={100} height={40} rx={6}
                fill={active ? `${st.color}18` : "#08080f"}
                stroke={active ? st.color : C.border}
                strokeWidth={active ? 1.5 : 1}
                style={{ filter: active ? `drop-shadow(0 0 6px ${st.color}44)` : "none" }}
              />
              {/* Pulse dot */}
              <circle cx={cx + 40} cy={14} r={3.5}
                fill={active ? st.color : C.dim}
                style={{ filter: active ? `drop-shadow(0 0 4px ${st.color})` : "none" }}
              />
              {/* Label */}
              {st.label.split("\n").map((line, li) => (
                <text key={li} x={cx} y={30 + li * 11}
                  textAnchor="middle" fill={active ? "#ddd" : C.dim}
                  fontSize="8" fontFamily="monospace" fontWeight={active ? "700" : "400"}>
                  {line}
                </text>
              ))}
            </g>
          );
        })}
        <defs>
          <marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill={C.accent} opacity={0.5} />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────
function NodeDetail({ nodeId, alerts, onClose }) {
  const node = NODES[nodeId];
  if (!node) return null;

  const nodeAlerts = nodeId === "kali"
    ? alerts.filter(a => a.severity === "CRITICAL" || a.severity === "HIGH").slice(0, 5)
    : nodeId === "camera"
    ? alerts.filter(a => a.dst_ip === "192.168.50.10" || a.src_ip === "192.168.50.10").slice(0, 5)
    : nodeId === "byod"
    ? alerts.filter(a => a.src_ip === "192.168.50.40" || a.dst_ip === "192.168.50.40").slice(0, 5)
    : alerts.slice(0, 5);

  const SEV_C = { CRITICAL: C.red, HIGH: C.orange, MEDIUM: C.yellow, LOW: C.green };

  return (
    <div style={{
      position: "absolute", top: 10, right: 10, width: 240,
      background: "#080816", border: `1px solid ${node.color}55`,
      borderRadius: 10, padding: 14,
      boxShadow: `0 0 20px ${node.color}22`,
      zIndex: 10,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 20 }}>{node.icon}</span>
          <div>
            <div style={{ color: node.color, fontWeight: 700, fontSize: 11 }}>{node.label}</div>
            <div style={{ color: C.dim, fontSize: 9 }}>{node.sub}</div>
          </div>
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "none", color: C.dim,
          cursor: "pointer", fontSize: 14,
        }}>✕</button>
      </div>

      {nodeAlerts.length > 0 ? (
        <>
          <div style={{ color: C.dim, fontSize: 8, letterSpacing: 1, marginBottom: 6 }}>RECENT ALERTS</div>
          {nodeAlerts.map((a, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between",
              borderBottom: `1px solid ${C.border}`,
              padding: "4px 0", fontSize: 9, fontFamily: "monospace",
            }}>
              <span style={{ color: SEV_C[a.severity] || C.text }}>{a.attack_type}</span>
              <span style={{ color: C.dim }}>{a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : "—"}</span>
            </div>
          ))}
        </>
      ) : (
        <div style={{ color: C.dim, fontSize: 10, textAlign: "center", padding: "8px 0" }}>
          No recent alerts
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function NetworkTopology() {
  const [packets, setPackets]           = useState({});   // edgeId → [packet]
  const [selected, setSelected]         = useState(null);
  const [alerts, setAlerts]             = useState([]);
  const [status, setStatus]             = useState(null);
  const [attackedNodes, setAttackedNodes] = useState(new Set());
  const [activeEdges, setActiveEdges]   = useState(new Set());
  const [activeStages, setActiveStages] = useState([]);
  const rafRef = useRef(null);
  const pktsRef = useRef({});

  // ── Fetch alerts & system status ──────────────────────────────────────────
  const loadData = useCallback(async () => {
    try {
      const [alertRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/alerts?limit=20`).then(r => r.json()),
        fetch(`${API_BASE}/api/system/status`).then(r => r.json()),
      ]);
      const al = alertRes.alerts || [];
      setAlerts(al);
      setStatus(statusRes);

      // Determine attacked nodes from recent alerts
      const attacked = new Set();
      const active   = new Set();

      // Known IP → node mapping (update if your real IPs differ)
      const IP_TO_NODE = {
        "192.168.50.10":  "camera",
        "192.168.50.40":  "byod",
        "192.168.1.43":   "backend",
      };

      al.slice(0, 10).forEach(a => {
        const srcNode = IP_TO_NODE[a.src_ip];
        const dstNode = IP_TO_NODE[a.dst_ip];

        // Any high-risk source → mark as attacker node
        if (a.severity === "CRITICAL" || a.severity === "HIGH") {
          if (srcNode) attacked.add(srcNode);
          // If source is unknown attacker machine, highlight kali node
          if (!IP_TO_NODE[a.src_ip] && a.severity === "CRITICAL") {
            attacked.add("kali");
            active.add("kali-camera");
            active.add("kali-byod");
          }
        }
        if (dstNode === "camera") attacked.add("camera");
        if (dstNode === "byod")   attacked.add("byod");

        if (a.src_ip === "192.168.50.10" || a.dst_ip === "192.168.50.10") active.add("router-camera");
        if (a.src_ip === "192.168.50.40" || a.dst_ip === "192.168.50.40") active.add("router-byod");
        active.add("pi-switch"); active.add("switch-backend"); active.add("backend-pipeline");
        active.add("pipeline-analyst");
      });
      setAttackedNodes(attacked);
      setActiveEdges(active);

      // Pipeline stages active if pipeline is running
      if (statusRes?.pipeline) {
        setActiveStages(["t1","t2","t3","t4","t5","t6","t7"]);
      } else {
        setActiveStages([]);
      }

      // Inject packets on active edges
      al.slice(0, 3).forEach(a => {
        const color = a.severity === "CRITICAL" ? C.red : a.severity === "HIGH" ? C.orange :
                      a.severity === "MEDIUM"   ? C.yellow : C.green;
        ["pi-switch", "switch-backend", "backend-pipeline"].forEach(eid => {
          if (!pktsRef.current[eid]) pktsRef.current[eid] = [];
          if (pktsRef.current[eid].length < 3) {
            pktsRef.current[eid].push(makePacket(eid, color, a.severity));
          }
        });
        if (attacked.has("kali")) {
          ["kali-camera", "kali-byod"].forEach(eid => {
            if (!pktsRef.current[eid]) pktsRef.current[eid] = [];
            if (pktsRef.current[eid].length < 2) {
              pktsRef.current[eid].push(makePacket(eid, C.red, "ATK"));
            }
          });
        }
      });

      // Always keep a slow idle packet on wired links
      ["pi-switch", "switch-backend"].forEach(eid => {
        if (!pktsRef.current[eid]) pktsRef.current[eid] = [];
        if (pktsRef.current[eid].length === 0) {
          pktsRef.current[eid].push(makePacket(eid, `${C.accent}`, "pkt"));
        }
      });

    } catch (_) {}
  }, []);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 6000);
    return () => clearInterval(id);
  }, [loadData]);

  // ── Packet animation loop ─────────────────────────────────────────────────
  useEffect(() => {
    const tick = () => {
      Object.entries(pktsRef.current).forEach(([eid, pkts]) => {
        pktsRef.current[eid] = pkts
          .map(p => ({ ...p, t: p.t + p.speed }))
          .filter(p => p.t < 1.05);
      });
      setPackets({ ...pktsRef.current });
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const activeNodes = new Set();
  if (status?.pipeline) { activeNodes.add("backend"); activeNodes.add("pipeline"); }
  if (status?.zeek)     activeNodes.add("pi");
  activeNodes.add("router"); activeNodes.add("switch");
  if (alerts.length > 0) { activeNodes.add("camera"); activeNodes.add("byod"); }

  return (
    <div style={{ position: "relative" }}>
      {/* ── Main topology SVG ── */}
      <div style={{ position: "relative" }}>
        <svg
          viewBox="0 0 900 500"
          width="100%"
          style={{
            background: C.bg, borderRadius: 10,
            border: `1px solid ${C.border}`,
          }}
        >
          {/* Grid background */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#0a0a1a" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="900" height="500" fill="url(#grid)" />

          {/* Zone labels */}
          <text x={80}  y={50} textAnchor="middle" fill="#2a2a55" fontSize="10" fontFamily="monospace" fontWeight="700" letterSpacing="2">CAPTURE ZONE</text>
          <text x={490} y={50} textAnchor="middle" fill="#2a2a55" fontSize="10" fontFamily="monospace" fontWeight="700" letterSpacing="2">DETECTION ZONE</text>
          <text x={700} y={50} textAnchor="middle" fill="#2a2a55" fontSize="10" fontFamily="monospace" fontWeight="700" letterSpacing="2">IOT DEVICES</text>

          {/* Zone dividers */}
          <line x1={190} y1={30} x2={190} y2={470} stroke="#0d0d22" strokeWidth={1} strokeDasharray="4 8" />
          <line x1={620} y1={30} x2={620} y2={470} stroke="#0d0d22" strokeWidth={1} strokeDasharray="4 8" />

          {/* Edges (behind nodes) */}
          {EDGES.map(edge => (
            <Edge
              key={edge.id}
              edge={edge}
              packets={(packets[edge.id] || []).filter(p => p.t >= 0 && p.t <= 1)}
            />
          ))}

          {/* Nodes */}
          {Object.values(NODES).map(node => (
            <NodeBox
              key={node.id}
              node={node}
              active={activeNodes.has(node.id)}
              attacked={attackedNodes.has(node.id)}
              selected={selected === node.id}
              onClick={id => setSelected(selected === id ? null : id)}
            />
          ))}

          {/* Legend */}
          <Legend />

          {/* Refresh button */}
          <g style={{ cursor: "pointer" }} onClick={loadData}>
            <rect x={850} y={10} width={40} height={20} rx={4}
              fill="#0a0a18" stroke={C.border} />
            <text x={870} y={24} textAnchor="middle" fill={C.dim} fontSize="13">⟳</text>
          </g>
        </svg>

        {/* Node detail panel */}
        {selected && (
          <NodeDetail
            nodeId={selected}
            alerts={alerts}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      {/* ── Pipeline thread strip ── */}
      <PipelineStrip activeStages={activeStages} />

      {/* ── Status row ── */}
      <div style={{
        display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap",
      }}>
        {[
          { label: "Pipeline",  ok: status?.pipeline, icon: "⚡" },
          { label: "Zeek",      ok: status?.zeek,     icon: "🔍" },
          { label: "Database",  ok: status?.database,  icon: "🗄" },
          { label: "ML Models", ok: status?.models,    icon: "🧠" },
          { label: `${alerts.length} Alerts`, ok: true, icon: "🚨", special: true },
          { label: `${attackedNodes.size} Attacked`, ok: attackedNodes.size === 0, icon: "🛡", invert: true },
        ].map(item => (
          <div key={item.label} style={{
            display: "flex", alignItems: "center", gap: 5,
            background: item.special ? "#00d4ff10" : item.invert
              ? (item.ok ? "#4caf5010" : "#ff2d2d10")
              : (item.ok ? "#4caf5010" : "#33333310"),
            border: `1px solid ${item.special ? "#00d4ff33" : item.invert
              ? (item.ok ? "#4caf5033" : "#ff2d2d55")
              : (item.ok ? "#4caf5033" : "#333")}`,
            borderRadius: 6, padding: "4px 10px",
          }}>
            <span style={{ fontSize: 11 }}>{item.icon}</span>
            <span style={{
              fontSize: 9, fontWeight: 700, letterSpacing: 0.8,
              color: item.special ? "#00d4ff" : item.invert
                ? (item.ok ? "#4caf50" : "#ff2d2d")
                : (item.ok ? "#4caf50" : "#555"),
            }}>
              {item.label}
            </span>
          </div>
        ))}

        <div style={{ marginLeft: "auto", color: C.dim, fontSize: 9, alignSelf: "center" }}>
          Click any node for details
        </div>
      </div>
    </div>
  );
}
