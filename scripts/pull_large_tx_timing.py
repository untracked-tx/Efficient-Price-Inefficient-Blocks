#!/usr/bin/env python3
"""
Pull large transaction timing data from BigQuery and save to CSV.

Usage:
  python scripts/pull_large_tx_timing.py --project YOUR_PROJECT --years 3 --min_btc 100
"""
import argparse
from pathlib import Path
import pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="GCP project id")
    p.add_argument("--location", default="US")
    p.add_argument("--years", type=int, default=3, help="Years of data to pull")
    p.add_argument("--min_btc", type=float, default=100, help="Minimum BTC threshold")
    p.add_argument("--out", default="data/raw/large_tx_timing.csv", help="Output CSV path")
    args = p.parse_args()

    # Read the SQL template
    sql_template = Path("sql/large_tx_timing.sql").read_text()
    
    # Replace the hardcoded values with parameters
    sql = sql_template.replace(
        "100 * 1e8", f"{args.min_btc} * 1e8"
    ).replace(
        "INTERVAL 3 YEAR", f"INTERVAL {args.years} YEAR"
    )

    # Lazy import to avoid forcing install if unused
    import pandas_gbq  # type: ignore

    print(f"Pulling large transaction timing data (>= {args.min_btc} BTC, last {args.years} years)...")
    df = pandas_gbq.read_gbq(
        sql,
        project_id=args.project,
        dialect="standard",
        location=args.location,
        progress_bar_type=None
    )
    
    # Ensure output directory exists
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {len(df):,} rows to {out_path} ...")
    df.to_csv(out_path, index=False)
    print("Done.")
    
    # Print some basic stats
    print(f"\nData summary:")
    print(f"Date range: {df.shape[0]} hour/day combinations")
    print(f"Total transactions: {df['tx_count'].sum():,}")
    print(f"Average BTC per transaction: {df['avg_btc_amount'].mean():.1f}")

if __name__ == "__main__":
    main()
