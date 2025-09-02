#!/usr/bin/env python3
"""
Create exchange inflow/outflow visualization.

Usage:
  python scripts/visualize_exchange_flows.py --csv data/raw/exchange_flows.csv
"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

# Add the scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))
from viz_utils import save_dual_output

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def main():
    parser = argparse.ArgumentParser(description="Create exchange flow visualization")
    parser.add_argument("--csv", default="data/raw/exchange_flows.csv", help="Input CSV file")
    parser.add_argument("--out_base", default="exchange_flows", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Convert date and ensure day_name is categorical
    df["date"] = pd.to_datetime(df["date"])
    df["day_name"] = pd.Categorical(df["day_name"], categories=DAY_ORDER, ordered=True)
    
    # Aggregate by day of week
    daily_stats = df.groupby("day_name").agg({
        "inflow_btc": ["mean", "sum", "std"],
        "outflow_btc": ["mean", "sum", "std"], 
        "net_flow_btc": ["mean", "sum", "std"]
    }).round(2)
    
    # Flatten column names
    daily_stats.columns = ['_'.join(col).strip() for col in daily_stats.columns]
    daily_stats = daily_stats.reindex(DAY_ORDER)
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Net Flow by Day of Week (Bar Chart)
    bars = ax1.bar(daily_stats.index, daily_stats["net_flow_btc_mean"], 
                   yerr=daily_stats["net_flow_btc_std"], 
                   capsize=4, alpha=0.8,
                   color=['red' if x < 0 else 'green' for x in daily_stats["net_flow_btc_mean"]])
    ax1.set_title("Average Net Flow by Day of Week")
    ax1.set_ylabel("Net Flow (BTC)")
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Inflow vs Outflow by Day (Grouped Bar)
    x = np.arange(len(daily_stats.index))
    width = 0.35
    ax2.bar(x - width/2, daily_stats["inflow_btc_mean"], width, 
            label='Inflow', alpha=0.8, color='blue')
    ax2.bar(x + width/2, daily_stats["outflow_btc_mean"], width,
            label='Outflow', alpha=0.8, color='orange')
    ax2.set_title("Average Inflow vs Outflow by Day")
    ax2.set_ylabel("BTC")
    ax2.set_xticks(x)
    ax2.set_xticklabels(daily_stats.index, rotation=45)
    ax2.legend()
    
    # 3. Time series of net flows
    df_sorted = df.sort_values("date")
    ax3.plot(df_sorted["date"], df_sorted["net_flow_btc"], alpha=0.7, linewidth=1)
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax3.set_title("Net Flow Over Time")
    ax3.set_ylabel("Net Flow (BTC)")
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Distribution of net flows
    ax4.hist(df["net_flow_btc"], bins=50, alpha=0.8, edgecolor='black')
    ax4.axvline(x=0, color='red', linestyle='--', alpha=0.8)
    ax4.axvline(x=df["net_flow_btc"].mean(), color='green', linestyle='--', alpha=0.8, 
                label=f'Mean: {df["net_flow_btc"].mean():.2f}')
    ax4.set_title("Distribution of Daily Net Flows")
    ax4.set_xlabel("Net Flow (BTC)")
    ax4.set_ylabel("Frequency")
    ax4.legend()
    
    plt.tight_layout()
    
    # Save both PNG and HTML
    title = "Bitcoin Exchange Flow Analysis"
    save_dual_output(fig, args.out_base, title=title)
    
    # Print summary stats
    print(f"\nSummary Statistics:")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Total days: {len(df):,}")
    print(f"  Average daily inflow: {df['inflow_btc'].mean():,.2f} BTC")
    print(f"  Average daily outflow: {df['outflow_btc'].mean():,.2f} BTC")
    print(f"  Average daily net flow: {df['net_flow_btc'].mean():,.2f} BTC")
    print(f"  Net flow over period: {df['net_flow_btc'].sum():,.2f} BTC")
    
    # Day of week analysis
    print(f"\nDay of Week Analysis:")
    for day in DAY_ORDER:
        if day in daily_stats.index:
            net_flow = daily_stats.loc[day, "net_flow_btc_mean"]
            print(f"  {day}: {net_flow:+.2f} BTC average net flow")

if __name__ == "__main__":
    main()
