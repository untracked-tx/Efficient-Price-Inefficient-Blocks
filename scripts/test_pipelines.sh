#!/bin/bash
# Master script to test all visualization pipelines

PROJECT_ID=${1:-"your-project-id"}

echo "=== Bitcoin Blockspace Analysis - Visualization Pipeline Test ==="
echo "Project ID: $PROJECT_ID"
echo ""

# Create directories if they don't exist
mkdir -p data/raw
mkdir -p data/figs

echo "=== Testing Visualization #1: Large Transaction Timing ==="
echo "This pulls BigQuery data for large transactions (>100 BTC) and creates an hour×day heatmap"
echo "Expected outputs:"
echo "  - Raw data: data/raw/large_tx_timing.csv"
echo "  - Visualization: data/figs/large_tx_heatmap.html"
echo ""

# Run large transaction pipeline
bash scripts/run_large_tx_pipeline.sh "$PROJECT_ID" 3 100

echo ""
echo "=== Testing Visualization #2: Mempool Congestion Heatmap ==="
echo "This uses Blockchain.com API to get mempool data and creates an hour×day heatmap"
echo "Expected outputs:"
echo "  - Raw data: data/raw/mempool_data.csv"
echo "  - Visualization: data/figs/mempool_heatmap.html"
echo ""

# Run mempool heatmap
python scripts/mempool_heatmap.py \
    --source blockchain \
    --out data/figs/mempool_heatmap.html \
    --save-raw data/raw/mempool_data.csv

echo ""
echo "=== Pipeline Test Summary ==="
echo "✓ Large Transaction Timing: data/figs/large_tx_heatmap.html"
echo "✓ Mempool Congestion: data/figs/mempool_heatmap.html"
echo ""
echo "Raw data files created:"
echo "  - data/raw/large_tx_timing.csv"
echo "  - data/raw/mempool_data.csv"
echo ""
echo "All visualizations saved to: data/figs/"
