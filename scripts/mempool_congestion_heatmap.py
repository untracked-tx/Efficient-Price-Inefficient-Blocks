#!/usr/bin/env python3
"""
Create a heatmap visualization of mempool congestion patterns using BigQuery fee rate data.

Usage:
  python scripts/mempool_congestion_heatmap.py --csv data/raw/mempool_congestion.csv --out data/figs/mempool_congestion_heatmap.png
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
    p.add_argument("--csv", default="data/raw/mempool_congestion.csv", help="Input CSV file")
    p.add_argument("--out", default="data/figs/mempool_congestion_heatmap.png", help="Output PNG file")
    p.add_argument("--metric", default="median_fee_rate", 
                   choices=["median_fee_rate", "avg_fee_rate", "p75_fee_rate", "p95_fee_rate"], 
                   help="Fee rate metric to visualize")
    p.add_argument("--years", type=int, default=1, help="Years of data for title")
    args = p.parse_args()

    # Load data
    df = pd.read_csv(args.csv)
    
    # Create pivot table for heatmap
    pivot = df.pivot_table(
        values=args.metric, 
        index="day_name", 
        columns="hour", 
        aggfunc="mean"
    ).reindex(DAY_ORDER)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    # Create heatmap with a color scheme that shows congestion (red = high fees = congestion)
    im = ax.imshow(pivot.values, aspect="auto", cmap="Reds")
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    # Set labels based on metric
    metric_labels = {
        "median_fee_rate": "Median Fee Rate (sat/vB)",
        "avg_fee_rate": "Average Fee Rate (sat/vB)", 
        "p75_fee_rate": "75th Percentile Fee Rate (sat/vB)",
        "p95_fee_rate": "95th Percentile Fee Rate (sat/vB)"
    }
    
    cbar.set_label(metric_labels[args.metric], fontsize=12)
    
    # Set ticks and labels
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    
    # Labels and title
    ax.set_xlabel("Hour of Day (UTC)", fontsize=12)
    ax.set_ylabel("Day of Week", fontsize=12)
    ax.set_title(f"Mempool Congestion Heatmap - {metric_labels[args.metric]}\nLast {args.years} Year(s)", 
                 fontsize=14, fontweight='bold')
    
    # Add text annotations with values
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if not np.isnan(value):
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
    print(f"Saved mempool congestion heatmap to {out_path}")
    
    # Print summary stats
    peak_congestion = df.loc[df[args.metric].idxmax()]
    print(f"\nSummary:")
    print(f"Peak congestion: {peak_congestion['day_name']} at {peak_congestion['hour']:02d}:00 UTC ({peak_congestion[args.metric]:.1f} sat/vB)")
    print(f"Overall median fee rate: {df['median_fee_rate'].mean():.1f} sat/vB")
    print(f"Overall 95th percentile: {df['p95_fee_rate'].mean():.1f} sat/vB")

if __name__ == "__main__":
    main()
