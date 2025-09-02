#!/usr/bin/env bash
"""
Complete pipeline for Large Transaction Timing visualization.
Pulls data from BigQuery and creates heatmap.

Usage:
  bash scripts/run_large_tx_pipeline.sh YOUR_PROJECT_ID
"""

set -e  # Exit on any error

if [ -z "$1" ]; then
    echo "Usage: $0 PROJECT_ID [years] [min_btc]"
    echo "Example: $0 my-gcp-project 3 100"
    exit 1
fi

PROJECT_ID=$1
YEARS=${2:-3}
MIN_BTC=${3:-100}

echo "=== Large Transaction Timing Pipeline ==="
echo "Project: $PROJECT_ID"
echo "Years: $YEARS"
echo "Min BTC: $MIN_BTC"
echo ""

# Step 1: Pull data from BigQuery
echo "Step 1: Pulling data from BigQuery..."
python scripts/pull_large_tx_timing.py \
    --project "$PROJECT_ID" \
    --years "$YEARS" \
    --min_btc "$MIN_BTC" \
    --out "data/raw/large_tx_timing.csv"

# Step 2: Create heatmap visualization
echo ""
echo "Step 2: Creating heatmap visualization..."
python scripts/large_tx_heatmap.py \
    --csv "data/raw/large_tx_timing.csv" \
    --out "data/figs/large_tx_heatmap.png" \
    --metric "tx_count" \
    --min_btc "$MIN_BTC" \
    --years "$YEARS"

echo ""
echo "=== Pipeline Complete! ==="
echo "Data: data/raw/large_tx_timing.csv"
echo "Visualization: data/figs/large_tx_heatmap.png"
