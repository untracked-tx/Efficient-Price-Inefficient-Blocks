#!/usr/bin/env python3
"""
Pull UTXO age movement data from BigQuery.

Usage:
  python scripts/pull_utxo_age_movement.py --project YOUR_PROJECT --years 1
"""
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pull UTXO age movement data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=1, help="Years of data to pull (keep small for this query)")
    parser.add_argument("--out", default="data/raw/utxo_age_movement.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query
    sql_path = Path("sql/utxo_age_movement.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
    except ImportError:
        print("Error: Please install pandas-gbq")
        print("pip install pandas-gbq")
        return 1

    print(f"Running UTXO age movement query...")
    print(f"  Years: {args.years}")
    print(f"  WARNING: This query joins large tables and may be expensive!")

    # Replace parameter in SQL
    sql_with_params = sql.replace("@years", str(args.years))

    try:
        # Run query
        df = pandas_gbq.read_gbq(
            sql_with_params,
            project_id=args.project,
            location=args.location,
            progress_bar_type=None
        )
    except Exception as e:
        print(f"Query failed: {e}")
        print("This query is computationally expensive. Consider:")
        print("1. Reducing the --years parameter")
        print("2. Using a smaller date range in the SQL")
        print("3. Adding more filters to reduce data size")
        return 1

    # Save to CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {len(df):,} rows to {out_path}")
    df.to_csv(out_path, index=False)
    print("Done!")

    # Show summary
    total_utxos = df["utxo_count"].sum()
    total_value = df["total_value_btc"].sum()
    
    print(f"\nSummary:")
    print(f"  Total UTXOs moved: {total_utxos:,}")
    print(f"  Total value moved: {total_value:,.2f} BTC")
    print(f"  Date range: last {args.years} year(s)")
    
    # Show age bucket distribution
    age_summary = df.groupby("age_bucket").agg({
        "utxo_count": "sum",
        "total_value_btc": "sum"
    })
    print(f"\nAge Bucket Distribution:")
    for bucket, row in age_summary.iterrows():
        pct_count = (row["utxo_count"] / total_utxos) * 100
        pct_value = (row["total_value_btc"] / total_value) * 100
        print(f"  {bucket}: {row['utxo_count']:,} UTXOs ({pct_count:.1f}%), {row['total_value_btc']:,.1f} BTC ({pct_value:.1f}%)")

    return 0

if __name__ == "__main__":
    exit(main())
