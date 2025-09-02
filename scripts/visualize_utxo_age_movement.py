#!/usr/bin/env python3
"""
Create UTXO age movement visualization.

Usage:
  python scripts/visualize_utxo_age_movement.py --csv data/raw/utxo_age_movement.csv
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

# Define consistent age bucket order
AGE_BUCKET_ORDER = [
    "< 1 day", "1-7 days", "1-4 weeks", "1-3 months", "3-6 months", 
    "6-12 months", "1-2 years", "2-3 years", "3-4 years", "4+ years"
]

def main():
    parser = argparse.ArgumentParser(description="Create UTXO age movement visualization")
    parser.add_argument("--csv", default="data/raw/utxo_age_movement.csv", help="Input CSV file")
    parser.add_argument("--metric", choices=["utxo_count", "total_value_btc"], default="total_value_btc",
                       help="Metric to visualize")
    parser.add_argument("--out_base", default="utxo_age_movement", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Ensure categorical ordering
    df["spend_day_name"] = pd.Categorical(df["spend_day_name"], categories=DAY_ORDER, ordered=True)
    df["age_bucket"] = pd.Categorical(df["age_bucket"], categories=AGE_BUCKET_ORDER, ordered=True)
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Stacked area chart by day of week
    daily_data = df.groupby(["spend_day_name", "age_bucket"])[args.metric].sum().unstack(fill_value=0)
    daily_data = daily_data.reindex(DAY_ORDER)
    
    # Use a colormap for age buckets
    colors = plt.cm.Set3(np.linspace(0, 1, len(AGE_BUCKET_ORDER)))
    
    # Create stacked area plot
    daily_data.plot.area(ax=ax1, stacked=True, alpha=0.8, 
                        color=colors[:len(daily_data.columns)])
    ax1.set_title(f"UTXO Age Movement by Day ({'Value' if args.metric == 'total_value_btc' else 'Count'})")
    ax1.set_xlabel("Day of Week")
    ax1.set_ylabel("BTC Value" if args.metric == "total_value_btc" else "UTXO Count")
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 2. Heatmap of total movement by hour and day
    hourly_data = df.groupby(["spend_day_name", "spend_hour"])[args.metric].sum().unstack(fill_value=0)
    hourly_data = hourly_data.reindex(DAY_ORDER)
    
    im = ax2.imshow(hourly_data.values, aspect="auto", cmap="YlOrRd")
    cbar = plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("BTC Value" if args.metric == "total_value_btc" else "UTXO Count")
    ax2.set_xticks(range(24))
    ax2.set_xticklabels([str(h) for h in range(24)])
    ax2.set_yticks(range(len(hourly_data.index)))
    ax2.set_yticklabels(hourly_data.index)
    ax2.set_xlabel("Hour of Day")
    ax2.set_ylabel("Day of Week")
    ax2.set_title("UTXO Movement Intensity Heatmap")
    
    # 3. Age bucket distribution
    age_totals = df.groupby("age_bucket")[args.metric].sum()
    age_totals = age_totals.reindex([bucket for bucket in AGE_BUCKET_ORDER if bucket in age_totals.index])
    
    wedges, texts, autotexts = ax3.pie(age_totals.values, labels=age_totals.index, autopct='%1.1f%%')
    ax3.set_title(f"Distribution by Age Bucket ({'Value' if args.metric == 'total_value_btc' else 'Count'})")
    
    # 4. Average age by day and hour
    avg_age_data = df.groupby(["spend_day_name", "spend_hour"])["avg_age_days"].mean().unstack(fill_value=0)
    avg_age_data = avg_age_data.reindex(DAY_ORDER)
    
    im2 = ax4.imshow(avg_age_data.values, aspect="auto", cmap="viridis")
    cbar2 = plt.colorbar(im2, ax=ax4, fraction=0.046, pad=0.04)
    cbar2.set_label("Average Age (days)")
    ax4.set_xticks(range(24))
    ax4.set_xticklabels([str(h) for h in range(24)])
    ax4.set_yticks(range(len(avg_age_data.index)))
    ax4.set_yticklabels(avg_age_data.index)
    ax4.set_xlabel("Hour of Day")
    ax4.set_ylabel("Day of Week")
    ax4.set_title("Average UTXO Age When Spent")
    
    plt.tight_layout()
    
    # Save both PNG and HTML
    title = f"UTXO Age Movement Analysis ({'Value' if args.metric == 'total_value_btc' else 'Count'})"
    save_dual_output(fig, args.out_base, title=title)
    
    # Print summary statistics
    total_value = df["total_value_btc"].sum()
    total_count = df["utxo_count"].sum()
    
    print(f"\nSummary Statistics:")
    print(f"  Total UTXOs moved: {total_count:,}")
    print(f"  Total value moved: {total_value:,.2f} BTC")
    print(f"  Average UTXO age: {df['avg_age_days'].mean():.1f} days")
    
    # Day of week analysis
    daily_summary = df.groupby("spend_day_name").agg({
        "utxo_count": "sum",
        "total_value_btc": "sum",
        "avg_age_days": "mean"
    }).reindex(DAY_ORDER)
    
    print(f"\nDay of Week Analysis:")
    for day in DAY_ORDER:
        if day in daily_summary.index:
            row = daily_summary.loc[day]
            print(f"  {day}: {row['utxo_count']:,} UTXOs, {row['total_value_btc']:,.1f} BTC, {row['avg_age_days']:.1f} days avg age")
    
    # Age bucket analysis
    print(f"\nAge Bucket Analysis:")
    for bucket in AGE_BUCKET_ORDER:
        bucket_data = df[df["age_bucket"] == bucket]
        if len(bucket_data) > 0:
            value_sum = bucket_data["total_value_btc"].sum()
            count_sum = bucket_data["utxo_count"].sum()
            pct_value = (value_sum / total_value) * 100
            pct_count = (count_sum / total_count) * 100
            print(f"  {bucket}: {value_sum:,.1f} BTC ({pct_value:.1f}%), {count_sum:,} UTXOs ({pct_count:.1f}%)")

if __name__ == "__main__":
    main()
