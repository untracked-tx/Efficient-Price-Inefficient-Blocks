#!/usr/bin/env python3
"""
Block Fullness Heatmap - Can work with BigQuery or existing CSV.
"""

import argparse
import pandas as pd
import plotly.express as px
import os

def run_bigquery(project_id: str):
    """Pull data from BigQuery and save to CSV."""
    from pandas_gbq import read_gbq
    
    query = """
    WITH block_fullness AS (
      SELECT
        TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
        AVG(weight / 4000000.0) AS avg_fullness,
        COUNT(*) AS n_blocks
      FROM `bigquery-public-data.crypto_bitcoin.blocks`
      WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 YEAR)
      GROUP BY 1
    )
    SELECT
      EXTRACT(DAYOFWEEK FROM hour) AS dow,
      EXTRACT(HOUR FROM hour) AS hod,
      APPROX_QUANTILES(avg_fullness, 100)[OFFSET(50)] AS p50_fullness
    FROM block_fullness
    GROUP BY dow, hod
    ORDER BY dow, hod
    """
    
    print("Running BigQuery...")
    df = read_gbq(query, project_id=project_id)
    
    # Save raw data
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/block_fullness.csv", index=False)
    df.to_parquet("data/raw/block_fullness.parquet", index=False)
    print("Saved raw data to data/raw/")
    
    return df

def load_csv(csv_path: str):
    """Load existing CSV data."""
    return pd.read_csv(csv_path)

def create_visualization(df: pd.DataFrame, out_dir: str = "data/figs"):
    """Create the heatmap visualization."""
    # Create pivot table
    pivot = df.pivot_table(values="p50_fullness", index="dow", columns="hod", aggfunc="first")
    
    # Map day numbers to names (1=Sunday in BigQuery)
    day_map = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
    pivot.index = [day_map.get(i, f"Day{i}") for i in pivot.index]
    
    # Create heatmap
    fig = px.imshow(
        pivot,
        labels=dict(x="Hour of Day", y="Day of Week", color="Median Block Fullness"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale="YlOrRd"
    )
    fig.update_layout(title="Bitcoin Block Fullness Patterns — Hour×Day Heatmap")
    
    # Save outputs
    os.makedirs(out_dir, exist_ok=True)
    fig.write_html(f"{out_dir}/block_fullness_heatmap.html")
    fig.write_image(f"{out_dir}/block_fullness_heatmap.png")
    
    print(f"Saved visualization to {out_dir}/")

def main():
    parser = argparse.ArgumentParser(description="Block Fullness Heatmap")
    parser.add_argument("--source", choices=["bigquery", "csv"], default="csv", 
                       help="Data source: bigquery or csv")
    parser.add_argument("--project", type=str, help="GCP project ID (for BigQuery)")
    parser.add_argument("--csv", type=str, default="block_fullness.csv", 
                       help="CSV file path (for CSV source)")
    parser.add_argument("--out", type=str, default="data/figs", 
                       help="Output directory")
    args = parser.parse_args()
    
    if args.source == "bigquery":
        if not args.project:
            print("Error: --project required for BigQuery source")
            return
        df = run_bigquery(args.project)
    else:
        df = load_csv(args.csv)
    
    create_visualization(df, args.out)

if __name__ == "__main__":
    main()
