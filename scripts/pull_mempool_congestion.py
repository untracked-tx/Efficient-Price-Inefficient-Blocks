#!/usr/bin/env python3
"""
Pull mempool congestion proxy data (fee rates) from BigQuery and save to CSV.

Usage:
  python scripts/pull_mempool_congestion.py --project YOUR_PROJECT --years 1
"""
import argparse
from pathlib import Path
import pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="GCP project id")
    p.add_argument("--location", default="US")
    p.add_argument("--years", type=int, default=1, help="Years of data to pull")
    p.add_argument("--out", default="data/raw/mempool_congestion.csv", help="Output CSV path")
    args = p.parse_args()

    # Read the SQL template
    sql_template = Path("sql/mempool_congestion.sql").read_text()
    
    # Replace the hardcoded values with parameters
    sql = sql_template.replace(
        "INTERVAL 1 YEAR", f"INTERVAL {args.years} YEAR"
    )

    # Lazy import to avoid forcing install if unused
    import pandas_gbq  # type: ignore

    print(f"Pulling mempool congestion data (fee rates, last {args.years} years)...")
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
    print(f"Median fee rate: {df['median_fee_rate'].mean():.1f} sat/vB")
    print(f"95th percentile fee rate: {df['p95_fee_rate'].mean():.1f} sat/vB")

if __name__ == "__main__":
    main()
