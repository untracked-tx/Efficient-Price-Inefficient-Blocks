#!/usr/bin/env python3
"""
Pull fee overpayment patterns data from BigQuery.

Usage:
  python scripts/pull_fee_overpayment_patterns.py --project YOUR_PROJECT --years 2
"""
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pull fee overpayment patterns data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=2, help="Years of data to pull")
    parser.add_argument("--out", default="data/raw/fee_overpayment_patterns.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query
    sql_path = Path("sql/fee_overpayment_patterns.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
    except ImportError:
        print("Error: Please install pandas-gbq")
        print("pip install pandas-gbq")
        return 1

    print(f"Running fee overpayment patterns query...")
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
    total_txs = df["total_transactions"].sum()
    total_overpayments = df["overpayment_transactions"].sum()
    overall_overpayment_pct = (total_overpayments / total_txs) * 100 if total_txs > 0 else 0
    total_overpayment_btc = df["total_overpayment_btc"].sum()
    
    print(f"\nSummary:")
    print(f"  Total transactions: {total_txs:,}")
    print(f"  Overpayment transactions: {total_overpayments:,}")
    print(f"  Overall overpayment rate: {overall_overpayment_pct:.2f}%")
    print(f"  Total overpayment value: {total_overpayment_btc:.2f} BTC")
    print(f"  Average fee ratio: {df['avg_fee_ratio'].mean():.2f}x")
    print(f"  Date range: last {args.years} years")

    return 0

if __name__ == "__main__":
    exit(main())
