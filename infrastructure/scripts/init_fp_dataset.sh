#!/bin/bash
# Initialize fp_dataset.csv with correct headers (GAP 4 FIX)
# Called by start_pipeline.sh automatically — can also run standalone

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FP_PATH="$PROJECT_ROOT/ml/datasets/fp_dataset.csv"

if [ ! -f "$FP_PATH" ]; then
    echo "duration,packet_count,byte_count,avg_pkt_size,flow_rate,dst_port,protocol,conn_state,dns_query_count,label" \
        > "$FP_PATH"
    echo "[✔] fp_dataset.csv created at $FP_PATH"
else
    echo "[✔] fp_dataset.csv already exists"
fi
