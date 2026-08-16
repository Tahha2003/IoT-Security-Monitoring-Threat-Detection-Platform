-- SIEM Database Schema — Real IoT Setup
-- Devices: IP Camera, 2x BYOD Android, Pi Gateway, Backend
-- Run: psql -U postgres -c "CREATE DATABASE fyp_security;" then psql -U postgres -d fyp_security -f schema.sql

CREATE TABLE IF NOT EXISTS alerts (
    id            SERIAL PRIMARY KEY,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src_ip        VARCHAR(45) NOT NULL,
    dst_ip        VARCHAR(45) NOT NULL,
    dst_port      INTEGER DEFAULT 0,
    protocol      VARCHAR(20) DEFAULT '-',
    risk_score    FLOAT DEFAULT 0.0,
    severity      VARCHAR(20) DEFAULT 'LOW',
    attack_type   VARCHAR(50) DEFAULT 'UNKNOWN',
    packet_count  INTEGER DEFAULT 0,
    byte_count    BIGINT DEFAULT 0,
    verdict       VARCHAR(5) DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity  ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_src_ip    ON alerts(src_ip);
