"""
FastAPI API Service — Phase 7
WebSocket /ws  — broadcasts new alerts to all connected dashboard clients
GET /api/alerts — reads from PostgreSQL
POST /api/review/{alert_id} — verdict (FP/TP) + FP export
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras
import secrets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------
# Logging
# ---------------------------
os.makedirs("logs/dashboard", exist_ok=True)
logging.basicConfig(
    filename="logs/dashboard/api_service.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("api.service")

# ---------------------------
# DB config — set env vars on your backend
# ---------------------------
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "fyp_security"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "postgres"),
}

FP_DATASET_PATH = os.getenv("FP_DATASET_PATH", "ml/datasets/fp_dataset.csv")
INTERNAL_TOKEN  = os.getenv("INTERNAL_TOKEN", "changeme-set-this-in-env")

# ---------------------------
# App
# ---------------------------
app = FastAPI(title="IoT IDS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# WebSocket connection manager
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"[WS] Client connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"[WS] Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ---------------------------
# Helpers
# ---------------------------
def get_db():
    return psycopg2.connect(**DB_CONFIG)


def _row_to_dict(row, cursor) -> dict:
    cols = [desc[0] for desc in cursor.description]
    d = dict(zip(cols, row))
    # make timestamp JSON-serializable
    if "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
        d["timestamp"] = d["timestamp"].isoformat()
    return d


# ---------------------------
# Routes
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/alerts")
def get_alerts(limit: int = 100, severity: Optional[str] = None):
    try:
        conn = get_db()
        cur  = conn.cursor()

        # Total count (all rows, no limit) — for StatsBar
        if severity:
            cur.execute(
                "SELECT COUNT(*) FROM alerts WHERE severity=%s",
                (severity.upper(),)
            )
        else:
            cur.execute("SELECT COUNT(*) FROM alerts")
        total = cur.fetchone()[0]

        # Per-severity counts
        cur.execute("""
            SELECT severity, COUNT(*) FROM alerts
            GROUP BY severity
        """)
        severity_counts = {row[0]: row[1] for row in cur.fetchall()}

        # Paginated rows
        if severity:
            cur.execute(
                "SELECT * FROM alerts WHERE severity=%s ORDER BY timestamp DESC LIMIT %s",
                (severity.upper(), limit)
            )
        else:
            cur.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT %s",
                (limit,)
            )

        rows = [_row_to_dict(r, cur) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {
            "alerts": rows,
            "count": len(rows),
            "total": total,
            "severity_counts": severity_counts,
        }

    except Exception as e:
        logger.error(f"[DB] get_alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VerdictRequest(BaseModel):
    verdict: str   # "FP" or "TP"


@app.post("/api/review/{alert_id}")
def review_alert(alert_id: int, body: VerdictRequest):
    verdict = body.verdict.upper()
    if verdict not in ("FP", "TP"):
        raise HTTPException(status_code=400, detail="verdict must be FP or TP")

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute(
            "UPDATE alerts SET verdict=%s WHERE id=%s RETURNING *",
            (verdict, alert_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert = _row_to_dict(row, cur)
        conn.commit()
        cur.close()
        conn.close()

        if verdict == "FP":
            _export_to_fp_dataset(alert)

        return {"status": "updated", "alert": alert}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DB] review_alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _export_to_fp_dataset(alert: dict):
    """Append FP alert features to fp_dataset.csv."""
    header = "duration,packet_count,byte_count,avg_pkt_size,flow_rate,dst_port,protocol,conn_state,dns_query_count,label\n"
    exists = os.path.exists(FP_DATASET_PATH)

    try:
        with open(FP_DATASET_PATH, "a") as f:
            if not exists:
                f.write(header)

            duration     = 0.0
            packet_count = alert.get("packet_count", 0)
            byte_count   = alert.get("byte_count", 0)
            avg_pkt_size = round(byte_count / max(packet_count, 1), 4)
            flow_rate    = round(byte_count / max(duration, 0.001), 4)
            dst_port     = alert.get("dst_port", 0)
            protocol     = alert.get("protocol", "-")
            conn_state   = "-"
            dns_query    = 0
            label        = 0  # FP = normal

            f.write(f"{duration},{packet_count},{byte_count},{avg_pkt_size},"
                    f"{flow_rate},{dst_port},{protocol},{conn_state},{dns_query},{label}\n")

        logger.info(f"[FP] Exported alert {alert.get('id')} to fp_dataset.csv")

    except Exception as e:
        logger.error(f"[FP] Export failed: {e}")


# ---------------------------
# WebSocket endpoint
# ---------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # On connect: replay last 50 alerts from DB so the dashboard
    # populates immediately without waiting for new live traffic.
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 50")
        rows = [_row_to_dict(r, cur) for r in cur.fetchall()]
        cur.close()
        conn.close()
        # Send oldest-first so the client list ends up newest-at-top
        for row in reversed(rows):
            try:
                await ws.send_json(row)
            except Exception:
                break
    except Exception as e:
        logger.warning(f"[WS] seed replay failed: {e}")
    try:
        while True:
            # keep connection alive — client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------
# Internal broadcast endpoint (called by pipeline via HTTP POST)
# ---------------------------
@app.post("/internal/broadcast")
async def internal_broadcast(alert: dict, x_internal_token: str = Header(None)):
    if not secrets.compare_digest(x_internal_token or "", INTERNAL_TOKEN):
        raise HTTPException(status_code=403, detail="Forbidden")
    await manager.broadcast(alert)
    return {"ok": True}


# ---------------------------
# SOAR endpoints
# ---------------------------
@app.get("/api/soar/log")
def soar_log():
    """Recent playbook executions"""
    try:
        import importlib.util, pathlib
        p = pathlib.Path("services/soar-service/engine/soar_engine.py")
        spec = importlib.util.spec_from_file_location("soar_engine", p)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {"log": mod.get_playbook_log()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/soar/quarantined")
def soar_quarantined():
    """List quarantined devices"""
    try:
        import importlib.util, pathlib
        p = pathlib.Path("services/soar-service/engine/soar_engine.py")
        spec = importlib.util.spec_from_file_location("soar_engine", p)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {"quarantined": mod.get_quarantined_devices()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/soar/unblock/{src_ip}")
def soar_unblock(src_ip: str):
    """Unblock an IP — called from dashboard"""
    try:
        import importlib.util, pathlib
        p = pathlib.Path("services/soar-service/engine/soar_engine.py")
        spec = importlib.util.spec_from_file_location("soar_engine", p)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.unblock_ip(src_ip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Playbook toggle endpoints
# ---------------------------
# In-process toggle state — persists for the lifetime of the API service
_playbook_enabled: dict = {
    "block_attacker":    True,
    "camera_defense":    True,
    "quarantine_device": True,
    "scan_detection":    True,
}

@app.get("/api/soar/playbooks")
def get_playbook_status():
    """Return enabled/disabled state of all 4 playbooks"""
    return {"playbooks": _playbook_enabled}

class PlaybookToggle(BaseModel):
    enabled: bool

@app.post("/api/soar/playbooks/{name}")
def toggle_playbook(name: str, body: PlaybookToggle):
    """Enable or disable a playbook by name at runtime"""
    if name not in _playbook_enabled:
        raise HTTPException(status_code=404, detail=f"Unknown playbook: {name}")
    _playbook_enabled[name] = body.enabled
    logger.info(f"[SOAR] Playbook '{name}' set to {'ENABLED' if body.enabled else 'DISABLED'}")
    # Notify soar_engine via shared flag file so the in-process engine picks it up
    try:
        import json, pathlib
        flag_path = pathlib.Path("logs/soar/playbook_flags.json")
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text(json.dumps(_playbook_enabled))
    except Exception:
        pass
    return {"name": name, "enabled": body.enabled}


@app.get("/api/alerts/all")
def get_all_alerts(
    limit: int = 500,
    severity: Optional[str] = None,
    attack_type: Optional[str] = None,
    src_ip: Optional[str] = None,
):
    """Full alert history with filters — used by View All modal"""
    try:
        conn = get_db()
        cur  = conn.cursor()

        conditions = []
        params     = []

        if severity:
            conditions.append("severity = %s")
            params.append(severity.upper())
        if attack_type:
            conditions.append("attack_type ILIKE %s")
            params.append(f"%{attack_type}%")
        if src_ip:
            conditions.append("src_ip = %s")
            params.append(src_ip)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        cur.execute(f"SELECT COUNT(*) FROM alerts {where}", params[:-1])
        total = cur.fetchone()[0]

        cur.execute(
            f"SELECT * FROM alerts {where} ORDER BY timestamp DESC LIMIT %s",
            params
        )
        rows = [_row_to_dict(r, cur) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"alerts": rows, "total": total}

    except Exception as e:
        logger.error(f"[DB] get_all_alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Broadcast helper (called from async context)
# ---------------------------
async def broadcast_alert(alert: dict):
    await manager.broadcast(alert)


# ---------------------------
# System Control endpoints
# All backend management — start, stop, status, logs, db
# ---------------------------
import subprocess as _subprocess
import pathlib as _pathlib
import signal as _signal

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

def _pid_alive(pid_file: str) -> bool:
    """Check if a process tracked by a PID file is still running."""
    p = _pathlib.Path(pid_file)
    if not p.exists():
        return False
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, 0)   # signal 0 = existence check
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


@app.get("/api/system/status")
def system_status():
    """Return running/stopped state of each backend service."""
    pipeline_up = _pid_alive("/tmp/iot_ids_pipeline.pid")

    # In pcap mode there is no standalone zeek -i process and no zeek_live.pid.
    # Instead we check if conn.log was written recently (within 30 s) — that
    # proves zeek_feeder.py successfully ran `zeek -r` on incoming pcap data.
    def _zeek_pcap_active() -> bool:
        import time as _time
        conn_log = _pathlib.Path(_PROJECT_ROOT) / "services/flow_service/logs/zeek/current/conn.log"
        if not conn_log.exists():
            return False
        return (_time.time() - conn_log.stat().st_mtime) < 30

    zeek_up = _pid_alive("/tmp/zeek_live.pid") or _zeek_pcap_active()

    # DB connectivity
    db_ok = False
    try:
        conn = get_db(); conn.close(); db_ok = True
    except Exception:
        pass

    # ML models present
    models_ok = all(
        (_pathlib.Path(_PROJECT_ROOT) / "ml/training/models" / f).exists()
        for f in ("rf_model.pkl", "iso_model.pkl", "preprocessor.pkl")
    )

    # Alert counts
    total_alerts = 0
    recent_alerts = 0
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alerts")
        total_alerts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alerts WHERE timestamp > NOW() - INTERVAL '5 minutes'")
        recent_alerts = cur.fetchone()[0]
        cur.close(); conn.close()
    except Exception:
        pass

    return {
        "pipeline":      pipeline_up,
        "zeek":          zeek_up,
        "database":      db_ok,
        "models":        models_ok,
        "total_alerts":  total_alerts,
        "recent_alerts": recent_alerts,
    }


@app.get("/api/system/interfaces")
def system_interfaces():
    """Return available network interfaces on this machine."""
    try:
        result = _subprocess.run(
            ["ip", "-br", "link", "show"],
            capture_output=True, text=True, timeout=5
        )
        ifaces = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                name = parts[0]
                # Skip loopback and virtual interfaces
                if name not in ("lo",) and not name.startswith(("docker", "veth", "br-", "virbr")):
                    state = parts[1] if len(parts) > 1 else "UNKNOWN"
                    ifaces.append({"name": name, "state": state})
        return {"interfaces": ifaces}
    except Exception as e:
        return {"interfaces": [], "error": str(e)}


@app.post("/api/system/start")
def system_start(zeek_interface: str = "wlxe009bf6913de"):
    """Start the full backend pipeline (equivalent to start_pipeline.sh)."""
    script  = str(_pathlib.Path(_PROJECT_ROOT) / "infrastructure/scripts/start_pipeline.sh")
    log_out = str(_pathlib.Path(_PROJECT_ROOT) / "logs/pipeline/start_pipeline_stdout.log")

    if _pid_alive("/tmp/iot_ids_pipeline.pid"):
        return {"ok": False, "message": "Pipeline is already running"}

    try:
        os.makedirs(os.path.dirname(log_out), exist_ok=True)
        env = os.environ.copy()
        env["ZEEK_INTERFACE"] = zeek_interface
        with open(log_out, "w") as fout:
            proc = _subprocess.Popen(
                ["bash", script],
                cwd=_PROJECT_ROOT,
                stdout=fout,
                stderr=fout,
                env=env,
                start_new_session=True,
            )
        logger.info(f"[SYSTEM] start_pipeline.sh launched (pid={proc.pid}, iface={zeek_interface})")
        return {"ok": True, "message": f"Pipeline starting on {zeek_interface} — watch Startup log tab"}
    except Exception as e:
        logger.error(f"[SYSTEM] start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/stop")
def system_stop():
    """Stop the backend pipeline (equivalent to stop_pipeline.sh)."""
    script = str(_pathlib.Path(_PROJECT_ROOT) / "infrastructure/scripts/stop_pipeline.sh")
    try:
        result = _subprocess.run(
            ["bash", script],
            cwd=_PROJECT_ROOT,
            capture_output=True, text=True, timeout=15,
        )
        logger.info(f"[SYSTEM] stop_pipeline.sh → {result.stdout.strip()}")
        return {"ok": True, "message": result.stdout.strip() or "Pipeline stopped"}
    except Exception as e:
        logger.error(f"[SYSTEM] stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/train")
def system_train():
    """Train ML models (runs model_training.py in background)."""
    models_dir = _pathlib.Path(_PROJECT_ROOT) / "ml/training/models"
    if all((models_dir / f).exists() for f in ("rf_model.pkl", "iso_model.pkl", "preprocessor.pkl")):
        return {"ok": True, "message": "Models already exist — delete them first to retrain"}

    script = str(_pathlib.Path(_PROJECT_ROOT) / "ml/training/model_training.py")
    log_out = str(_pathlib.Path(_PROJECT_ROOT) / "logs/pipeline/model_training.log")
    try:
        os.makedirs(os.path.dirname(log_out), exist_ok=True)
        with open(log_out, "w") as fout:
            _subprocess.Popen(
                ["python3", script],
                cwd=_PROJECT_ROOT,
                stdout=fout, stderr=fout,
                start_new_session=True,
            )
        return {"ok": True, "message": "Model training started (~60s) — watch logs/pipeline/model_training.log"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/reset-firewall")
def system_reset_firewall():
    """Reset UFW/iptables SOAR rules."""
    script = str(_pathlib.Path(_PROJECT_ROOT) / "infrastructure/scripts/reset_firewall.sh")
    try:
        result = _subprocess.run(
            ["bash", script], cwd=_PROJECT_ROOT,
            capture_output=True, text=True, timeout=15,
        )
        return {"ok": True, "message": result.stdout.strip() or "Firewall reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/clear-db")
def system_clear_db():
    """Truncate alerts table — fresh start."""
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("TRUNCATE TABLE alerts RESTART IDENTITY")
        conn.commit()
        cur.close(); conn.close()
        logger.warning("[SYSTEM] alerts table truncated")
        return {"ok": True, "message": "Database cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/logs/{service}")
def system_logs(service: str, lines: int = 40):
    """Tail a log file. service = pipeline | api | zeek | soar | ml"""
    log_map = {
        "pipeline":  "logs/pipeline/main_pipeline.log",
        "api":       "logs/dashboard/uvicorn.log",
        "zeek":      "logs/pipeline/zeek_feeder.log",
        "zeek_live": "logs/pipeline/zeek_live.log",
        "parser":    "logs/pipeline/zeek_parser.log",
        "ml":        "logs/pipeline/ml_inference.log",
        "dpi":       "logs/pipeline/dpi_worker.log",
        "soar":      "logs/siem/soar_engine.log",
        "siem":      "logs/siem/batch_writer.log",
        "startup":   "logs/pipeline/start_pipeline_stdout.log",
        "training":  "logs/pipeline/model_training.log",
    }
    if service not in log_map:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}. Valid: {list(log_map)}")
    log_path = _pathlib.Path(_PROJECT_ROOT) / log_map[service]
    if not log_path.exists():
        return {"lines": [], "path": str(log_map[service])}
    try:
        result = _subprocess.run(
            ["tail", f"-{lines}", str(log_path)],
            capture_output=True, text=True
        )
        return {
            "lines": result.stdout.splitlines(),
            "path": log_map[service],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
