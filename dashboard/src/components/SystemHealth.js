import React, { useEffect, useState } from "react";
import { fetchPrometheus } from "../services/api";

function MetricRow({ label, value, unit, warn, crit, raw }) {
  const num = parseFloat(raw ?? value);
  const color = isNaN(num) ? "#555"
    : num >= crit ? "#ff2d2d"
    : num >= warn ? "#ffd700"
    : "#4caf50";

  const pct = isNaN(num) ? 0 : Math.min((num / crit) * 100, 100);

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: "#888" }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: "bold", color, fontFamily: "monospace" }}>
          {isNaN(num) ? "—" : `${typeof value === "string" ? value : num.toFixed(1)}${unit}`}
        </span>
      </div>
      <div style={{ background: "#1a1a35", borderRadius: 3, height: 4 }}>
        <div style={{
          width: `${pct}%`, height: "100%", borderRadius: 3,
          background: color,
          boxShadow: `0 0 6px ${color}`,
          transition: "width 0.5s ease",
        }} />
      </div>
    </div>
  );
}

export default function SystemHealth() {
  const [m, setM] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const [cpu, queue, latency, loss] = await Promise.all([
          fetchPrometheus('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'),
          fetchPrometheus("pipeline_queue_depth"),
          fetchPrometheus("inference_latency_ms"),
          fetchPrometheus("packet_loss_pct"),
        ]);
        const v = r => parseFloat(r?.data?.result?.[0]?.value?.[1] ?? "NaN");
        setM({ cpu: v(cpu), queue: v(queue), latency: v(latency), loss: v(loss) });
      } catch (_) {}
    }
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <MetricRow label="CPU Usage"         raw={m.cpu}     value={isNaN(m.cpu) ? "—" : m.cpu?.toFixed(1)}     unit="%" warn={60} crit={85} />
      <MetricRow label="ML Queue Depth"    raw={m.queue}   value={isNaN(m.queue) ? "—" : m.queue?.toFixed(0)} unit=""  warn={300} crit={800} />
      <MetricRow label="Inference Latency" raw={m.latency} value={isNaN(m.latency) ? "—" : m.latency?.toFixed(1)} unit="ms" warn={3} crit={5} />
      <MetricRow label="Packet Loss"       raw={m.loss}    value={isNaN(m.loss) ? "—" : m.loss?.toFixed(1)}   unit="%" warn={5} crit={20} />

      <div style={{ borderTop: "1px solid #1a1a35", paddingTop: 10, marginTop: 4 }}>
        <div style={{ fontSize: 10, color: "#555", marginBottom: 6 }}>SERVICES</div>
        {[
          { name: "Pipeline",   port: 9091 },
          { name: "API",        port: 8000 },
          { name: "PostgreSQL", port: 5432 },
        ].map(s => (
          <div key={s.name} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 11, color: "#888" }}>{s.name}</span>
            <span style={{ fontSize: 10, color: "#4caf50" }}>● RUNNING</span>
          </div>
        ))}
      </div>
    </div>
  );
}
