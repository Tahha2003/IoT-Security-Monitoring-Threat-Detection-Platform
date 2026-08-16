import React, { useEffect, useState, useRef } from "react";
import { fetchAlerts } from "../services/api";

const CARDS = [
  { key: "total",    label: "TOTAL ALERTS",   color: "#ffffff", dimColor: "#888",      border: "#1a1a35",   icon: "📊" },
  { key: "critical", label: "CRITICAL",        color: "#ff2d2d", dimColor: "#ff2d2d44", border: "#ff2d2d44", icon: null },
  { key: "high",     label: "HIGH",            color: "#ff6b00", dimColor: "#ff6b0044", border: "#ff6b0044", icon: null },
  { key: "medium",   label: "MEDIUM",          color: "#ffd700", dimColor: "#ffd70044", border: "#ffd70044", icon: null },
  { key: "low",      label: "LOW",             color: "#4caf50", dimColor: "#4caf5044", border: "#4caf5044", icon: null },
  { key: "live",     label: "LIVE (SESSION)",  color: "#00d4ff", dimColor: "#00d4ff44", border: "#00d4ff44", icon: "⚡" },
];

function AnimatedNumber({ value }) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    if (value === prevRef.current) return;
    const start = prevRef.current;
    const end = value;
    const diff = end - start;
    const steps = Math.min(Math.abs(diff), 30);
    if (steps === 0) return;
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setDisplay(Math.round(start + (diff * step) / steps));
      if (step >= steps) {
        clearInterval(interval);
        prevRef.current = end;
      }
    }, 20);
    return () => clearInterval(interval);
  }, [value]);

  return <>{display.toLocaleString()}</>;
}

function StatCard({ label, value, color, border, icon, dimColor }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? `${dimColor}18` : "#0d0d1c",
        border: `1px solid ${hovered ? border : "#16163a"}`,
        borderRadius: 10,
        padding: "10px 16px",
        flex: 1,
        minWidth: 110,
        transition: "all 0.25s ease",
        boxShadow: hovered ? `0 0 16px ${dimColor}` : "none",
        cursor: "default",
      }}
    >
      <div style={{ fontSize: 9, color: "#444", letterSpacing: 1.5, marginBottom: 6, textTransform: "uppercase" }}>
        {label}
      </div>
      <div style={{
        fontSize: 22, fontWeight: 800, color,
        fontFamily: "monospace",
        display: "flex", alignItems: "center", gap: 6,
        textShadow: hovered ? `0 0 12px ${color}` : "none",
        transition: "text-shadow 0.25s ease",
      }}>
        {icon && <span style={{ fontSize: 14 }}>{icon}</span>}
        <AnimatedNumber value={value} />
      </div>
      {color !== "#ffffff" && color !== "#888" && (
        <div style={{
          width: "100%", height: 2, borderRadius: 1,
          background: `linear-gradient(90deg, ${color}88, transparent)`,
          marginTop: 8,
        }} />
      )}
    </div>
  );
}

export default function StatsBar({ messages }) {
  const [stats, setStats] = useState({ total: 0, critical: 0, high: 0, medium: 0, low: 0 });

  useEffect(() => {
    async function load() {
      try {
        // limit=1 — we only need counts, not rows
        const res = await fetchAlerts(1);
        const sc = res.severity_counts || {};
        setStats({
          total:    res.total    ?? res.count ?? 0,
          critical: sc["CRITICAL"] ?? 0,
          high:     sc["HIGH"]     ?? 0,
          medium:   sc["MEDIUM"]   ?? 0,
          low:      sc["LOW"]      ?? 0,
        });
      } catch (_) {}
    }
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const values = {
    total:    stats.total,
    critical: stats.critical,
    high:     stats.high,
    medium:   stats.medium,
    low:      stats.low,
    live:     messages.length,
  };

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {CARDS.map(c => (
        <StatCard
          key={c.key}
          label={c.label}
          value={values[c.key]}
          color={c.color}
          border={c.border}
          dimColor={c.dimColor}
          icon={c.icon}
        />
      ))}
    </div>
  );
}
