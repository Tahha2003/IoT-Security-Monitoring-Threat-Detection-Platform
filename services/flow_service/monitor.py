import os
import sys
import time
import subprocess
from collections import deque
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box

from services.flow_service.configs.config import (
    CONN_LOG_PATH,
    ZEEK_BINARY,
    QUEUE_MAXLEN
)
from services.flow_service.state import QUEUE_1, ML_QUEUE

console = Console()


# =========================================================
# FORMAT HELPERS
# =========================================================
def fmt_ago(ts):
    if not ts:
        return "never"
    s = int(time.time() - ts)
    if s < 2: return "just now"
    if s < 60: return f"{s}s ago"
    if s < 3600: return f"{s//60}m ago"
    return f"{s//3600}h ago"


def fmt_uptime(start):
    s = int(time.time() - start)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# =========================================================
# PIPELINE MONITOR (IMPROVED)
# =========================================================
class PipelineMonitor:

    def __init__(self):
        self.start_time = time.time()

        # history buffers (SMOOTHING ENGINE)
        self.q1_history = deque(maxlen=10)
        self.ml_history = deque(maxlen=10)
        self.pps_history = deque(maxlen=10)

        self.last_q1 = 0
        self.last_ml = 0
        self.last_time = time.time()

        self.total_packets = 0
        self.last_packet_time = None

        self.threads = {}

        self.zeek_ok, self.zeek_ver = self.check_zeek()

    def check_zeek(self):
        try:
            r = subprocess.run(
                [ZEEK_BINARY, "--version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if r.returncode == 0:
                return True, r.stdout.split("\n")[0]
        except:
            pass
        return False, "unknown"

    # -----------------------------------------------------
    # CORE UPDATE (SMOOTHED METRICS)
    # -----------------------------------------------------
    def update(self):

        now = time.time()
        dt = max(now - self.last_time, 0.001)

        cur_q1 = len(QUEUE_1)
        cur_ml = len(ML_QUEUE)

        # packet flow delta
        q1_delta = max(cur_q1 - self.last_q1, 0)
        ml_delta = max(cur_ml - self.last_ml, 0)

        pps = q1_delta / dt
        ml_rate = ml_delta / dt

        # update totals
        if q1_delta > 0:
            self.total_packets += q1_delta
            self.last_packet_time = now

        # store history (SMOOTHING)
        self.q1_history.append(cur_q1)
        self.ml_history.append(cur_ml)
        self.pps_history.append(pps)

        # rolling averages
        avg_q1 = sum(self.q1_history) / len(self.q1_history)
        avg_ml = sum(self.ml_history) / len(self.ml_history)
        avg_pps = sum(self.pps_history) / len(self.pps_history)

        # update baseline
        self.last_q1 = cur_q1
        self.last_ml = cur_ml
        self.last_time = now

        return {
            "queue_1": cur_q1,
            "ml_queue": cur_ml,
            "avg_q1": round(avg_q1, 2),
            "avg_ml": round(avg_ml, 2),
            "pps": round(pps, 2),
            "avg_pps": round(avg_pps, 2),
            "ml_rate": round(ml_rate, 2),
            "total_packets": self.total_packets,
            "uptime": fmt_uptime(self.start_time),
            "last_packet_time": self.last_packet_time,
            "thread_status": self.threads
        }


# =========================================================
# DASHBOARD UI (IMPROVED IDS LOOK)
# =========================================================
def build_dashboard(monitor, stats):

    ts = datetime.now().strftime("%H:%M:%S")

    # -------------------------
    # THREAD PANEL
    # -------------------------
    t = Table(box=box.SIMPLE)
    t.add_column("THREAD")
    t.add_column("STATUS")

    for name in ["T1-packet_listener", "T2-zeek_feeder", "T3-zeek_parser", "T4-ml_worker"]:
        alive = monitor.threads.get(name, None)
        status = "RUNNING" if alive and alive.is_alive() else "UNKNOWN"
        t.add_row(name, status)

    thread_panel = Panel(t, title="SYSTEM THREADS")

    # -------------------------
    # QUEUE PANEL (SMOOTHED)
    # -------------------------
    q = Table(box=box.SIMPLE)
    q.add_column("QUEUE")
    q.add_column("CURRENT")
    q.add_column("AVG")

    q.add_row(
        "QUEUE_1",
        str(stats["queue_1"]),
        str(stats["avg_q1"])
    )

    q.add_row(
        "ML_QUEUE",
        str(stats["ml_queue"]),
        str(stats["avg_ml"])
    )

    queue_panel = Panel(q, title="DATA FLOW")

    # -------------------------
    # TRAFFIC PANEL
    # -------------------------
    traffic = Panel(
        f"Packets Total: {stats['total_packets']}\n"
        f"Instant Rate: {stats['pps']}\n"
        f"Avg Rate: {stats['avg_pps']}\n"
        f"ML Rate: {stats['ml_rate']}\n"
        f"Last Packet: {fmt_ago(stats['last_packet_time'])}",
        title="TRAFFIC ENGINE"
    )

    # -------------------------
    # ALERT PANEL (BASIC INTELLIGENCE)
    # -------------------------
    alert = "🟢 NORMAL"

    if stats["queue_1"] > QUEUE_MAXLEN * 0.7:
        alert = "🟡 HIGH TRAFFIC"
    if stats["ml_queue"] > 50:
        alert = "🔴 ML BACKLOG"

    alert_panel = Panel(f"[bold]{alert}[/bold]", title="ALERT STATUS")

    # -------------------------
    # ROOT LAYOUT
    # -------------------------
    layout = Layout()

    layout.split_column(
        Layout(Panel(f"IoT IDS PIPELINE | {ts}"), size=3),
        Layout(name="middle"),
        Layout(alert_panel, size=3)
    )

    layout["middle"].split_row(
        thread_panel,
        queue_panel,
        traffic
    )

    return layout


# =========================================================
# LIVE DASHBOARD LOOP
# =========================================================
def start_dashboard(monitor):

    with Live(console=console, refresh_per_second=1, screen=True) as live:

        while True:
            stats = monitor.update()
            live.update(build_dashboard(monitor, stats))
            time.sleep(1)
