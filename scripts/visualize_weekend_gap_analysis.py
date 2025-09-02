#!/usr/bin/env python3
"""
Create weekend gap analysis visualization using existing BTC price data.

Usage:
  python scripts/visualize_weekend_gap_analysis.py --csv data/external/btcusd_daily.csv
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

def calculate_gaps(df):
    """Calculate day-to-day price gaps."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    
    # Calculate day of week (0=Monday, 6=Sunday)
    df["dow"] = df["date"].dt.dayofweek
    df["day_name"] = df["date"].dt.day_name()
    
    # Calculate next day's open
    df["next_open"] = df["open"].shift(-1)
    df["next_dow"] = df["dow"].shift(-1)
    
    # Calculate gap percentage: (next_open - close) / close * 100
    df["gap_pct"] = ((df["next_open"] - df["close"]) / df["close"]) * 100
    
    # Remove last row (no next day)
    df = df[:-1].copy()
    
    return df

def main():
    parser = argparse.ArgumentParser(description="Create weekend gap analysis visualization")
    parser.add_argument("--csv", default="data/external/btcusd_daily.csv", help="Input CSV file with BTC prices")
    parser.add_argument("--out_base", default="weekend_gap_analysis", help="Base filename (without extension)")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.csv}")
    df = pd.read_csv(args.csv)
    
    if len(df) == 0:
        print("Error: No data to visualize!")
        return 1
    
    # Calculate gaps
    df = calculate_gaps(df)
    
    # Identify different gap types
    friday_to_monday = df[(df["dow"] == 4) & (df["next_dow"] == 0)]["gap_pct"]  # Friday to Monday
    weekend_gaps = df[df["dow"].isin([4, 5, 6])]["gap_pct"]  # Friday, Saturday, Sunday
    weekday_gaps = df[df["dow"].isin([0, 1, 2, 3])]["gap_pct"]  # Monday to Thursday
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Gap distribution comparison
    bins = np.linspace(-15, 15, 50)
    ax1.hist(weekday_gaps.dropna(), bins=bins, alpha=0.6, label=f'Weekday gaps (n={len(weekday_gaps.dropna())})', 
             color='blue', density=True)
    ax1.hist(weekend_gaps.dropna(), bins=bins, alpha=0.6, label=f'Weekend gaps (n={len(weekend_gaps.dropna())})', 
             color='red', density=True)
    if len(friday_to_monday.dropna()) > 0:
        ax1.hist(friday_to_monday.dropna(), bins=bins, alpha=0.8, label=f'Fri→Mon gaps (n={len(friday_to_monday.dropna())})', 
                 color='orange', density=True)
    ax1.axvline(x=0, color='black', linestyle='--', alpha=0.5)
    ax1.set_xlabel("Gap Percentage (%)")
    ax1.set_ylabel("Density")
    ax1.set_title("Distribution of Price Gaps")
    ax1.legend()
    
    # 2. Gap statistics by day of week
    gap_stats = df.groupby("dow")["gap_pct"].agg(["mean", "std", "count"]).reset_index()
    gap_stats["day_name"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    bars = ax2.bar(gap_stats["day_name"], gap_stats["mean"], 
                   yerr=gap_stats["std"], capsize=4, alpha=0.8)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax2.set_title("Average Gap by Day of Week")
    ax2.set_ylabel("Average Gap (%)")
    ax2.tick_params(axis='x', rotation=45)
    
    # Color bars differently for weekends
    for i, bar in enumerate(bars):
        if i >= 5:  # Saturday, Sunday
            bar.set_color('red')
        elif i == 4:  # Friday
            bar.set_color('orange')
        else:
            bar.set_color('blue')
    
    # 3. Time series of gaps
    df_plot = df.set_index("date")
    ax3.plot(df_plot.index, df_plot["gap_pct"], alpha=0.7, linewidth=0.5)
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax3.set_title("Daily Price Gaps Over Time")
    ax3.set_ylabel("Gap (%)")
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Box plot by day of week
    daily_gaps = [df[df["dow"] == i]["gap_pct"].dropna() for i in range(7)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    bp = ax4.boxplot(daily_gaps, labels=day_labels, patch_artist=True)
    
    # Color boxes
    colors = ['blue', 'blue', 'blue', 'blue', 'orange', 'red', 'red']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax4.set_title("Gap Distribution by Day of Week")
    ax4.set_ylabel("Gap (%)")
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save both PNG and HTML
    title = "Bitcoin Weekend Gap Analysis"
    save_dual_output(fig, args.out_base, title=title)
    
    # Print summary statistics
    print(f"\nSummary Statistics:")
    print(f"  Data range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Total gaps analyzed: {len(df):,}")
    
    print(f"\nGap Statistics:")
    print(f"  Weekday gaps: mean={weekday_gaps.mean():.3f}%, std={weekday_gaps.std():.3f}%")
    print(f"  Weekend gaps: mean={weekend_gaps.mean():.3f}%, std={weekend_gaps.std():.3f}%")
    if len(friday_to_monday) > 0:
        print(f"  Friday→Monday gaps: mean={friday_to_monday.mean():.3f}%, std={friday_to_monday.std():.3f}%")
    
    # Statistical test (optional, requires scipy)
    try:
        from scipy import stats
        if len(weekday_gaps.dropna()) > 0 and len(weekend_gaps.dropna()) > 0:
            t_stat, p_value = stats.ttest_ind(weekday_gaps.dropna(), weekend_gaps.dropna())
            print(f"\nT-test (weekday vs weekend gaps):")
            print(f"  t-statistic: {t_stat:.3f}")
            print(f"  p-value: {p_value:.3f}")
            print(f"  Significant difference: {'Yes' if p_value < 0.05 else 'No'}")
    except ImportError:
        print(f"\nNote: Install scipy for statistical tests: pip install scipy")
    
    # Day-by-day analysis
    print(f"\nDay-by-Day Analysis:")
    for i, day in enumerate(day_labels):
        day_data = daily_gaps[i]
        if len(day_data) > 0:
            print(f"  {day}: mean={day_data.mean():.3f}%, std={day_data.std():.3f}%, n={len(day_data)}")

if __name__ == "__main__":
    main()
