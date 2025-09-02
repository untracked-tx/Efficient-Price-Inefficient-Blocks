import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

CSV_PATH = "data/external/btcusd_daily.csv"
SAVE_PATH = "data/figs/one_figure_to_rule_them_all_interactive.html"

# Load daily price data
_df = pd.read_csv(CSV_PATH, parse_dates=["date"])
_df = _df.sort_values("date").reset_index(drop=True)
_df["close"] = pd.to_numeric(_df["close"], errors="coerce")
_df = _df.dropna(subset=["close"]).copy()
_df["ret"] = _df["close"].pct_change()
_df = _df.dropna(subset=["ret"]).copy()

weekday_map = {0:"Mon", 1:"Tue", 2:"Wed", 3:"Thu", 4:"Fri", 5:"Sat", 6:"Sun"}
_df["weekday"] = _df["date"].dt.dayofweek.map(weekday_map)
weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Timeframes
frames = {
    "All": _df,
    "5 Years": _df[_df["date"] >= _df["date"].max() - pd.DateOffset(years=5)],
    "3 Years": _df[_df["date"] >= _df["date"].max() - pd.DateOffset(years=3)],
    "1 Year": _df[_df["date"] >= _df["date"].max() - pd.DateOffset(years=1)],
    "6 Months": _df[_df["date"] >= _df["date"].max() - pd.DateOffset(months=6)]
}

# Compute stats for each timeframe
stats_dict = {}
for label, df in frames.items():
    stats = df.groupby("weekday").agg(
        mean_ret=("ret", "mean"),
        up_share=("ret", lambda x: np.mean(x > 0))
    ).reindex(weekday_order)
    stats_dict[label] = stats

# Colors and style
bar_color = "#4C78A8"
dot_color = "#222222"
ann_color = "#2ca02c"
font_family = "Open Sans, Arial, sans-serif"

# Create traces for each timeframe
traces = []
for i, (label, stats) in enumerate(stats_dict.items()):
    bar_heights = stats["mean_ret"].values * 100.0
    up_pct = stats["up_share"].values * 100.0
    traces.append(go.Bar(
        x=weekday_order,
        y=bar_heights,
        name=f"{label} Mean Return",
        marker_color=bar_color,
        visible=(i==0),
        text=[f"{v:.2f}%" for v in bar_heights],
        textposition="outside",
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        width=0.6
    ))
    traces.append(go.Scatter(
        x=weekday_order,
        y=bar_heights + 0.02,
        mode="markers+text",
        marker=dict(color=dot_color, size=10),
        text=[f"{v:.0f}%" for v in up_pct],
        textposition="top center",
        name=f"{label} Up Share",
        visible=(i==0),
        hovertemplate="%{x}: %{text} up days<extra></extra>"
    ))

# Dropdown menu
dropdown = [
    dict(
        args=[{"visible": [i==j or i==j+len(frames) for i in range(len(frames)*2)]}],
        label=label,
        method="update"
    )
    for j, label in enumerate(frames.keys())
]

# Annotation text for each timeframe
annotations = []
for i, (label, stats) in enumerate(stats_dict.items()):
    weekend_avg = stats.loc[["Sat", "Sun"], "mean_ret"].mean() * 100.0
    weekdays_avg = stats.loc[["Mon", "Tue", "Wed", "Thu", "Fri"], "mean_ret"].mean() * 100.0
    ann_text = f"<b>{label}:</b> Weekends avg {weekend_avg:.2f}%, Weekdays avg {weekdays_avg:.2f}%"
    annotations.append(dict(
        text=ann_text,
        xref="paper", yref="paper",
        x=0.5, y=1.08,
        showarrow=False,
        font=dict(size=16, color=ann_color, family=font_family),
        align="center",
        visible=(i==0)
    ))

# Layout
layout = go.Layout(
    title=dict(
        text="<b>Average Bitcoin Daily Return by Weekday</b>",
        font=dict(size=24, family=font_family, color="#222222")
    ),
    yaxis=dict(
        title="Average daily return (%)",
        tickformat=".2f",
        gridcolor="#EEEEEE",
        zerolinecolor="#888888",
        zerolinewidth=1.2,
        showline=True,
        linecolor="#BBBBBB",
        linewidth=1.2,
        range=[-0.15, 0.55]
    ),
    xaxis=dict(
        title="Weekday",
        tickmode="array",
        tickvals=weekday_order,
        ticktext=weekday_order,
        showline=True,
        linecolor="#BBBBBB",
        linewidth=1.2
    ),
    updatemenus=[dict(
        active=0,
        buttons=dropdown,
        x=0.5,
        xanchor="center",
        y=1.18,
        yanchor="top"
    )],
    annotations=annotations,
    font=dict(family=font_family, size=15, color="#222222"),
    margin=dict(t=120, b=60, l=70, r=30),
    height=540,
    width=950,
    plot_bgcolor="#FAFAFA"
)

fig = go.Figure(data=traces, layout=layout)

# Add callback to update annotation visibility
fig.update_layout(
    updatemenus=[dict(
        type="dropdown",
        active=0,
        buttons=dropdown,
        x=0.5,
        xanchor="center",
        y=1.18,
        yanchor="top"
    )]
)
for i in range(len(frames)):
    fig.layout.annotations[i].visible = (i==0)

fig.write_html(SAVE_PATH, include_plotlyjs="cdn", full_html=True)
print(f"Saved interactive figure to: {SAVE_PATH}")
