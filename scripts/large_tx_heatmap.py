#!/usr/bin/env python3
"""
Create a heatmap visualization of large transaction timing patterns.

Usage:
  python scripts/large_tx_heatmap.py --csv data/raw/large_tx_timing.csv --out data/figs/large_tx_heatmap.png
"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Ensure proper day ordering
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="data/raw/large_tx_timing.csv", help="Input CSV file")
    p.add_argument("--out", default="data/figs/large_tx_heatmap.png", help="Output PNG file")
    p.add_argument("--metric", default="tx_count", choices=["tx_count", "avg_btc_amount", "median_btc_amount"], 
                   help="Metric to visualize")
    p.add_argument("--min_btc", type=float, default=100, help="BTC threshold for title")
    p.add_argument("--years", type=int, default=3, help="Years of data for title")
    args = p.parse_args()

    # Load data
    df = pd.read_csv(args.csv)
    
    # Create pivot table for heatmap
    pivot = df.pivot_table(
        values=args.metric, 
        index="day_name", 
        columns="hour", 
        aggfunc="sum" if args.metric == "tx_count" else "mean"
    ).reindex(DAY_ORDER)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    # Create heatmap
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    # Set labels based on metric
    if args.metric == "tx_count":
        cbar.set_label("Transaction count", fontsize=12)
        title_metric = "Transaction Count"
    elif args.metric == "avg_btc_amount":
        cbar.set_label("Average BTC amount", fontsize=12)
        title_metric = "Average BTC Amount"
    else:
        cbar.set_label("Median BTC amount", fontsize=12)
        title_metric = "Median BTC Amount"
    
    # Set ticks and labels
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    
    # Labels and title
    ax.set_xlabel("Hour of Day (UTC)", fontsize=12)
    ax.set_ylabel("Day of Week", fontsize=12)
    ax.set_title(f"Large Transaction Timing (≥{args.min_btc} BTC) - {title_metric}\nLast {args.years} Years", 
                 fontsize=14, fontweight='bold')
    
    # Add text annotations with values
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if not np.isnan(value):
                if args.metric == "tx_count":
                    text = f"{int(value)}"
                else:
                    text = f"{value:.0f}"
                ax.text(j, i, text, ha="center", va="center", 
                       color="white" if value > pivot.values.max() * 0.6 else "black",
                       fontsize=8, fontweight='bold')
    
    plt.tight_layout()
    
    # Ensure output directory exists
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save figure
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    print(f"Saved heatmap to {out_path}")
    
    # Print summary stats
    total_transactions = df['tx_count'].sum()
    peak_hour = df.loc[df['tx_count'].idxmax()]
    print(f"\nSummary:")
    print(f"Total large transactions: {total_transactions:,}")
    print(f"Peak activity: {peak_hour['day_name']} at {peak_hour['hour']:02d}:00 UTC ({peak_hour['tx_count']} transactions)")
    print(f"Average BTC amount: {df['avg_btc_amount'].mean():.1f}")

if __name__ == "__main__":
    main()
