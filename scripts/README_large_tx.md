# Large Transaction Timing — Hour×Day

This script reads a CSV exported from BigQuery with at least a `block_timestamp` column and produces an interactive heatmap HTML.

Steps:
1. In BigQuery, run the query in `sql/large_tx_timing.sql`.
2. Export results as CSV to `data/raw/large_tx_timing.csv`.
3. Generate the figure:

python scripts/large_tx_heatmap_from_csv.py --csv data/raw/large_tx_timing.csv --out data/figs/large_tx_heatmap.html --min_btc 100 --years 3 --tz America/Denver
