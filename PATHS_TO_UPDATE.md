# Paths & Config to Update on Your Backend PC

## 1. Network IPs
Update these in the files listed:

| What | Default | File |
|------|---------|------|
| Backend IP | 192.168.1.20 | `dashboard/.env` (copy from .env.example) |
| Pi IP | 192.168.1.10 | `services/flow_service/configs/config.py` |
| Listen host | 0.0.0.0 | `services/flow_service/configs/config.py` → HOST |
| Listen port | 9000 | `services/flow_service/configs/config.py` → PORT |

## 2. Network Interface
| What | Default | File |
|------|---------|------|
| Zeek/tcpdump interface | eth0 | `infrastructure/scripts/start_pipeline.sh` → ZEEK_INTERFACE |
| | | Set env: `export ZEEK_INTERFACE=ens3` before running |

## 3. Zeek Binary Path
| What | Default | File |
|------|---------|------|
| Zeek binary | /opt/zeek/bin/zeek | `services/flow_service/configs/config.py` → ZEEK_BINARY |
| | | Also in `infrastructure/scripts/start_pipeline.sh` |

## 4. Suricata
| What | Default | File |
|------|---------|------|
| Suricata binary | /usr/bin/suricata | `services/dpi-service/parser/dpi_engine.py` → SURICATA_BIN |
| Suricata config | /etc/suricata/suricata.yaml | `services/dpi-service/parser/dpi_engine.py` → SURICATA_CONF |

## 5. PostgreSQL
Set these environment variables on your backend before starting:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=fyp_security
export DB_USER=postgres
export DB_PASS=your_password_here
```
Or edit directly in:
- `services/siem-service/writer/batch_writer.py` → DB_CONFIG
- `services/api-service/app/main.py` → DB_CONFIG

## 6. Model Paths
Models are loaded relative to project root — no change needed IF you unzip to same folder.
Verify: `ml/training/models/rf_model.pkl`, `iso_model.pkl`, `preprocessor.pkl` exist.

## 7. Dataset Paths
| What | Default | File |
|------|---------|------|
| Training dataset | ml/datasets/balanced_dataset.csv | `ml/training/dataset_preparer.py` |
| FP dataset | ml/datasets/fp_dataset.csv | auto-created by start_pipeline.sh |

## 8. Dashboard
```bash
cd dashboard
cp .env.example .env
# Edit .env with your backend IP
npm install
npm start
```

## 9. First Run Checklist
```bash
# From project root:
sudo -u postgres psql -c "CREATE DATABASE fyp_security;"
sudo -u postgres psql -d fyp_security -f services/siem-service/db/schema.sql
bash infrastructure/scripts/start_pipeline.sh
```
