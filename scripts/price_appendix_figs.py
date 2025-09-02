import pandas as pd, numpy as np
import plotly.express as px, plotly.graph_objects as go
from pathlib import Path

INFILE = "data/external/btcusd_daily.csv"
OUTDIR = Path("data/figs"); OUTDIR.mkdir(parents=True, exist_ok=True)

# Load daily and compute returns
_df = pd.read_csv(INFILE, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
if "close" not in _df.columns:
    raise SystemExit("CSV must have 'close' column.")
_df["close"] = pd.to_numeric(_df["close"], errors="coerce")
_df = _df.dropna(subset=["close"]).copy()
_df["ret_d"] = np.log(_df["close"]).diff()
_df = _df.dropna(subset=["ret_d"]).copy()

# Weekday mapping
_df["dow_i"] = _df["date"].dt.dayofweek  # 0=Mon ... 6=Sun
dow_map = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
_df["DOW"] = _df["dow_i"].map(dow_map)
_df["is_weekend"] = _df["dow_i"].isin([5,6]).astype(int)

# Figure E1: % Up Days by Weekday
up_rate = (_df.assign(up=_df["ret_d"]>0)
             .groupby("DOW")["up"].mean()
             .reindex(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]))
figE1 = px.bar(up_rate, title="Share of Up Days by Weekday",
               labels={"value":"% up days","DOW":"Weekday"})
figE1.update_layout(template="plotly_white"); figE1.update_yaxes(tickformat=".0%", range=[0,1])
figE1.write_html(OUTDIR/"upday_rate_by_weekday.html", include_plotlyjs="cdn")

# Figure E2: Volatility by Weekday (median |return|)
vol = (_df.assign(absret=_df["ret_d"].abs())
         .groupby("DOW")["absret"].median()
         .reindex(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]))
figE2 = px.bar(vol, title="Median Absolute Daily Return by Weekday (Volatility)",
               labels={"value":"Median |log return|","DOW":"Weekday"})
figE2.update_layout(template="plotly_white"); figE2.update_yaxes(tickformat=".2%")
figE2.write_html(OUTDIR/"abs_return_by_weekday.html", include_plotlyjs="cdn")

# Figure E3: Cumulative return if trading only a given weekday vs Buy & Hold
cum = []
for i, name in dow_map.items():
    mask = (_df["dow_i"]==i)
    r = _df["ret_d"].where(mask, 0.0)
    cum_val = np.exp(r.cumsum())
    cum.append(pd.DataFrame({"date": _df["date"], "index": cum_val, "Strategy": f"Only {name}"}))
# Buy & Hold
bh = pd.DataFrame({"date": _df["date"], "index": np.exp(_df["ret_d"].cumsum()), "Strategy":"Buy & Hold"})
plot_df = pd.concat(cum + [bh])
figE3 = px.line(plot_df, x="date", y="index", color="Strategy",
                title="Cumulative Return: Only-One-Weekday Strategies vs Buy & Hold",
                labels={"index":"Growth of $1","date":"Date"})
figE3.update_layout(template="plotly_white")
figE3.write_html(OUTDIR/"cumret_by_weekday_strategy.html", include_plotlyjs="cdn")

# Figure E4: Month x Weekday average return heatmap (simple seasonality grid)
heat = (_df.assign(Month=_df["date"].dt.month)
          .groupby(["Month","DOW"])['ret_d']
          .mean()
          .reset_index())
# Ensure order
heat["DOW"] = pd.Categorical(heat["DOW"], ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], ordered=True)
heat = heat.sort_values(["Month","DOW"]) 
figE4 = px.density_heatmap(heat, x="DOW", y="Month", z="ret_d", color_continuous_scale="RdBu",
                           title="Average Daily Return by Month × Weekday",
                           labels={"ret_d":"Avg log return"})
figE4.update_layout(template="plotly_white"); figE4.update_coloraxes(colorbar=dict(tickformat=".2%"))
figE4.write_html(OUTDIR/"heatmap_month_weekday_returns.html", include_plotlyjs="cdn")

print("Saved:",
      OUTDIR/"upday_rate_by_weekday.html",
      OUTDIR/"abs_return_by_weekday.html",
      OUTDIR/"cumret_by_weekday_strategy.html",
      OUTDIR/"heatmap_month_weekday_returns.html")
