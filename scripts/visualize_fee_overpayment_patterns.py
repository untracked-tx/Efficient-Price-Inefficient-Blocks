#!/usr/bin/env python3
"""
Create fee overpayment patterns visualization.

Usage:
  python scripts/visualize_fee_overpayment_patterns.py --csv data/raw/fee_overpayment_patterns.csv
"""
import argparse
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from pathlib import Path

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def main():
    parser = argparse.ArgumentParser(description="Create fee overpayment patterns visualization")
    parser.add_argument("--csv", default="data/raw/fee_overpayment_patterns.csv", help="Input CSV file")
    parser.add_argument("--out_base", default="fee_overpayment_patterns", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Handle NaN values before setting categorical
    df = df.fillna(0)
    # Ensure day_name is categorical
    df["day_name"] = pd.Categorical(df["day_name"], categories=DAY_ORDER, ordered=True)
    
    # Aggregate by day of week
    daily_stats = df.groupby("day_name").agg({
        "total_transactions": "sum",
        "overpayment_transactions": "sum",
        "overpayment_percentage": "mean",
        "avg_fee_ratio": "mean",
        "total_overpayment_btc": "sum"
    }).reindex(DAY_ORDER)

    # Recalculate percentage for aggregated data
    daily_stats["overpayment_pct_actual"] = (daily_stats["overpayment_transactions"] /
                                            daily_stats["total_transactions"]) * 100

    # 1. Overpayment percentage by day of week (Plotly Bar)
    bar_fig = go.Figure()
    bar_fig.add_trace(go.Bar(
        x=daily_stats.index,
        y=daily_stats["overpayment_pct_actual"],
        marker_color='orange',
        text=[f'{v:.1f}%' for v in daily_stats["overpayment_pct_actual"]],
        textposition='outside',
    ))
    bar_fig.update_layout(
        title="Fee Overpayment Rate by Day of Week",
        yaxis_title="Overpayment Rate (%)",
        xaxis_title="Day of Week",
        template="plotly_white",
        height=400
    )

    # 2. Heatmap of overpayment percentage by hour and day (Plotly Heatmap)
    pivot = df.pivot_table(
        values="overpayment_percentage",
        index="day_name",
        columns="hour",
        aggfunc="mean",
        fill_value=0
    ).reindex(DAY_ORDER)
    heatmap_fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[str(h) for h in range(24)],
        y=pivot.index,
        colorscale='Reds',
        colorbar=dict(title="Overpayment Rate (%)")
    ))
    heatmap_fig.update_layout(
        title="Fee Overpayment Rate Heatmap",
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        template="plotly_white",
        height=400
    )

    # 3. Average fee ratio by day (Plotly Bar)
    ratio_fig = go.Figure()
    ratio_fig.add_trace(go.Bar(
        x=daily_stats.index,
        y=daily_stats["avg_fee_ratio"],
        marker_color='skyblue',
        text=[f'{v:.2f}x' for v in daily_stats["avg_fee_ratio"]],
        textposition='outside',
    ))
    ratio_fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="1x (median)", annotation_position="bottom right")
    ratio_fig.add_hline(y=2, line_dash="dash", line_color="orange", annotation_text="2x (overpayment threshold)", annotation_position="top right")
    ratio_fig.update_layout(
        title="Average Fee Ratio by Day of Week",
        yaxis_title="Fee Ratio (actual/median)",
        xaxis_title="Day of Week",
        template="plotly_white",
        height=400
    )

    # 4. Total overpayment value by day (Plotly Bar)
    value_fig = go.Figure()
    value_fig.add_trace(go.Bar(
        x=daily_stats.index,
        y=daily_stats["total_overpayment_btc"],
        marker_color='red',
        text=[f'{v:.2f} BTC' for v in daily_stats["total_overpayment_btc"]],
        textposition='outside',
    ))
    value_fig.update_layout(
        title="Total Overpayment Value by Day of Week",
        yaxis_title="Overpayment Value (BTC)",
        xaxis_title="Day of Week",
        template="plotly_white",
        height=400
    )

    # Save interactive HTML with all figures
    out_html = f"data/figs/{args.out_base}_interactive.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(pio.to_html(bar_fig, full_html=False, include_plotlyjs="cdn"))
        f.write(pio.to_html(heatmap_fig, full_html=False, include_plotlyjs=False))
        f.write(pio.to_html(ratio_fig, full_html=False, include_plotlyjs=False))
        f.write(pio.to_html(value_fig, full_html=False, include_plotlyjs=False))
    print(f"✅ Saved interactive HTML: {out_html}")
    
    # Print summary statistics
    total_txs = daily_stats["total_transactions"].sum()
    total_overpayments = daily_stats["overpayment_transactions"].sum()
    overall_rate = (total_overpayments / total_txs) * 100 if total_txs > 0 else 0
    total_waste = daily_stats["total_overpayment_btc"].sum()
    
    print(f"\nSummary Statistics:")
    print(f"  Total transactions: {total_txs:,}")
    print(f"  Total overpayments: {total_overpayments:,}")
    print(f"  Overall overpayment rate: {overall_rate:.2f}%")
    print(f"  Total overpayment value: {total_waste:.3f} BTC")
    print(f"  Average fee ratio: {daily_stats['avg_fee_ratio'].mean():.2f}x")
    
    # Day of week analysis
    print(f"\nDay of Week Analysis:")
    for day in DAY_ORDER:
        if day in daily_stats.index:
            row = daily_stats.loc[day]
            rate = row["overpayment_pct_actual"]
            ratio = row["avg_fee_ratio"]
            value = row["total_overpayment_btc"]
            print(f"  {day}: {rate:.1f}% rate, {ratio:.2f}x avg ratio, {value:.3f} BTC waste")
    
    # Find peak patterns
    hourly_avg = df.groupby("hour")["overpayment_percentage"].mean()
    peak_hour = hourly_avg.idxmax()
    peak_rate = hourly_avg.max()
    
    print(f"\nPeak Patterns:")
    print(f"  Peak overpayment hour: {peak_hour}:00 ({peak_rate:.1f}%)")
    print(f"  Peak overpayment day: {daily_stats['overpayment_pct_actual'].idxmax()} ({daily_stats['overpayment_pct_actual'].max():.1f}%)")

if __name__ == "__main__":
    main()
