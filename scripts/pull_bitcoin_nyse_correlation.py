#!/usr/bin/env python3
"""
Pull Bitcoin volume data and NYSE data for correlation analysis.

Usage:
  python scripts/pull_bitcoin_nyse_correlation.py --project YOUR_PROJECT --api_key YOUR_API_KEY
"""
import argparse
import pandas as pd
import requests
from pathlib import Path
import time

def get_nyse_data(api_key, years=2):
    """Get NYSE composite volume data from Alpha Vantage."""
    # Using NYSE Composite Index as proxy for NYSE volume
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "NYA",  # NYSE Composite Index
        "apikey": api_key,
        "outputsize": "full"
    }
    
    print("Fetching NYSE data from Alpha Vantage...")
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error: NYSE API request failed with status {response.status_code}")
        return None
    
    data = response.json()
    
    if "Error Message" in data:
        print(f"Error: {data['Error Message']}")
        return None
    
    if "Note" in data:
        print(f"Warning: {data['Note']}")
        return None
    
    time_series = data.get("Time Series (Daily)", {})
    
    if not time_series:
        print("Error: No time series data found in NYSE response")
        return None
    
    # Convert to DataFrame
    nyse_data = []
    for date_str, values in time_series.items():
        nyse_data.append({
            "date": pd.to_datetime(date_str),
            "nyse_open": float(values["1. open"]),
            "nyse_high": float(values["2. high"]),
            "nyse_low": float(values["3. low"]),
            "nyse_close": float(values["4. close"]),
            "nyse_volume": float(values["5. volume"])
        })
    
    df = pd.DataFrame(nyse_data)
    df = df.sort_values("date")
    
    # Filter to recent years
    cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=years)
    df = df[df["date"] >= cutoff_date]
    
    print(f"Retrieved {len(df)} days of NYSE data")
    return df

def main():
    parser = argparse.ArgumentParser(description="Pull Bitcoin and NYSE volume data")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--api_key", help="Alpha Vantage API key (free from alphavantage.co)")
    parser.add_argument("--years", type=int, default=2, help="Years of data to pull")
    parser.add_argument("--out", default="data/raw/bitcoin_nyse_correlation.csv", help="Output CSV path")
    args = parser.parse_args()

    # Read SQL query for Bitcoin data
    sql_path = Path("sql/bitcoin_volume.sql")
    sql = sql_path.read_text()

    # Import here to avoid forcing install if unused
    try:
        import pandas_gbq
    except ImportError:
        print("Error: Please install pandas-gbq")
        print("pip install pandas-gbq")
        return 1

    print(f"Running Bitcoin volume query...")
    print(f"  Years: {args.years}")

    # Replace parameter in SQL
    sql_with_params = sql.replace("@years", str(args.years))

    # Get Bitcoin data
    btc_df = pandas_gbq.read_gbq(
        sql_with_params,
        project_id=args.project,
        location="US",
        progress_bar_type=None
    )

    print(f"Retrieved {len(btc_df)} rows of Bitcoin data")

    # Get daily Bitcoin data for correlation
    btc_daily = btc_df.groupby("date").agg({
        "daily_volume_btc": "first",
        "daily_tx_count": "first"
    }).reset_index()

    # Get NYSE data if API key provided
    if args.api_key:
        nyse_df = get_nyse_data(args.api_key, args.years)
        if nyse_df is not None:
            # Merge Bitcoin and NYSE data
            merged_df = pd.merge(btc_daily, nyse_df, on="date", how="inner")
            
            # Calculate correlations
            btc_nyse_corr = merged_df["daily_volume_btc"].corr(merged_df["nyse_volume"])
            print(f"Bitcoin-NYSE volume correlation: {btc_nyse_corr:.3f}")
            
            # Save merged data
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            merged_df.to_csv(out_path, index=False)
            print(f"Saved correlation data to {out_path}")
        else:
            print("Failed to get NYSE data, saving Bitcoin data only")
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            btc_daily.to_csv(out_path, index=False)
    else:
        print("No NYSE API key provided, saving Bitcoin data only")
        print("To get NYSE data, sign up for free API key at: https://www.alphavantage.co/support/#api-key")
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        btc_daily.to_csv(out_path, index=False)

    return 0

if __name__ == "__main__":
    exit(main())
