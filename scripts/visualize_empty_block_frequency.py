#!/usr/bin/env python3
"""
Create empty block frequency visualization.

Usage:
  python scripts/visualize_empty_block_frequency.py --csv data/raw/empty_block_frequency.csv
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
    parser = argparse.ArgumentParser(description="Create empty block frequency visualization")
    parser.add_argument("--csv", default="data/raw/empty_block_frequency.csv", help="Input CSV file")
    parser.add_argument("--out_base", default="empty_block_frequency", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Ensure day_name is categorical
    df["day_name"] = pd.Categorical(df["day_name"], categories=DAY_ORDER, ordered=True)
    
    # Aggregate by day of week
    daily_stats = df.groupby("day_name").agg({
        "total_blocks": "sum",
        "empty_blocks": "sum",
        "empty_block_percentage": "mean",
        "avg_tx_count": "mean"
    }).reindex(DAY_ORDER)
    
    # Recalculate percentage for aggregated data
    daily_stats["empty_block_pct_actual"] = (daily_stats["empty_blocks"] / daily_stats["total_blocks"]) * 100
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Empty Block Percentage by Day of Week
    bars = ax1.bar(daily_stats.index, daily_stats["empty_block_pct_actual"], 
                   alpha=0.8, color='coral')
    ax1.set_title("Empty Block Percentage by Day of Week")
    ax1.set_ylabel("Empty Block Percentage (%)")
    ax1.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}%', ha='center', va='bottom')
    
    # 2. Heatmap of empty block percentage by hour and day
    pivot = df.pivot_table(
        values="empty_block_percentage", 
        index="day_name", 
        columns="hour", 
        aggfunc="mean"
    ).reindex(DAY_ORDER)
    
    im = ax2.imshow(pivot.values, aspect="auto", cmap="Reds")
    cbar = plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("Empty Block Percentage (%)")
    ax2.set_xticks(range(24))
    ax2.set_xticklabels([str(h) for h in range(24)])
    ax2.set_yticks(range(len(pivot.index)))
    ax2.set_yticklabels(pivot.index)
    ax2.set_xlabel("Hour of Day")
    ax2.set_ylabel("Day of Week")
    ax2.set_title("Empty Block Frequency Heatmap")
    
    # 3. Average Transaction Count by Day
    ax3.bar(daily_stats.index, daily_stats["avg_tx_count"], 
            alpha=0.8, color='lightblue')
    ax3.set_title("Average Transactions per Block by Day")
    ax3.set_ylabel("Average Tx Count")
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Time series of empty block percentage (if we have hourly data)
    hourly_empty = df.groupby("hour")["empty_block_percentage"].mean()
    ax4.plot(hourly_empty.index, hourly_empty.values, marker='o', linewidth=2, markersize=4)
    ax4.set_title("Empty Block Percentage by Hour of Day")
    ax4.set_xlabel("Hour of Day")
    ax4.set_ylabel("Empty Block Percentage (%)")
    ax4.set_xticks(range(0, 24, 2))
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save both PNG and HTML
    title = "Bitcoin Empty Block Frequency Analysis"
    save_dual_output(fig, args.out_base, title=title)
    
    # Print summary stats
    total_blocks = daily_stats["total_blocks"].sum()
    total_empty = daily_stats["empty_blocks"].sum()
    overall_empty_pct = (total_empty / total_blocks) * 100
    
    print(f"\nSummary Statistics:")
    print(f"  Total blocks analyzed: {total_blocks:,}")
    print(f"  Total empty blocks: {total_empty:,}")
    print(f"  Overall empty block percentage: {overall_empty_pct:.2f}%")
    print(f"  Average transactions per block: {daily_stats['avg_tx_count'].mean():.1f}")
    
    # Day of week analysis
    print(f"\nDay of Week Analysis:")
    for day in DAY_ORDER:
        if day in daily_stats.index:
            pct = daily_stats.loc[day, "empty_block_pct_actual"]
            count = daily_stats.loc[day, "empty_blocks"]
            print(f"  {day}: {pct:.2f}% empty ({count:,} blocks)")
    
    # Find peak hours
    peak_hour = hourly_empty.idxmax()
    peak_pct = hourly_empty.max()
    print(f"\nPeak empty block hour: {peak_hour}:00 ({peak_pct:.2f}%)")

if __name__ == "__main__":
    main()
