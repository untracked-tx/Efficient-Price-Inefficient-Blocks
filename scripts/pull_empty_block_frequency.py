#!/usr/bin/env python3
"""
Pull empty block frequency data from BigQuery.

Usage:
  python scripts/pull_empty_block_frequency.py --project YOUR_PROJECT --years 3
"""
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pull empty block frequency data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=3, help="Years of data to pull")
    parser.add_argument("--out", default="data/raw/empty_block_frequency.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query
    sql_path = Path("sql/empty_block_frequency.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
    except ImportError:
        print("Error: Please install pandas-gbq")
        print("pip install pandas-gbq")
        return 1

    print(f"Running empty block frequency query...")
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
    total_blocks = df["total_blocks"].sum()
    total_empty = df["empty_blocks"].sum()
    empty_percentage = (total_empty / total_blocks) * 100 if total_blocks > 0 else 0
    
    print(f"\nSummary:")
    print(f"  Total blocks: {total_blocks:,}")
    print(f"  Empty blocks: {total_empty:,}")
    print(f"  Empty block percentage: {empty_percentage:.2f}%")
    print(f"  Date range: last {args.years} years")

    return 0

if __name__ == "__main__":
    exit(main())
