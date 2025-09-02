#!/usr/bin/env python3
"""
Create block time variance visualization.

Usage:
  python scripts/visualize_block_time_variance.py --csv data/raw/block_time_variance.csv
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
    parser = argparse.ArgumentParser(description="Create block time variance visualization")
    parser.add_argument("--csv", default="data/raw/block_time_variance.csv", help="Input CSV file")
    parser.add_argument("--out_base", default="block_time_variance", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Ensure day_name is categorical
    df["day_name"] = pd.Categorical(df["day_name"], categories=DAY_ORDER, ordered=True)
    
    # Convert seconds to minutes for better readability
    df["avg_interval_minutes"] = df["avg_interval_seconds"] / 60
    df["std_interval_minutes"] = df["std_interval_seconds"] / 60
    df["median_interval_minutes"] = df["median_interval_seconds"] / 60
    
    # Aggregate by day of week
    daily_stats = df.groupby("day_name").agg({
        "avg_interval_minutes": "mean",
        "std_interval_minutes": "mean", 
        "median_interval_minutes": "mean",
        "block_count": "sum"
    }).reindex(DAY_ORDER)
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Average Block Time by Day of Week (with error bars)
    ax1.bar(daily_stats.index, daily_stats["avg_interval_minutes"], 
            yerr=daily_stats["std_interval_minutes"], 
            capsize=4, alpha=0.8, color='steelblue')
    ax1.axhline(y=10, color='red', linestyle='--', alpha=0.8, label='Target (10 min)')
    ax1.set_title("Average Block Time by Day of Week")
    ax1.set_ylabel("Time (minutes)")
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend()
    ax1.set_ylim(0, max(daily_stats["avg_interval_minutes"]) * 1.2)
    
    # 2. Block Count by Day
    ax2.bar(daily_stats.index, daily_stats["block_count"], alpha=0.8, color='green')
    ax2.set_title("Number of Blocks by Day of Week")
    ax2.set_ylabel("Block Count")
    ax2.tick_params(axis='x', rotation=45)
    
    # 3. Heatmap of block times by hour and day
    pivot = df.pivot_table(
        values="avg_interval_minutes", 
        index="day_name", 
        columns="hour", 
        aggfunc="mean"
    ).reindex(DAY_ORDER)
    
    im = ax3.imshow(pivot.values, aspect="auto", cmap="RdYlBu_r")
    cbar = plt.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
    cbar.set_label("Average Block Time (minutes)")
    ax3.set_xticks(range(24))
    ax3.set_xticklabels([str(h) for h in range(24)])
    ax3.set_yticks(range(len(pivot.index)))
    ax3.set_yticklabels(pivot.index)
    ax3.set_xlabel("Hour of Day")
    ax3.set_ylabel("Day of Week")
    ax3.set_title("Block Time Heatmap (Hour × Day)")
    
    # 4. Box plot of block times by day
    daily_data = []
    day_labels = []
    for day in DAY_ORDER:
        day_data = df[df["day_name"] == day]["avg_interval_minutes"]
        if len(day_data) > 0:
            daily_data.append(day_data)
            day_labels.append(day)
    
    if daily_data:
        bp = ax4.boxplot(daily_data, labels=day_labels, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax4.axhline(y=10, color='red', linestyle='--', alpha=0.8, label='Target (10 min)')
        ax4.set_title("Block Time Distribution by Day")
        ax4.set_ylabel("Time (minutes)")
        ax4.tick_params(axis='x', rotation=45)
        ax4.legend()
    
    plt.tight_layout()
    
    # Save both PNG and HTML
    title = "Bitcoin Block Time Variance Analysis"
    save_dual_output(fig, args.out_base, title=title)
    
    # Print summary stats
    overall_avg = daily_stats["avg_interval_minutes"].mean()
    print(f"\nSummary Statistics:")
    print(f"  Overall average block time: {overall_avg:.2f} minutes")
    print(f"  Target block time: 10.00 minutes")
    print(f"  Deviation from target: {overall_avg - 10:+.2f} minutes")
    print(f"  Total blocks analyzed: {daily_stats['block_count'].sum():,}")
    
    # Day of week analysis
    print(f"\nDay of Week Analysis:")
    for day in DAY_ORDER:
        if day in daily_stats.index:
            avg_time = daily_stats.loc[day, "avg_interval_minutes"]
            deviation = avg_time - 10
            print(f"  {day}: {avg_time:.2f} min (target {deviation:+.2f})")

if __name__ == "__main__":
    main()
