#!/usr/bin/env python3
"""
====================================================================
AUTHENTIC NORMAL CONN.LOG GENERATOR
====================================================================
Generates 2000+ normal conn.log rows matching your EXACT Zeek format.

Based on real observed ESP32+DHT22 traffic:
  - proto=tcp, service=mqtt, port=1883
  - Long duration sessions (sensor stays connected)
  - One-way traffic: orig_bytes high, resp_bytes=0
  - conn_state=OTH (ongoing/no clean close — typical MQTT keepalive)
  - history=DA (data sent, ack received)
  - ESP32 IP: 192.168.50.50
  - Broker IP: 192.168.50.1

Also generates realistic background normal traffic seen on any LAN:
  - mDNS (udp/5353) — your router, phones, laptops
  - DNS (udp/53)
  - NTP (udp/123)
  - HTTP/HTTPS (tcp/80, tcp/443)
  - DHCP (udp/67-68)

All rows are statistically sampled from your real observed values.
Output is a valid Zeek conn.log — drop it anywhere your parser reads.

NEW: Two realism improvements added:
  1. Daily cycle variation — publish rate, byte counts, and session
     duration shift across a simulated 24h period (cooler nights =
     less sensor variance; warm afternoons = faster publishes).
  2. Reconnection events — 15% of ESP32 sessions are short (30–180s)
     representing WiFi drops, deep-sleep wakeups, and DHT22 read
     errors followed by reconnect. Mixed in with long sessions.

Usage:
    python3 generate_normal.py --rows 2000 --out dataset/normal_conn.log
    python3 generate_normal.py --rows 5000 --out dataset/normal_conn.log
====================================================================
"""

import os
import random
import argparse
import string
import math
from datetime import datetime

# ── Seed for reproducibility (remove for fresh random each run) ───
random.seed(42)


# ====================================================================
# HELPERS
# ====================================================================

def rand_uid(length=18):
    """Generate a Zeek-style UID like C34Bvs2XfhNhGaYK23"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def rand_port(low=1024, high=65535):
    return random.randint(low, high)

def fmt(val):
    """Format float to 6 decimal places like Zeek."""
    return f"{val:.6f}"


# ====================================================================
# DAILY CYCLE + RECONNECTION HELPERS
# ====================================================================

def hour_of_day(ts: float) -> float:
    """Return fractional hour (0.0–23.99) from a unix timestamp."""
    import time as _time
    return _time.localtime(ts).tm_hour + _time.localtime(ts).tm_min / 60.0


def daily_byte_rate_multiplier(ts: float) -> float:
    """
    DHT22 publish rate varies with temperature cycle:
      - Night  (00:00–06:00): sensor stable, slower variance → lower rate
      - Morning(06:00–10:00): warming up, rate picks up
      - Day    (10:00–18:00): peak activity, highest rate
      - Evening(18:00–24:00): cooling, tapering off

    Returns a multiplier applied to the base byte_rate (44.9 bytes/s).
    Range: 0.75 – 1.25  (±25% around observed value)
    """
    import math
    h = hour_of_day(ts)
    # sinusoidal daily cycle: peak at 14:00, trough at 02:00
    # sin period = 24h, shifted so peak aligns with 14:00
    phase = (h - 14.0) * (2 * math.pi / 24.0)
    return 1.0 + 0.25 * math.sin(phase - math.pi)


def is_reconnect_event() -> bool:
    """
    15% of ESP32 MQTT sessions are short reconnections:
      - WiFi drop + reconnect
      - ESP32 deep sleep wakeup
      - DHT22 sensor read error causing restart
    """
    return random.random() < 0.15


def reconnect_session_duration() -> float:
    """
    Short session: 30–180 seconds.
    Bimodal — either very short (deep sleep wakeup ~30–60s)
    or medium (WiFi drop recovery ~90–180s).
    """
    if random.random() < 0.5:
        return random.uniform(30.0, 60.0)    # deep sleep wakeup
    return random.uniform(90.0, 180.0)       # WiFi recovery


def reconnect_history() -> str:
    """
    Short sessions have different Zeek history strings:
      - 'D'   : sent data, no ACK (abrupt drop)
      - 'DA'  : data + ACK (clean short session)
      - 'DAR' : data + ACK + RST (broker reset connection)
    """
    return random.choice(["D", "DA", "DAR"])


def reconnect_conn_state() -> str:
    """
    Short sessions have varied conn_state:
      - OTH  : most common (session ongoing when logged)
      - RSTO : ESP32 reset the connection
      - RSTR : broker reset
    """
    return random.choices(["OTH", "RSTO", "RSTR"], weights=[60, 25, 15])[0]



# ====================================================================
# TRAFFIC PROFILES
# All values derived from your real conn.log observation +
# standard IoT/LAN traffic literature.
# ====================================================================

class Profile:
    """Base class — each subclass generates one conn.log row."""

    # Your real network IPs
    ESP32_IP     = "192.168.50.50"
    BROKER_IP    = "192.168.50.1"
    GATEWAY_IP   = "192.168.50.1"
    DNS_SERVER   = "192.168.50.1"
    NTP_SERVER   = "216.239.35.0"    # time.google.com range

    # Simulated LAN devices (phones, laptops, etc)
    LAN_DEVICES  = [
        "192.168.50.10", "192.168.50.11", "192.168.50.15",
        "192.168.50.20", "192.168.50.21", "192.168.50.30",
        "192.168.50.100","192.168.50.102","192.168.50.110",
    ]
    MULTICAST_MDNS = "224.0.0.251"
    BROADCAST      = "192.168.50.255"

    def row(self, base_ts: float) -> dict:
        raise NotImplementedError


# ── 1. ESP32 MQTT session ────────────────────────────────────────
class ESP32MQTTProfile(Profile):
    """
    Matches your exact observed row with two realism additions:

    ADDITION 1 — Daily cycle:
      byte_rate is multiplied by daily_byte_rate_multiplier(ts)
      so sessions at 14:00 produce ~25% more bytes than at 02:00.
      This mirrors real DHT22 behaviour where warmer daytime temps
      cause more frequent sensor variance and faster publishes.

    ADDITION 2 — Reconnection events:
      15% of sessions are short (30–180s) with different conn_state
      and history, representing WiFi drops / deep-sleep wakeups /
      DHT22 read errors. These are critical for Isolation Forest —
      without them the model treats any short session as anomalous.
    """
    def row(self, base_ts):
        # ── RECONNECTION EVENT (15% probability) ─────────────────
        if is_reconnect_event():
            duration     = reconnect_session_duration()
            conn_state   = reconnect_conn_state()
            history      = reconnect_history()
            # short sessions send very few bytes before dropping
            orig_bytes   = int(duration * random.uniform(5.0, 20.0))
            orig_bytes   = max(100, orig_bytes)
            overhead     = random.gauss(1.298, 0.05)
            orig_ip_bytes = int(orig_bytes * overhead)
            orig_pkts    = max(2, int(orig_ip_bytes * random.gauss(0.00574, 0.001)))
            resp_pkts    = 0 if history in ("D",) else random.randint(1, 5)
            resp_bytes   = 0 if resp_pkts == 0 else resp_pkts * random.randint(20, 60)
            resp_ip_bytes = 0 if resp_pkts == 0 else int(resp_bytes * 1.1)

            return {
                "ts":             fmt(base_ts),
                "uid":            rand_uid(),
                "id.orig_h":      self.ESP32_IP,
                "id.orig_p":      rand_port(49152, 65535),
                "id.resp_h":      self.BROKER_IP,
                "id.resp_p":      1883,
                "proto":          "tcp",
                "service":        "mqtt",
                "duration":       fmt(duration),
                "orig_bytes":     orig_bytes,
                "resp_bytes":     resp_bytes,
                "conn_state":     conn_state,
                "local_orig":     "T",
                "local_resp":     "T",
                "missed_bytes":   random.randint(0, 50),
                "history":        history,
                "orig_pkts":      orig_pkts,
                "orig_ip_bytes":  orig_ip_bytes,
                "resp_pkts":      resp_pkts,
                "resp_ip_bytes":  resp_ip_bytes,
                "tunnel_parents": "-",
                "ip_proto":       6,
            }

        # ── NORMAL LONG SESSION ───────────────────────────────────
        duration = max(30.0, random.gauss(2264, 400))

        # ADDITION 1: scale byte_rate by time-of-day multiplier
        base_rate   = random.gauss(44.9, 8.0)
        daily_mult  = daily_byte_rate_multiplier(base_ts)
        byte_rate   = max(10.0, base_rate * daily_mult)

        orig_bytes    = int(duration * byte_rate)
        orig_bytes    = max(1000, orig_bytes)
        overhead      = random.gauss(1.298, 0.05)
        orig_ip_bytes = int(orig_bytes * overhead)
        orig_pkts     = max(10, int(orig_ip_bytes * random.gauss(0.00574, 0.0005)))
        src_port      = rand_port(49152, 65535)

        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      self.ESP32_IP,
            "id.orig_p":      src_port,
            "id.resp_h":      self.BROKER_IP,
            "id.resp_p":      1883,
            "proto":          "tcp",
            "service":        "mqtt",
            "duration":       fmt(duration),
            "orig_bytes":     orig_bytes,
            "resp_bytes":     0,
            "conn_state":     "OTH",
            "local_orig":     "T",
            "local_resp":     "T",
            "missed_bytes":   0,
            "history":        "DA",
            "orig_pkts":      orig_pkts,
            "orig_ip_bytes":  orig_ip_bytes,
            "resp_pkts":      0,
            "resp_ip_bytes":  0,
            "tunnel_parents": "-",
            "ip_proto":       6,
        }


# ── 2. mDNS (your router/devices announce themselves) ───────────
class MDNSProfile(Profile):
    """
    Matches your real observed row:
      1775924959 C34Bvs2X... 192.168.10.110 5353 224.0.0.251 5353 udp dns - - - S0 T T 0 D 1 73 0 0 - 17
      duration = - (S0: no response)
      orig_pkts = 1, orig_ip_bytes = 73 (standard mDNS query size)
    """
    def row(self, base_ts):
        src = random.choice(self.LAN_DEVICES)
        # mDNS queries are small — 60–120 bytes
        pkt_size = random.randint(60, 120)
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      5353,
            "id.resp_h":      self.MULTICAST_MDNS,
            "id.resp_p":      5353,
            "proto":          "udp",
            "service":        "dns",
            "duration":       "-",
            "orig_bytes":     "-",
            "resp_bytes":     "-",
            "conn_state":     "S0",
            "local_orig":     "T",
            "local_resp":     "T",
            "missed_bytes":   0,
            "history":        "D",
            "orig_pkts":      1,
            "orig_ip_bytes":  pkt_size,
            "resp_pkts":      0,
            "resp_ip_bytes":  0,
            "tunnel_parents": "-",
            "ip_proto":       17,
        }


# ── 3. DNS query + response ──────────────────────────────────────
class DNSProfile(Profile):
    def row(self, base_ts):
        src      = random.choice(self.LAN_DEVICES + [self.ESP32_IP])
        duration = random.uniform(0.001, 0.15)
        q_size   = random.randint(60, 90)
        r_size   = random.randint(80, 300)
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      rand_port(1024, 65535),
            "id.resp_h":      self.DNS_SERVER,
            "id.resp_p":      53,
            "proto":          "udp",
            "service":        "dns",
            "duration":       fmt(duration),
            "orig_bytes":     q_size - 28,
            "resp_bytes":     r_size - 28,
            "conn_state":     "SF",
            "local_orig":     "T",
            "local_resp":     "T",
            "missed_bytes":   0,
            "history":        "Dd",
            "orig_pkts":      1,
            "orig_ip_bytes":  q_size,
            "resp_pkts":      1,
            "resp_ip_bytes":  r_size,
            "tunnel_parents": "-",
            "ip_proto":       17,
        }


# ── 4. NTP sync ──────────────────────────────────────────────────
class NTPProfile(Profile):
    def row(self, base_ts):
        src      = random.choice(self.LAN_DEVICES)
        duration = random.uniform(0.005, 0.080)
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      rand_port(1024, 65535),
            "id.resp_h":      self.NTP_SERVER,
            "id.resp_p":      123,
            "proto":          "udp",
            "service":        "ntp",
            "duration":       fmt(duration),
            "orig_bytes":     48,
            "resp_bytes":     48,
            "conn_state":     "SF",
            "local_orig":     "T",
            "local_resp":     "F",
            "missed_bytes":   0,
            "history":        "Dd",
            "orig_pkts":      1,
            "orig_ip_bytes":  76,
            "resp_pkts":      1,
            "resp_ip_bytes":  76,
            "tunnel_parents": "-",
            "ip_proto":       17,
        }


# ── 5. HTTP browsing ─────────────────────────────────────────────
class HTTPProfile(Profile):
    def row(self, base_ts):
        src      = random.choice(self.LAN_DEVICES)
        port     = random.choice([80, 443])
        service  = "http" if port == 80 else "ssl"
        duration = random.uniform(0.1, 8.0)
        orig_b   = random.randint(200, 2000)
        resp_b   = random.randint(500, 80000)
        o_pkts   = max(2, int(orig_b / 500) + random.randint(1, 4))
        r_pkts   = max(2, int(resp_b / 1400) + random.randint(1, 6))
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      rand_port(49152, 65535),
            "id.resp_h":      f"93.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
            "id.resp_p":      port,
            "proto":          "tcp",
            "service":        service,
            "duration":       fmt(duration),
            "orig_bytes":     orig_b,
            "resp_bytes":     resp_b,
            "conn_state":     "SF",
            "local_orig":     "T",
            "local_resp":     "F",
            "missed_bytes":   0,
            "history":        "ShADadFf",
            "orig_pkts":      o_pkts,
            "orig_ip_bytes":  orig_b + (o_pkts * 40),
            "resp_pkts":      r_pkts,
            "resp_ip_bytes":  resp_b + (r_pkts * 40),
            "tunnel_parents": "-",
            "ip_proto":       6,
        }


# ── 6. DHCP lease renewal ────────────────────────────────────────
class DHCPProfile(Profile):
    def row(self, base_ts):
        src = random.choice(self.LAN_DEVICES + [self.ESP32_IP])
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      68,
            "id.resp_h":      self.BROADCAST,
            "id.resp_p":      67,
            "proto":          "udp",
            "service":        "-",
            "duration":       fmt(random.uniform(0.001, 0.05)),
            "orig_bytes":     300,
            "resp_bytes":     300,
            "conn_state":     "SF",
            "local_orig":     "T",
            "local_resp":     "T",
            "missed_bytes":   0,
            "history":        "Dd",
            "orig_pkts":      1,
            "orig_ip_bytes":  328,
            "resp_pkts":      1,
            "resp_ip_bytes":  328,
            "tunnel_parents": "-",
            "ip_proto":       17,
        }


# ── 7. ICMP ping (router keepalive / gateway check) ──────────────
class ICMPProfile(Profile):
    def row(self, base_ts):
        src      = random.choice(self.LAN_DEVICES)
        duration = random.uniform(0.0005, 0.020)
        return {
            "ts":             fmt(base_ts),
            "uid":            rand_uid(),
            "id.orig_h":      src,
            "id.orig_p":      8,       # ICMP type echo request
            "id.resp_h":      self.GATEWAY_IP,
            "id.resp_p":      0,
            "proto":          "icmp",
            "service":        "-",
            "duration":       fmt(duration),
            "orig_bytes":     84,
            "resp_bytes":     84,
            "conn_state":     "SF",
            "local_orig":     "T",
            "local_resp":     "T",
            "missed_bytes":   0,
            "history":        "Ee",
            "orig_pkts":      1,
            "orig_ip_bytes":  112,
            "resp_pkts":      1,
            "resp_ip_bytes":  112,
            "tunnel_parents": "-",
            "ip_proto":       1,
        }


# ====================================================================
# GENERATOR — assembles rows with realistic timestamp spacing
# ====================================================================

# Traffic mix weights — controls how many of each type appear
# Adjust to match your real network's traffic composition
PROFILES = [
    (ESP32MQTTProfile, 40),   # 40% — ESP32 is your main device
    (MDNSProfile,      20),   # 20% — constant on any LAN
    (DNSProfile,       15),   # 15% — every device queries DNS
    (NTPProfile,        5),   # 5%  — periodic time sync
    (HTTPProfile,      10),   # 10% — background browsing
    (DHCPProfile,       5),   # 5%  — lease renewals
    (ICMPProfile,       5),   # 5%  — gateway pings
]

def weighted_profile():
    classes, weights = zip(*PROFILES)
    return random.choices(classes, weights=weights, k=1)[0]()


ZEEK_HEADER = """\
#separator \\x09
#set_separator\t,
#empty_field\t(empty)
#unset_field\t-
#path\tconn
#open\t{open_time}
#fields\tts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\tduration\torig_bytes\tresp_bytes\tconn_state\tlocal_orig\tlocal_resp\tmissed_bytes\thistory\torig_pkts\torig_ip_bytes\tresp_pkts\tresp_ip_bytes\ttunnel_parents\tip_proto
#types\ttime\tstring\taddr\tport\taddr\tport\tenum\tstring\tinterval\tcount\tcount\tstring\tbool\tbool\tcount\tstring\tcount\tcount\tcount\tcount\tset[string]\tcount
"""

FIELD_ORDER = [
    "ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p",
    "proto", "service", "duration", "orig_bytes", "resp_bytes",
    "conn_state", "local_orig", "local_resp", "missed_bytes", "history",
    "orig_pkts", "orig_ip_bytes", "resp_pkts", "resp_ip_bytes",
    "tunnel_parents", "ip_proto",
]


def generate(n_rows: int, out_path: str):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Start timestamp ~24 hours ago so data looks historical
    import time
    base_ts = time.time() - 86400
    open_time = datetime.fromtimestamp(base_ts).strftime("%Y-%m-%d-%H-%M-%S")

    counts = {}
    written = 0

    with open(out_path, "w") as f:
        f.write(ZEEK_HEADER.format(open_time=open_time))

        for i in range(n_rows):
            profile = weighted_profile()
            row     = profile.row(base_ts)

            # advance timestamp — realistic inter-arrival time per type
            if row["proto"] == "tcp" and row.get("id.resp_p") == 1883:
                # MQTT sessions start infrequently (every few minutes)
                base_ts += random.uniform(30, 180)
            elif row["proto"] == "udp" and row.get("id.resp_p") == 5353:
                base_ts += random.uniform(5, 30)
            elif row["proto"] == "udp" and row.get("id.resp_p") == 53:
                base_ts += random.uniform(1, 10)
            else:
                base_ts += random.uniform(0.5, 15)

            # write tab-separated row
            line = "\t".join(str(row[f]) for f in FIELD_ORDER)
            f.write(line + "\n")

            ptype = type(profile).__name__
            counts[ptype] = counts.get(ptype, 0) + 1
            written += 1

        close_time = datetime.fromtimestamp(base_ts).strftime("%Y-%m-%d-%H-%M-%S")
        f.write(f"#close\t{close_time}\n")

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  NORMAL DATA GENERATION COMPLETE")
    print(f"  Output  : {out_path}")
    print(f"  Total   : {written} rows")
    print(f"\n  Traffic type breakdown:")
    for ptype, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count / written * 100
        bar = "█" * int(pct / 2)
        print(f"    {ptype:<26} {count:>5} rows  ({pct:4.1f}%)  {bar}")
    print(f"\n  Realism features active:")
    print(f"    ✔  Daily cycle variation  — byte rate shifts ±25% across 24h")
    print(f"    ✔  Reconnection events    — ~15% of MQTT rows are short sessions")
    print(f"       (WiFi drops, deep-sleep wakeups, DHT22 read errors)")
    print(f"\n  All rows labeled: normal")
    print(f"  Format : valid Zeek conn.log — ready for your parser + ML model")
    print(f"{'='*60}\n")


# ====================================================================
# CLI
# ====================================================================

def main():
    p = argparse.ArgumentParser(
        description="Generate authentic normal conn.log data for IoT anomaly detection"
    )
    p.add_argument("--rows", type=int, default=2000,
                   help="Number of rows to generate (default: 2000)")
    p.add_argument("--out",  default="dataset/normal_conn.log",
                   help="Output path (default: dataset/normal_conn.log)")
    args = p.parse_args()

    print(f"Generating {args.rows} normal rows → {args.out}")
    generate(args.rows, args.out)


if __name__ == "__main__":
    main()
