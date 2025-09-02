#!/usr/bin/env bash
# Export large transaction timing (>=100 BTC, last 3 years) to CSV and build the heatmap
# Requires: bq CLI configured and authenticated

set -euo pipefail

ROOT_DIR=$(pwd)
SQL_FILE="$ROOT_DIR/sql/large_tx_timing.sql"
OUT_CSV="$ROOT_DIR/data/raw/large_tx_timing.csv"
OUT_HTML="$ROOT_DIR/data/figs/large_tx_heatmap.html"

mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/data/figs"

# Run with bq and save to CSV
bq query --use_legacy_sql=false --format=csv < "$SQL_FILE" > "$OUT_CSV"

# Build the interactive heatmap
python "$ROOT_DIR/scripts/large_tx_heatmap_from_csv.py" --csv "$OUT_CSV" --out "$OUT_HTML" --tz America/Denver --min_btc 100 --years 3

echo "Done. Created $OUT_HTML"
