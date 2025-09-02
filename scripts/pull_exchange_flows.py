#!/usr/bin/env python3
"""
Pull exchange inflow/outflow data from BigQuery.

Usage:
  python scripts/pull_exchange_flows.py --project YOUR_PROJECT --exchanges exchanges.txt
"""
import argparse
import pandas as pd
from pathlib import Path

# Default known exchange addresses (sample - you should expand this list)
DEFAULT_EXCHANGE_ADDRESSES = [
    # Coinbase (sample addresses)
    "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64",
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block (placeholder)
    # Binance (sample addresses)
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    # Kraken (sample addresses)  
    "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j",
    # Add more known exchange addresses here
]

def load_exchange_addresses(file_path=None):
    """Load exchange addresses from file or use defaults."""
    if file_path and Path(file_path).exists():
        print(f"Loading exchange addresses from {file_path}")
        with open(file_path, 'r') as f:
            addresses = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return addresses
    else:
        print("Using default exchange addresses (limited set)")
        print("Note: For production analysis, provide a comprehensive list via --exchanges file")
        return DEFAULT_EXCHANGE_ADDRESSES

def main():
    parser = argparse.ArgumentParser(description="Pull exchange flow data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--location", default="US", help="BigQuery location")
    parser.add_argument("--years", type=int, default=2, help="Years of data to pull")
    parser.add_argument("--exchanges", help="File with exchange addresses (one per line)")
    parser.add_argument("--out", default="data/raw/exchange_flows.csv", help="Output CSV path")
    args = parser.parse_args()

    # Load exchange addresses
    exchange_addresses = load_exchange_addresses(args.exchanges)
    print(f"Loaded {len(exchange_addresses)} exchange addresses")

    if len(exchange_addresses) == 0:
        print("Error: No exchange addresses loaded!")
        return 1

    # Read SQL query
    sql_path = Path("sql/exchange_flows.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
        from google.cloud import bigquery
    except ImportError:
        print("Error: Please install google-cloud-bigquery and pandas-gbq")
        print("pip install google-cloud-bigquery pandas-gbq")
        return 1

    print(f"Running exchange flows query...")
    print(f"  Years: {args.years}")
    print(f"  Exchange addresses: {len(exchange_addresses)}")

    # Set up query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("exchange_addresses", "STRING", exchange_addresses),
            bigquery.ScalarQueryParameter("years", "INT64", args.years),
        ]
    )

    # Note: Due to BigQuery parameter limitations, we need to use a different approach
    # Let's modify the query to include addresses directly
    addresses_str = "', '".join(exchange_addresses)
    sql_with_addresses = sql.replace(
        "SELECT address FROM UNNEST(@exchange_addresses) AS address",
        f"SELECT address FROM UNNEST(['{addresses_str}']) AS address"
    ).replace("@years", str(args.years))

    # Run query
    try:
        df = pandas_gbq.read_gbq(
            sql_with_addresses,
            project_id=args.project,
            location=args.location,
            progress_bar_type=None
        )
    except Exception as e:
        print(f"Query failed: {e}")
        print("This might be due to the limited exchange address list or query complexity.")
        print("Consider using a more comprehensive exchange address dataset.")
        return 1

    # Save to CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {len(df):,} rows to {out_path}")
    df.to_csv(out_path, index=False)
    print("Done!")

    # Show summary
    if len(df) > 0:
        print(f"\nSummary:")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Total inflow: {df['inflow_btc'].sum():,.2f} BTC")
        print(f"  Total outflow: {df['outflow_btc'].sum():,.2f} BTC")
        print(f"  Net flow: {df['net_flow_btc'].sum():,.2f} BTC")
    else:
        print("Warning: No data returned. Check exchange addresses and query.")

    return 0

if __name__ == "__main__":
    exit(main())
