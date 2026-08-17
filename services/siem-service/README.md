# SIEM Service — Security Information and Event Management

The SIEM service is responsible for persisting all detected threat alerts to the PostgreSQL database. It uses a non-blocking batch write approach — alerts are queued in memory by the pipeline and flushed to the database every 2 seconds. This decouples the fast ML inference path from the slower database write latency.

---

## Role in the Pipeline

```
T5 DPI Worker (main_pipeline.py)
        │
        └──→ queue_alert(alert_dict)         ← non-blocking, O(1)
                    │
                    ▼
        In-memory deque (maxlen = 10,000)
                    │
                    ▼ (every 2 seconds)
        [T6] batch_loop()
                    │
            IoT device filter +
            alert-level filter
                    │
                    ▼
        PostgreSQL — alerts table
                    │
        On DB error: batch re-queued (no data loss)
```

---

## Structure

```
siem-service/
├── db/
│   └── schema.sql          # Hardened PostgreSQL schema — alerts table
├── writer/
│   └── batch_writer.py     # In-memory queue + batch flush to PostgreSQL
└── __init__.py
```

---

## Database Schema (`db/schema.sql`)

The `alerts` table was hardened in Session 1 — all columns have `NOT NULL` + `DEFAULT` constraints to prevent partial inserts from crashing the batch writer:

```sql
CREATE TABLE IF NOT EXISTS alerts (
    id           SERIAL PRIMARY KEY,
    timestamp    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    src_ip       INET         NOT NULL DEFAULT '0.0.0.0',
    dst_ip       INET         NOT NULL DEFAULT '0.0.0.0',
    dst_port     INTEGER      NOT NULL DEFAULT 0,
    protocol     VARCHAR(10)  NOT NULL DEFAULT 'unknown',
    risk_score   FLOAT        NOT NULL DEFAULT 0.0,
    severity     VARCHAR(10)  NOT NULL DEFAULT 'LOW',
    attack_type  VARCHAR(64)  NOT NULL DEFAULT 'unknown',
    packet_count INTEGER      NOT NULL DEFAULT 0,
    byte_count   BIGINT       NOT NULL DEFAULT 0,
    verdict      VARCHAR(4)   DEFAULT NULL    -- set by analyst: 'TP' or 'FP'
);
```

The schema uses `IF NOT EXISTS` — it is safe to re-apply on every `start_pipeline.sh` run.

### Applying the Schema

```bash
PGPASSWORD=postgres psql -U postgres -d fyp_security \
    -f services/siem-service/db/schema.sql
```

### Creating the Database (first time)

```bash
sudo -u postgres psql -c "CREATE DATABASE fyp_security;"
```

---

## Batch Writer (`writer/batch_writer.py`)

### `queue_alert(d: dict)`
Called from T5 in the pipeline's hot path. Appends the alert dict to the in-memory `deque`. Non-blocking — returns immediately. Thread-safe via `deque`'s GIL-protected append.

### `batch_loop()`
Runs as T6 (background thread). Every 2 seconds:

1. Drains the entire in-memory queue into a batch list
2. Applies alert filtering (see below)
3. Bulk-inserts the batch via `executemany`
4. On DB failure: puts the batch back into the queue — **no alerts are silently lost**

### `fp_dataset.csv` Initialization

At startup, `start_pipeline.sh` (step 5) creates `ml/datasets/fp_dataset.csv` with the correct header row if it does not already exist:

```
duration,packet_count,byte_count,avg_pkt_size,flow_rate,dst_port,protocol,conn_state,dns_query_count,label
```

This prevents a `FileNotFoundError` in the API service when the first FP verdict is submitted before any retraining has occurred.

---

## Alert Filtering

The batch writer applies a final filter before persisting to the database:

| Traffic Type | Stored? |
|-------------|---------|
| ML-flagged (any severity) from any source | ✅ Always stored |
| Traffic from IoT devices (Camera, BYOD) | ✅ Always stored (for monitoring and baselining) |
| Normal traffic from non-IoT devices | ❌ Discarded — not written to DB |

IoT device IPs are loaded from `shared/config/system_config.yaml` via `config_loader.py` — not hardcoded in the batch writer.

---

## Alert Retention

The in-memory deque is capped at 10,000 items. Under normal conditions the batch loop drains it every 2 seconds, so backlog never approaches this limit. On sustained DB outages, the queue fills and the oldest un-flushed alerts are evicted.

---

## Analyst Verdict (FP/TP Feedback)

The `verdict` column is updated by the API service (`POST /api/review/{alert_id}`) when an analyst marks an alert:

- **TP** (True Positive): Updates `verdict = 'TP'` in the database. No further action.
- **FP** (False Positive): Updates `verdict = 'FP'` in the database **and** exports the flow's features to `ml/datasets/fp_dataset.csv`.

The FP export feeds the model retraining pipeline — run `python3 -m ml.training.model_training` after accumulating enough FP examples to improve model precision.

---

## Database Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fyp_security` | Database name |
| `DB_USER` | `postgres` | Username |
| `DB_PASS` | `postgres` | Password — always set via env var, never commit in code |

---

## Useful Queries

```sql
-- Total alerts by severity
SELECT severity, COUNT(*) FROM alerts
GROUP BY severity ORDER BY COUNT(*) DESC;

-- Recent alerts (last 5 minutes)
SELECT src_ip, severity, attack_type, risk_score, timestamp
FROM alerts
WHERE timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC;

-- Top attacker IPs
SELECT src_ip, COUNT(*) AS cnt, MAX(risk_score) AS max_risk
FROM alerts
GROUP BY src_ip ORDER BY cnt DESC LIMIT 10;

-- False positive rate
SELECT
    COUNT(*) FILTER (WHERE verdict = 'FP') AS fp_count,
    COUNT(*) FILTER (WHERE verdict = 'TP') AS tp_count,
    COUNT(*) FILTER (WHERE verdict IS NULL) AS unreviewed
FROM alerts;

-- Clear all alerts (fresh start)
TRUNCATE TABLE alerts RESTART IDENTITY;
```

---

## Logs

| Log File | Contents |
|----------|----------|
| `logs/siem/batch_writer.log` | Batch insert counts, DB errors, queue overflow warnings |
| `logs/siem/soar_engine.log` | SOAR trigger events (written by soar-service, kept here for centralized SIEM logging) |
