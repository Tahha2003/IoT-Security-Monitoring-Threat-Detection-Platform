// NOTE: Update API_BASE to your backend IP before running
const API_BASE = process.env.REACT_APP_API_URL || "http://192.168.1.20:8000";

export async function fetchAlerts(limit = 100) {
  const res = await fetch(`${API_BASE}/api/alerts?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function fetchAllAlerts({ limit = 500, severity, attackType, srcIp } = {}) {
  const params = new URLSearchParams();
  params.set("limit", limit);
  if (severity)   params.set("severity", severity);
  if (attackType) params.set("attack_type", attackType);
  if (srcIp)      params.set("src_ip", srcIp);
  const res = await fetch(`${API_BASE}/api/alerts/all?${params}`);
  if (!res.ok) throw new Error("Failed to fetch all alerts");
  return res.json();
}

export async function submitVerdict(alertId, verdict) {
  const res = await fetch(`${API_BASE}/api/review/${alertId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verdict }),
  });
  if (!res.ok) throw new Error("Failed to submit verdict");
  return res.json();
}

export async function fetchPrometheus(query) {
  const PROM_URL = process.env.REACT_APP_PROM_URL || "http://192.168.1.20:9090";
  const res = await fetch(
    `${PROM_URL}/api/v1/query?query=${encodeURIComponent(query)}`
  );
  if (!res.ok) throw new Error("Prometheus query failed");
  return res.json();
}

export async function fetchSoarLog() {
  const res = await fetch(`${API_BASE}/api/soar/log`);
  if (!res.ok) throw new Error("Failed to fetch SOAR log");
  return res.json();
}

export async function fetchPlaybookStatus() {
  const res = await fetch(`${API_BASE}/api/soar/playbooks`);
  if (!res.ok) throw new Error("Failed to fetch playbook status");
  return res.json();
}

export async function togglePlaybook(name, enabled) {
  const res = await fetch(`${API_BASE}/api/soar/playbooks/${name}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error("Failed to toggle playbook");
  return res.json();
}

export async function fetchSystemStatus() {
  const res = await fetch(`${API_BASE}/api/system/status`);
  if (!res.ok) throw new Error("Failed to fetch system status");
  return res.json();
}

export async function startPipeline() {
  const res = await fetch(`${API_BASE}/api/system/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start pipeline");
  return res.json();
}

export async function stopPipeline() {
  const res = await fetch(`${API_BASE}/api/system/stop`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to stop pipeline");
  return res.json();
}

export async function trainModels() {
  const res = await fetch(`${API_BASE}/api/system/train`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start training");
  return res.json();
}

export async function resetFirewall() {
  const res = await fetch(`${API_BASE}/api/system/reset-firewall`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset firewall");
  return res.json();
}

export async function clearDatabase() {
  const res = await fetch(`${API_BASE}/api/system/clear-db`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to clear database");
  return res.json();
}

export async function fetchLogs(service, lines = 40) {
  const res = await fetch(`${API_BASE}/api/system/logs/${service}?lines=${lines}`);
  if (!res.ok) throw new Error("Failed to fetch logs");
  return res.json();
}
