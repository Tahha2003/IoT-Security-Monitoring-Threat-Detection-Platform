import React, { useEffect, useRef, useState, useCallback } from "react";
import { fetchAlerts } from "../services/api";

// ─── Config ──────────────────────────────────────────────────────────────────
const W          = 1000;   // SVG viewBox width
const H          = 160;    // SVG viewBox height
const BASELINE   = 115;    // y position of the flat line
const MAX_PTS    = 220;    // total points kept in the rolling buffer
const TICK_MS    = 40;     // animation frame interval — 25 fps
const ADV_PER_TICK = 2.5;  // pixels scrolled per tick  (scroll speed)
const SEV_HEIGHT = { CRITICAL: 90, HIGH: 65, MEDIUM: 42, LOW: 22 };
const SEV_COLOR  = { CRITICAL: "#ff2d2d", HIGH: "#ff6b00", MEDIUM: "#ffd700", LOW: "#4caf50" };

// Build the ECG spike shape for one alert
// Returns an array of {dx, dy} offsets from the baseline insertion point
function spikeOffsets(severity) {
  const h = SEV_HEIGHT[severity] || 20;
  return [
    { dx: 0,   dy: 0       },   // flat lead-in
    { dx: 4,   dy: -6      },   // small pre-notch up
    { dx: 3,   dy: 8       },   // pre-notch down (Q)
    { dx: 4,   dy: -(h)    },   // main spike up (R)
    { dx: 4,   dy: h * 0.55},   // sharp fall (S)
    { dx: 4,   dy: -h*0.15 },   // small bounce (J-point)
    { dx: 10,  dy: 0       },   // ST segment
    { dx: 6,   dy: -h*0.12},    // T-wave up
    { dx: 6,   dy: h*0.12  },   // T-wave down
    { dx: 8,   dy: 0       },   // return to baseline
  ];
}

// ─── Dot that travels along the line ─────────────────────────────────────────
// We track the rightmost point of the drawn path so the dot sits on the tip.

// ─── Main component ───────────────────────────────────────────────────────────
export default function AttackTimeline() {
  // Each point: { x, y, color }
  const ptsRef      = useRef([]);
  const offsetXRef  = useRef(0);      // how many px the canvas has scrolled
  const [path, setPath]   = useState("");
  const [dotPos, setDotPos] = useState({ x: W, y: BASELINE });
  const [dotColor, setDotColor] = useState("#00d4ff");
  const [gradColor, setGradColor] = useState("#00d4ff");
  const lastAlertRef = useRef(null);  // timestamp of newest alert already spiked

  // ── Seed flat baseline points on mount ──────────────────────────────────
  useEffect(() => {
    const pts = [];
    for (let x = 0; x <= W; x += 4) {
      pts.push({ x, y: BASELINE, color: "#00d4ff" });
    }
    ptsRef.current = pts;
  }, []);

  // ── Fetch alerts and inject spikes ──────────────────────────────────────
  const injectAlerts = useCallback(async () => {
    try {
      const res = await fetchAlerts(60);
      const alerts = (res.alerts || [])
        .filter(a => a.timestamp && a.severity)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      // Only inject alerts newer than last processed
      const newAlerts = lastAlertRef.current
        ? alerts.filter(a => new Date(a.timestamp) > new Date(lastAlertRef.current))
        : alerts.slice(-5);   // on first load just show last 5

      if (newAlerts.length === 0) return;
      lastAlertRef.current = newAlerts[newAlerts.length - 1].timestamp;

      // Append spike points for each new alert
      newAlerts.forEach(alert => {
        const color   = SEV_COLOR[alert.severity] || "#00d4ff";
        const offsets = spikeOffsets(alert.severity);
        const pts     = ptsRef.current;
        let   curX    = pts.length > 0 ? pts[pts.length - 1].x + 12 : W;

        offsets.forEach(({ dx, dy }) => {
          curX += dx;
          const prevY = pts.length > 0 ? pts[pts.length - 1].y : BASELINE;
          pts.push({ x: curX, y: prevY + dy, color });
        });
        // Return to baseline after spike
        pts.push({ x: curX + 6, y: BASELINE, color });
      });
    } catch (_) {}
  }, []);

  useEffect(() => {
    injectAlerts();
    const id = setInterval(injectAlerts, 5000);
    return () => clearInterval(id);
  }, [injectAlerts]);

  // ── Animation loop — scroll canvas left ─────────────────────────────────
  useEffect(() => {
    let animId;
    const tick = () => {
      const pts = ptsRef.current;
      if (pts.length === 0) { animId = setTimeout(tick, TICK_MS); return; }

      // Advance scroll offset
      offsetXRef.current += ADV_PER_TICK;

      // Cull points that have scrolled off the left edge
      const cutoff = offsetXRef.current - 20;
      while (pts.length > 0 && pts[0].x < cutoff) pts.shift();

      // Keep buffer from growing forever — trim head if too long
      if (pts.length > MAX_PTS) pts.splice(0, pts.length - MAX_PTS);

      // Add flat baseline point at right edge to keep line going
      const lastX = pts.length > 0 ? pts[pts.length - 1].x : offsetXRef.current;
      if (lastX < offsetXRef.current + W + 20) {
        pts.push({ x: lastX + ADV_PER_TICK * 2, y: BASELINE, color: "#00d4ff" });
      }

      // Build SVG path — translate x by -offsetXRef so points scroll left
      if (pts.length < 2) { animId = setTimeout(tick, TICK_MS); return; }

      const ox = offsetXRef.current;
      let d = "";
      let lastColor = pts[0].color;
      let segStart  = 0;
      const segments = [];   // [{color, points:[]}]

      // Group consecutive same-colour points into segments
      pts.forEach((p, i) => {
        if (p.color !== lastColor || i === pts.length - 1) {
          segments.push({
            color: lastColor,
            pts: pts.slice(segStart, i === pts.length - 1 ? i + 1 : i),
          });
          segStart  = i;
          lastColor = p.color;
        }
      });

      // Build one path per colour segment
      const pathParts = segments.map(seg => {
        if (seg.pts.length < 2) return null;
        const pp = seg.pts.map(p => `${(p.x - ox).toFixed(1)},${p.y.toFixed(1)}`);
        return { color: seg.color, d: `M ${pp[0]} L ${pp.slice(1).join(" L ")}` };
      }).filter(Boolean);

      // Dot position = rightmost rendered point
      const last = pts[pts.length - 1];
      const dotX = Math.min(last.x - ox, W - 4);
      const dotY = last.y;
      const dColor = last.color;

      setPath(pathParts);
      setDotPos({ x: dotX, y: dotY });
      setDotColor(dColor);

      // Gradient colour = highest severity in current view
      const visibleColors = pts.map(p => p.color);
      const priority = ["#ff2d2d", "#ff6b00", "#ffd700", "#4caf50", "#00d4ff"];
      const topColor = priority.find(c => visibleColors.includes(c)) || "#00d4ff";
      setGradColor(topColor);

      animId = setTimeout(tick, TICK_MS);
    };

    animId = setTimeout(tick, TICK_MS);
    return () => clearTimeout(animId);
  }, []);

  return (
    <div style={{ position: "relative" }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ display: "block", overflow: "hidden" }}
        preserveAspectRatio="none"
      >
        <defs>
          {/* Fade mask — left edge fades out */}
          <linearGradient id="at-fade" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#080812" stopOpacity="1" />
            <stop offset="6%"   stopColor="#080812" stopOpacity="0" />
            <stop offset="92%"  stopColor="#080812" stopOpacity="0" />
            <stop offset="100%" stopColor="#080812" stopOpacity="1" />
          </linearGradient>
          <filter id="at-glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <filter id="at-dot-glow">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* ── Grid lines ── */}
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f}
            x1={0} y1={H * f} x2={W} y2={H * f}
            stroke="#0f0f22" strokeWidth={1}
          />
        ))}
        {/* Baseline rule */}
        <line x1={0} y1={BASELINE} x2={W} y2={BASELINE}
          stroke="#1a1a35" strokeWidth={1} strokeDasharray="4 8"
        />

        {/* ── ECG line segments (one per colour) ── */}
        {Array.isArray(path) && path.map((seg, i) => (
          <path
            key={i}
            d={seg.d}
            fill="none"
            stroke={seg.color}
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#at-glow)"
            style={{ opacity: 0.9 }}
          />
        ))}

        {/* ── Travelling dot ── */}
        {/* Outer glow ring */}
        <circle
          cx={dotPos.x} cy={dotPos.y} r={7}
          fill="none"
          stroke={dotColor}
          strokeWidth={1}
          opacity={0.3}
          filter="url(#at-dot-glow)"
        />
        {/* Inner dot */}
        <circle
          cx={dotPos.x} cy={dotPos.y} r={4}
          fill={dotColor}
          filter="url(#at-dot-glow)"
        />
        {/* Centre pinpoint */}
        <circle cx={dotPos.x} cy={dotPos.y} r={1.5} fill="#fff" />

        {/* ── Fade overlay (left & right edges) ── */}
        <rect x={0} y={0} width={W} height={H} fill="url(#at-fade)" />
      </svg>

      {/* ── Legend ── */}
      <div style={{
        display: "flex", gap: 14, justifyContent: "center",
        marginTop: 6, flexWrap: "wrap",
      }}>
        {Object.entries(SEV_COLOR).map(([sev, col]) => (
          <div key={sev} style={{
            display: "flex", alignItems: "center", gap: 5,
          }}>
            <div style={{
              width: 22, height: 2.5, background: col, borderRadius: 2,
              boxShadow: `0 0 5px ${col}`,
            }} />
            <span style={{ color: col, fontSize: 9, fontWeight: 700, letterSpacing: 1 }}>
              {sev}
            </span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "#00d4ff", boxShadow: "0 0 6px #00d4ff",
          }} />
          <span style={{ color: "#00d4ff", fontSize: 9, fontWeight: 700, letterSpacing: 1 }}>
            LIVE
          </span>
        </div>
      </div>
    </div>
  );
}
