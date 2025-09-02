#!/usr/bin/env python3
"""
Create large transaction timing heatmap visualization.

Usage:
  python scripts/visualize_large_transaction_timing.py --csv data/raw/large_transaction_timing.csv
"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

# Add the scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))
from viz_utils import save_dual_output, create_heatmap_html

# Day order for consistent display
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def main():
    parser = argparse.ArgumentParser(description="Create large transaction timing heatmap")
    parser.add_argument("--csv", default="data/raw/large_transaction_timing.csv", help="Input CSV file")
    parser.add_argument("--metric", choices=["tx_count", "total_btc", "avg_btc"], default="tx_count", 
                       help="Metric to visualize")
    parser.add_argument("--out_base", default="large_transaction_timing_heatmap", help="Base filename (without extension)")
    parser.add_argument("--min_btc", type=float, default=100, help="Min BTC threshold (for title)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    # Ensure day_name is categorical with proper order
    df["day_name"] = pd.Categorical(df["day_name"], categories=DAY_ORDER, ordered=True)
    
    # Create pivot table
    pivot = df.pivot_table(
        values=args.metric, 
        index="day_name", 
        columns="hour", 
        aggfunc="sum",
        fill_value=0
    ).reindex(DAY_ORDER)
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    # Create heatmap
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    # Set labels based on metric
    if args.metric == "tx_count":
        cbar.set_label("Transaction Count")
        title_suffix = "Transaction Count"
    elif args.metric == "total_btc":
        cbar.set_label("Total BTC")
        title_suffix = "Total BTC Volume"
    else:  # avg_btc
        cbar.set_label("Average BTC per Transaction")
        title_suffix = "Average Transaction Size"
    
    # Set ticks and labels
    ax.set_xticks(range(24))
    ax.set_xticklabels([str(h) for h in range(24)])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    
    # Set labels and title
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Day of Week")
    ax.set_title(f"Large Transaction Timing (≥{args.min_btc:.0f} BTC) - {title_suffix}")
    
    # Add text annotations for better readability
    if args.metric == "tx_count":
        # Only add text for transaction count to avoid clutter
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                if value > 0:
                    text = ax.text(j, i, f'{int(value)}', 
                                 ha="center", va="center", 
                                 color="white" if value > pivot.values.max() * 0.5 else "black",
                                 fontsize=8)
    
    
    plt.tight_layout()
    
    # Save both PNG and HTML using utility function
    title = f"Large Transaction Timing (≥{args.min_btc:.0f} BTC) - {title_suffix}"
    save_dual_output(fig, args.out_base, title=title)
    
    # Also create interactive HTML heatmap
    html_path = Path("data/figs") / f"{args.out_base}.html"
    success = create_heatmap_html(
        data=pivot.values,
        x_labels=[str(h) for h in range(24)],
        y_labels=pivot.index.tolist(),
        title=title,
        output_path=html_path,
        colorscale='YlOrRd'
    )
    
    if success:
        print(f"✅ Saved interactive HTML: {html_path}")
    else:
        print("⚠️  Install plotly for interactive HTML: pip install plotly")
    
    # Print summary stats
    total_txs = df["tx_count"].sum()
    total_btc = df["total_btc"].sum()
    print(f"\nSummary Statistics:")
    print(f"  Total large transactions: {total_txs:,}")
    print(f"  Total BTC volume: {total_btc:,.2f}")
    print(f"  Peak hour: {pivot.sum(axis=0).idxmax()}:00")
    print(f"  Peak day: {pivot.sum(axis=1).idxmax()}")

if __name__ == "__main__":
    main()
