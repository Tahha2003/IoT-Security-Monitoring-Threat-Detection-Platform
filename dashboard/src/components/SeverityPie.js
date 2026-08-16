import React, { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { fetchAlerts } from "../services/api";

const COLORS = { CRITICAL: "#ff2d2d", HIGH: "#ff8c00", MEDIUM: "#ffd700", LOW: "#4caf50" };

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div style={{ background: "#0f0f1e", border: "1px solid #1a1a35", padding: "6px 12px", borderRadius: 6 }}>
      <span style={{ color: COLORS[name], fontWeight: "bold" }}>{name}: {value}</span>
    </div>
  );
};

export default function SeverityPie() {
  const [data, setData] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchAlerts(1000);
        const counts = {};
        res.alerts.forEach(a => { counts[a.severity] = (counts[a.severity] || 0) + 1; });
        setData(["CRITICAL","HIGH","MEDIUM","LOW"]
          .filter(s => counts[s])
          .map(s => ({ name: s, value: counts[s] })));
      } catch (_) {}
    }
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%"
          innerRadius={45} outerRadius={70} paddingAngle={3}>
          {data.map(e => (
            <Cell key={e.name} fill={COLORS[e.name]}
              style={{ filter: `drop-shadow(0 0 4px ${COLORS[e.name]})` }} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#666" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
