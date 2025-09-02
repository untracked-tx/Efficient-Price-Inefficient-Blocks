#!/usr/bin/env python3
"""
Pull large transaction timing data from BigQuery and save as CSV.

Usage:
  python scripts/pull_large_transaction_timing.py --project YOUR_PROJECT --years 3 --min_btc 100
"""
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Pull large transaction timing data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=3, help="Years of data to pull")
    parser.add_argument("--min_btc", type=float, default=100, help="Minimum BTC output value")
    parser.add_argument("--out", default="data/raw/large_transaction_timing.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query
    sql_path = Path("sql/large_transaction_timing.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
        from google.cloud import bigquery
    except ImportError:
        print("Error: Please install google-cloud-bigquery and pandas-gbq")
        print("pip install google-cloud-bigquery pandas-gbq")
        return

    print(f"Running large transaction timing query...")
    print(f"  Years: {args.years}")
    print(f"  Min BTC: {args.min_btc}")

    # Set up query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("years", "INT64", args.years),
            bigquery.ScalarQueryParameter("min_btc", "FLOAT64", args.min_btc),
        ]
    )

    # Run query
    df = pandas_gbq.read_gbq(
        sql,
        project_id=args.project,
        location=args.location,
        configuration={'query': {'parameterMode': 'NAMED', 'queryParameters': [
            {'name': 'years', 'parameterType': {'type': 'INT64'}, 'parameterValue': {'value': str(args.years)}},
            {'name': 'min_btc', 'parameterType': {'type': 'FLOAT64'}, 'parameterValue': {'value': str(args.min_btc)}}
        ]}}
    )

    # Save to CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {len(df):,} rows to {out_path}")
    df.to_csv(out_path, index=False)
    print("Done!")

    # Show summary
    print(f"\nSummary:")
    print(f"  Total transactions: {df['tx_count'].sum():,}")
    print(f"  Total BTC: {df['total_btc'].sum():,.2f}")
    print(f"  Date range: last {args.years} years")

if __name__ == "__main__":
    main()
