#!/usr/bin/env python3
"""
Pull block time variance data from BigQuery.

Usage:
  python scripts/pull_block_time_variance.py --project YOUR_PROJECT --years 3
"""
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pull block time variance data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=3, help="Years of data to pull")
    parser.add_argument("--out", default="data/raw/block_time_variance.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query
    sql_path = Path("sql/block_time_variance.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
        from google.cloud import bigquery
    except ImportError:
        print("Error: Please install google-cloud-bigquery and pandas-gbq")
        print("pip install google-cloud-bigquery pandas-gbq")
        return 1

    print(f"Running block time variance query...")
    print(f"  Years: {args.years}")

    # Replace parameter in SQL
    sql_with_params = sql.replace("@years", str(args.years))

    # Run query
    df = pandas_gbq.read_gbq(
        sql_with_params,
        project_id=args.project,
        location=args.location,
        progress_bar_type=None
    )

    # Save to CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {len(df):,} rows to {out_path}")
    df.to_csv(out_path, index=False)
    print("Done!")

    # Show summary
    print(f"\nSummary:")
    print(f"  Total block intervals: {df['block_count'].sum():,}")
    print(f"  Overall average interval: {df['avg_interval_seconds'].mean():.1f} seconds")
    print(f"  Target interval: 600 seconds (10 minutes)")
    print(f"  Date range: last {args.years} years")

    return 0

if __name__ == "__main__":
    exit(main())
