import argparse
import pandas as pd
import plotly.graph_objects as go
from dateutil import tz

ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def build_heatmap(csv_path: str, tz_name: str = "UTC"):
    df = pd.read_csv(csv_path)
    if "block_timestamp" not in df.columns:
        raise ValueError("CSV must include 'block_timestamp' column.")
    ts = pd.to_datetime(df["block_timestamp"], utc=True, errors="coerce")
    to_tz = tz.gettz(tz_name)
    local = ts.dt.tz_convert(to_tz)
    day_name = local.dt.day_name()
    hour = local.dt.hour
    agg = (
        pd.DataFrame({"day_name": day_name, "hour": hour})
        .dropna()
        .groupby(["day_name","hour"]).size().rename("tx_count").reset_index()
    )
    pivot = agg.pivot_table(values="tx_count", index="day_name", columns="hour", aggfunc="sum").reindex(ORDER)
    # Ensure all hours present
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]
    return pivot

def save_plot(pivot, out_html: str, min_btc: float, years: int, tz_name: str):
    z = pivot.values
    x = [str(h) for h in pivot.columns]
    y = list(pivot.index)
    title = f"Large Transactions ≥ {min_btc} BTC — Hour×Day (last {years}y)<br>Timezone: {tz_name}"
    fig = go.Figure(data=go.Heatmap(z=z, x=x, y=y, colorscale="Viridis", colorbar=dict(title="Tx count")))
    fig.update_layout(title=title, xaxis_title="Hour of day", yaxis_title="Day of week", margin=dict(l=60,r=30,t=90,b=60))
    fig.write_html(out_html, include_plotlyjs="cdn")
    print(f"Saved interactive heatmap to: {out_html}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/raw/large_tx_timing.csv")
    ap.add_argument("--out", default="data/figs/large_tx_heatmap.html")
    ap.add_argument("--min_btc", type=float, default=100.0)
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--tz", default="UTC")
    args = ap.parse_args()

    pivot = build_heatmap(args.csv, tz_name=args.tz)
    save_plot(pivot, args.out, min_btc=args.min_btc, years=args.years, tz_name=args.tz)

if __name__ == "__main__":
    main()
