import argparse
import io
import sys
import math
import json
from typing import Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from dateutil import tz

# ---------------------------
# Helpers
# ---------------------------

def fetch_blockchain_com_1y_hourly() -> pd.DataFrame:
    """
    Fetch mempool size for ~last 1 year with 1-hour rolling average from Blockchain.com Charts API.
    Returns a DataFrame with columns: ["ts", "mempool_bytes"]. Timestamps are timezone-aware UTC.
    """
    url = (
        "https://api.blockchain.info/charts/mempool-size"
        "?timespan=1year&rollingAverage=1hour&format=json&sampled=false"
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    payload = r.json()
    values = payload.get("values", [])
    if not values:
        raise RuntimeError("No data returned from Blockchain.com charts API.")
    df = pd.DataFrame(values)
    # Expect columns: x (unix seconds), y (bytes)
    if not {"x", "y"}.issubset(df.columns):
        raise RuntimeError("Unexpected response shape from API. Expected keys 'x' and 'y'.")
    df["ts"] = pd.to_datetime(df["x"], unit="s", utc=True)
    df["mempool_bytes"] = pd.to_numeric(df["y"], errors="coerce")
    df = df[["ts", "mempool_bytes"]].dropna()
    # Some charts can have irregular sampling; resample to hourly to be strict.
    df = (
        df.set_index("ts")
          .resample("1H")
          .mean()
          .interpolate("time")
          .reset_index()
    )
    return df


def read_csv_series(csv_path: str) -> pd.DataFrame:
    """
    Read a CSV with columns ["timestamp", "mempool_bytes"]. Timestamp can be UNIX seconds or ISO8601.
    """
    df = pd.read_csv(csv_path)
    # Try to parse flexibly
    if "timestamp" not in df.columns:
        raise ValueError("CSV must include a 'timestamp' column.")
    if "mempool_bytes" not in df.columns:
        # Try common alternative column names
        alt_cols = [c for c in df.columns if c.lower() in {"mempool_bytes", "bytes", "size_bytes", "mempool_size"}]
        if alt_cols:
            df["mempool_bytes"] = pd.to_numeric(df[alt_cols[0]], errors="coerce")
        else:
            raise ValueError("CSV must include a 'mempool_bytes' (bytes) column.")
    # Parse timestamp
    ts = df["timestamp"]
    try:
        # If it's numeric, assume UNIX seconds
        if pd.api.types.is_numeric_dtype(ts):
            parsed = pd.to_datetime(ts, unit="s", utc=True)
        else:
            parsed = pd.to_datetime(ts, utc=True, errors="coerce")
    except Exception as e:
        raise ValueError(f"Failed to parse timestamps: {e}")
    df["ts"] = parsed
    df["mempool_bytes"] = pd.to_numeric(df["mempool_bytes"], errors="coerce")
    df = df[["ts", "mempool_bytes"]].dropna()
    # Resample hourly for consistency
    df = (
        df.set_index("ts")
          .resample("1H")
          .mean()
          .interpolate("time")
          .reset_index()
    )
    return df


def build_hour_day_heatmap(df: pd.DataFrame, tz_name: str = "America/Denver") -> pd.DataFrame:
    """
    Convert a timestamped series to an Hour × Day-of-Week heatmap table of average mempool size (MB).
    Returns a pivoted DataFrame with rows=Mon..Sun and columns=0..23 hours.
    """
    # Convert to local tz for the "human" hour/day bins
    to_tz = tz.gettz(tz_name)
    local = df.copy()
    local["local_ts"] = local["ts"].dt.tz_convert(to_tz)
    local["day_name"] = local["local_ts"].dt.day_name()
    local["hour"] = local["local_ts"].dt.hour
    # Convert to MB for readability
    local["mempool_mb"] = local["mempool_bytes"] / 1_000_000.0
    # Aggregate
    pivot = (
        local.pivot_table(values="mempool_mb", index="day_name", columns="hour", aggfunc="mean")
    )
    # Reorder days Monday..Sunday
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex(order)
    # Fill gaps along hour axis with interpolation then ffill/bfill
    pivot = pivot.interpolate(axis=1).bfill(axis=1).ffill(axis=1)
    return pivot


import plotly.graph_objects as go

def plot_heatmap(pivot: pd.DataFrame, out_path: str, title_suffix: str = "", annotate: bool = False):
    """
    Render and save the heatmap as both interactive HTML and static PNG.
    """
    import matplotlib.pyplot as plt
    import os
    
    # Create both HTML and PNG versions
    base_path = os.path.splitext(out_path)[0]
    html_path = f"{base_path}.html"
    png_path = f"{base_path}.png"
    
    # Create static PNG using matplotlib
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Average Mempool Size (MB)")
    
    # Set ticks and labels
    ax.set_xticks(range(24))
    ax.set_xticklabels([str(h) for h in range(24)])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    
    # Set labels and title
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Day of Week")
    title = "Bitcoin Mempool Congestion Heatmap — Hour × Day"
    if title_suffix:
        title += f" ({title_suffix})"
    ax.set_title(title)
    
    plt.tight_layout()
    plt.savefig(png_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"Saved PNG heatmap to: {png_path}")
    
    # Create interactive HTML using Plotly
    z = pivot.values
    x = [str(h) for h in pivot.columns]
    y = list(pivot.index)
    ttl = "Bitcoin Mempool Congestion Heatmap — Hour × Day (avg over last ~1 year)"
    if title_suffix:
        ttl += f"<br>{title_suffix}"
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x,
        y=y,
        colorscale="Viridis",
        colorbar=dict(title="Avg mempool size (MB)")
    ))
    fig.update_layout(
        title=ttl,
        xaxis_title="Hour of day",
        yaxis_title="Day of week",
        autosize=True,
        margin=dict(l=60, r=30, t=80, b=60)
    )
    fig.write_html(html_path, include_plotlyjs="cdn")
    print(f"Saved HTML heatmap to: {html_path}")


def main():
    p = argparse.ArgumentParser(description="Mempool Congestion Heatmap (Hour × Day)")
    p.add_argument("--source", choices=["blockchain", "csv"], default="blockchain",
                   help="Data source: 'blockchain' (Blockchain.com API) or 'csv' (provide --csv). Default: blockchain")
    p.add_argument("--csv", type=str, default=None, help="Path to CSV when --source=csv")
    p.add_argument("--tz", type=str, default="America/Denver", help="Timezone for Hour×Day bins (default: America/Denver)")
    p.add_argument("--out", type=str, default="data/figs/mempool_heatmap.html", help="Output HTML path")
    p.add_argument("--save-raw", type=str, default="data/raw/mempool_data.csv", help="Save raw data to CSV")
    p.add_argument("--annotate", action="store_true", help="Annotate some values on the heatmap")
    args = p.parse_args()

    if args.source == "blockchain":
        df = fetch_blockchain_com_1y_hourly()
        title_suffix = "Source: Blockchain.com Charts API (mempool-size, 1h rolling average)"
    else:
        if not args.csv:
            print("Error: --csv is required when --source=csv", file=sys.stderr)
            sys.exit(2)
        df = read_csv_series(args.csv)
        title_suffix = "Source: CSV"
    
    # Save raw data to CSV
    import os
    os.makedirs(os.path.dirname(args.save_raw), exist_ok=True)
    df.to_csv(args.save_raw, index=False)
    print(f"Saved raw data to: {args.save_raw}")

    pivot = build_hour_day_heatmap(df, tz_name=args.tz)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plot_heatmap(pivot, args.out, title_suffix=title_suffix, annotate=args.annotate)


if __name__ == "__main__":
    main()
