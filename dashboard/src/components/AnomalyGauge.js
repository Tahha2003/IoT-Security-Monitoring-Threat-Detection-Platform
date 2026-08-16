import React, { useEffect, useRef, useState } from "react";

// ─── Gauge dimensions ────────────────────────────────────────────────────────
const W  = 240;
const H  = 145;   // half-circle + needle + labels
const CX = 120;   // pivot x
const CY = 130;   // pivot y  (near bottom edge)
const RO = 104;   // outer radius
const RI = 66;    // inner radius  → band thickness = 38px

// ─── Severity zones — aligned to project thresholds ─────────────────────────
// risk_scorer.py: LOW < 0.35, MEDIUM 0.35–0.60, HIGH 0.60–0.80, CRITICAL >= 0.80
const ZONES = [
  { from: 0,  to: 35, color: "#4caf50", label: "LOW"      },
  { from: 35, to: 60, color: "#ffd700", label: "MEDIUM"   },
  { from: 60, to: 80, color: "#ff6b00", label: "HIGH"     },
  { from: 80, to: 100,color: "#ff2d2d", label: "CRITICAL" },
];

// ─── Maths helpers ───────────────────────────────────────────────────────────
// pct 0 → left end (angle 180°), pct 100 → right end (angle 0°)
function pctToAngle(pct) {
  return 180 - pct * 1.8;   // degrees, standard math convention
}

function polarXY(angleDeg, r) {
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: CX + r * Math.cos(rad),
    y: CY - r * Math.sin(rad),   // SVG y-axis is inverted
  };
}

// Filled arc segment (donut slice) from pct1 to pct2
function zonePath(p1, p2) {
  const a1 = pctToAngle(p1);
  const a2 = pctToAngle(p2);
  const o1 = polarXY(a1, RO);
  const o2 = polarXY(a2, RO);
  const i1 = polarXY(a1, RI);
  const i2 = polarXY(a2, RI);
  const span = p2 - p1;
  const large = span > 50 ? 1 : 0;
  // outer arc goes from a1→a2 clockwise (flag=1 in SVG = counter-clockwise maths)
  return [
    `M ${o1.x.toFixed(2)} ${o1.y.toFixed(2)}`,
    `A ${RO} ${RO} 0 ${large} 1 ${o2.x.toFixed(2)} ${o2.y.toFixed(2)}`,
    `L ${i2.x.toFixed(2)} ${i2.y.toFixed(2)}`,
    `A ${RI} ${RI} 0 ${large} 0 ${i1.x.toFixed(2)} ${i1.y.toFixed(2)}`,
    "Z",
  ].join(" ");
}

// Needle — thin pointed shape, pivot at CX/CY, tip at outer radius
function needlePath(pct) {
  const angle = pctToAngle(Math.max(0.5, Math.min(pct, 99.5)));
  const tip   = polarXY(angle, RO - 6);

  // Two base points perpendicular to the needle direction
  const perpAngle1 = angle + 90;
  const perpAngle2 = angle - 90;
  const bw = 6;   // half base-width
  const b1 = polarXY(perpAngle1, bw);
  const b2 = polarXY(perpAngle2, bw);

  // Base points are offset from pivot toward the opposite side
  const tail = polarXY(angle + 180, 14);

  return [
    `M ${tip.x.toFixed(2)} ${tip.y.toFixed(2)}`,
    `L ${b1.x.toFixed(2)} ${b1.y.toFixed(2)}`,
    `L ${tail.x.toFixed(2)} ${tail.y.toFixed(2)}`,
    `L ${b2.x.toFixed(2)} ${b2.y.toFixed(2)}`,
    "Z",
  ].join(" ");
}

function zoneForPct(pct) {
  return ZONES.slice().reverse().find(z => pct >= z.from) || ZONES[0];
}

// ─── Smooth animation hook ───────────────────────────────────────────────────
function useSmooth(target, ms = 700) {
  const [val, setVal] = useState(target);
  const rafRef  = useRef(null);
  const fromRef = useRef(target);
  const t0Ref   = useRef(null);

  useEffect(() => {
    fromRef.current = val;
    t0Ref.current   = null;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);

    const tick = (ts) => {
      if (!t0Ref.current) t0Ref.current = ts;
      const elapsed = ts - t0Ref.current;
      const progress = Math.min(elapsed / ms, 1);
      const ease = 1 - Math.pow(1 - progress, 3);   // ease-out cubic
      setVal(fromRef.current + (target - fromRef.current) * ease);
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [target]); // eslint-disable-line

  return val;
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function AnomalyGauge({ messages }) {
  const latest  = messages[0];
  const rawPct  = latest ? Math.round(parseFloat(latest.risk_score) * 100) : 0;
  const pct     = useSmooth(rawPct);
  const zone    = zoneForPct(pct);
  const color   = zone.color;

  // separator lines between zones
  const separators = [35, 60, 80];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 240, display: "block", overflow: "visible" }}>
        <defs>
          <filter id="ag-glow">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          {/* dark background fill for inner circle area */}
          <clipPath id="ag-semicircle">
            <path d={`M ${polarXY(180, RO+2).x} ${polarXY(180, RO+2).y}
                      A ${RO+2} ${RO+2} 0 0 1 ${polarXY(0, RO+2).x} ${polarXY(0, RO+2).y}
                      L ${CX + RO + 2} ${CY} L ${CX - RO - 2} ${CY} Z`} />
          </clipPath>
        </defs>

        {/* ── Outer border ring (grey) ── */}
        <path
          d={`M ${polarXY(180, RO+4).x} ${polarXY(180, RO+4).y}
              A ${RO+4} ${RO+4} 0 0 1 ${polarXY(0, RO+4).x} ${polarXY(0, RO+4).y}`}
          fill="none" stroke="#1a1a2e" strokeWidth={3}
        />

        {/* ── Colour zone segments ── */}
        {ZONES.map((z) => (
          <path
            key={z.label}
            d={zonePath(z.from, z.to)}
            fill={z.color}
            opacity={0.88}
          />
        ))}

        {/* ── Separator lines between zones ── */}
        {separators.map(p => {
          const outer = polarXY(pctToAngle(p), RO + 3);
          const inner = polarXY(pctToAngle(p), RI - 3);
          return (
            <line
              key={p}
              x1={outer.x} y1={outer.y}
              x2={inner.x} y2={inner.y}
              stroke="#080812"
              strokeWidth={3}
            />
          );
        })}

        {/* ── Inner background (covers centre of donut) ── */}
        <path
          d={`M ${polarXY(180, RI-1).x} ${polarXY(180, RI-1).y}
              A ${RI-1} ${RI-1} 0 0 1 ${polarXY(0, RI-1).x} ${polarXY(0, RI-1).y}
              L ${CX} ${CY} Z`}
          fill="#0d0d1c"
        />

        {/* ── Zone labels inside the band ── */}
        {ZONES.map(z => {
          const mid = (z.from + z.to) / 2;
          const pos = polarXY(pctToAngle(mid), (RO + RI) / 2);
          return (
            <text
              key={z.label}
              x={pos.x} y={pos.y}
              textAnchor="middle" dominantBaseline="middle"
              fill="#00000099"
              fontSize={z.label === "CRITICAL" ? "7.5" : "8.5"}
              fontWeight="900"
              fontFamily="monospace"
              letterSpacing="0.5"
            >
              {z.label}
            </text>
          );
        })}

        {/* ── Tick marks at zone boundaries + ends ── */}
        {[0, 35, 60, 80, 100].map(p => {
          const outer = polarXY(pctToAngle(p), RO + 8);
          const inner = polarXY(pctToAngle(p), RO + 2);
          return (
            <line key={p}
              x1={outer.x} y1={outer.y}
              x2={inner.x} y2={inner.y}
              stroke="#444466" strokeWidth={1.5}
            />
          );
        })}

        {/* ── Pct labels at 0 / 35 / 60 / 80 / 100 ── */}
        {[
          { p: 0,   text: "0" },
          { p: 35,  text: "35" },
          { p: 60,  text: "60" },
          { p: 80,  text: "80" },
          { p: 100, text: "100" },
        ].map(({ p, text }) => {
          const pos = polarXY(pctToAngle(p), RO + 18);
          return (
            <text key={p}
              x={pos.x} y={pos.y}
              textAnchor="middle" dominantBaseline="middle"
              fill="#333355" fontSize="8" fontFamily="monospace"
            >
              {text}
            </text>
          );
        })}

        {/* ── Needle shadow ── */}
        <path
          d={needlePath(pct)}
          fill="#000000aa"
          transform="translate(2,3)"
        />

        {/* ── Needle ── */}
        <path
          d={needlePath(pct)}
          fill="#e8e8f0"
          style={{ filter: "drop-shadow(0 0 3px #ffffff55)" }}
        />

        {/* ── Hub outer ring ── */}
        <circle cx={CX} cy={CY} r={14} fill="#0d0d1c" stroke="#333355" strokeWidth={2} />

        {/* ── Hub inner circle — colour-matched ── */}
        <circle cx={CX} cy={CY} r={8} fill={color}
          style={{
            filter: `drop-shadow(0 0 6px ${color})`,
            transition: "fill 0.5s ease",
          }}
        />
        <circle cx={CX} cy={CY} r={3.5} fill="#0d0d1c" />

        {/* ── Score number ── */}
        <text
          x={CX} y={CY - 34}
          textAnchor="middle"
          fill={color}
          fontSize="24"
          fontWeight="bold"
          fontFamily="monospace"
          style={{ transition: "fill 0.4s ease" }}
        >
          {Math.round(pct)}%
        </text>

        {/* ── Severity label ── */}
        <text
          x={CX} y={CY - 14}
          textAnchor="middle"
          fill={color}
          fontSize="9"
          fontWeight="700"
          letterSpacing="2"
          fontFamily="monospace"
          style={{ transition: "fill 0.4s ease" }}
        >
          {zone.label}
        </text>
      </svg>

      {/* ── Alert info below gauge ── */}
      <div style={{ textAlign: "center", marginTop: 4, lineHeight: 1.8 }}>
        {latest ? (
          <>
            <div style={{ color: "#00d4ff", fontFamily: "monospace", fontSize: 12, fontWeight: 700 }}>
              {latest.src_ip}
            </div>
            <div style={{ color: "#e94560", fontSize: 11, fontWeight: 600 }}>
              {latest.attack_type}
            </div>
            <div style={{ color: "#444", fontSize: 10, fontFamily: "monospace" }}>
              {new Date(latest.timestamp).toLocaleTimeString()}
            </div>
          </>
        ) : (
          <div style={{ color: "#2a2a45", fontSize: 11, letterSpacing: 1 }}>
            Waiting for alerts...
          </div>
        )}
      </div>
    </div>
  );
}
