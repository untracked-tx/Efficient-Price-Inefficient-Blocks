#!/usr/bin/env python3
"""
Rolling Monday-vs-Others Difference (Interactive)

Computes the rolling difference in mean daily log returns (Monday − others)
using calendar-day windows of 1 year and 2 years. Plots as a time series with
95% confidence bands (Welch t-interval) and a toggle to switch window length.

Input:  data/external/btcusd_daily.csv (columns: date, open, high, low, close, volume)
Output: data/figs/rolling_monday_diff.html
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from math import isfinite
from scipy.stats import t as t_dist

INFILE = Path("data/external/btcusd_daily.csv")
OUTFILE = Path("data/figs/rolling_monday_diff.html")


def welch_ci(diff_mean: float, s2x: float, nx: int, s2y: float, ny: int, alpha=0.05):
    """Return (lower, upper, se, dof, tcrit) for a Welch 100·(1−alpha)% CI of (mean_x − mean_y)."""
    if nx < 2 or ny < 2:
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    se = np.sqrt(s2x / nx + s2y / ny)
    # Welch–Satterthwaite df
    num = (s2x / nx + s2y / ny) ** 2
    den = (s2x**2 / (nx**2 * (nx - 1))) + (s2y**2 / (ny**2 * (ny - 1)))
    dof = num / den if den > 0 else np.nan
    try:
        tcrit = t_dist.ppf(1 - alpha / 2, dof) if isfinite(dof) else 1.96
    except Exception:
        tcrit = 1.96
    lo = diff_mean - tcrit * se
    hi = diff_mean + tcrit * se
    return (lo, hi, se, dof, tcrit)


def rolling_diff(df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Compute rolling (Monday − others) mean log return difference with Welch CI over a calendar window."""
    out = {"date": [], "diff": [], "lo": [], "hi": [], "n_mon": [], "n_oth": []}
    arr = df[["date", "ret", "dow_num"]].to_numpy(object)
    left = 0
    for right in range(len(arr)):
        end_date = arr[right, 0]
        start_date = end_date - pd.Timedelta(days=window_days)
        while left < right and arr[left, 0] < start_date:
            left += 1
        window = arr[left : right + 1]
        mon = np.array([r for (_, r, d) in window if d == 0], dtype=float)  # 0=Mon
        oth = np.array([r for (_, r, d) in window if d != 0], dtype=float)
        if len(mon) >= 8 and len(oth) >= 40:
            m_mon = float(np.nanmean(mon))
            m_oth = float(np.nanmean(oth))
            d = m_mon - m_oth
            s2_mon = float(np.nanvar(mon, ddof=1)) if len(mon) > 1 else np.nan
            s2_oth = float(np.nanvar(oth, ddof=1)) if len(oth) > 1 else np.nan
            lo, hi, se, dof, tcrit = welch_ci(d, s2_mon, len(mon), s2_oth, len(oth))
            out["date"].append(end_date)
            out["diff"].append(d)
            out["lo"].append(lo)
            out["hi"].append(hi)
            out["n_mon"].append(len(mon))
            out["n_oth"].append(len(oth))
    return pd.DataFrame(out)


def main():
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INFILE, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    # Coerce numerics and drop invalids
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "close"]).copy()
    # Daily log return
    df["ret"] = np.log(df["close"] / df["close"].shift(1))
    df = df.dropna(subset=["ret"]).copy()
    df["dow_num"] = df["date"].dt.dayofweek  # 0=Mon .. 6=Sun

    series = {
        "1Y (365d)": rolling_diff(df, 365),
        "2Y (730d)": rolling_diff(df, 730),
    }
    # Precompute extents for buttons
    extents = {
        label: (d["date"].min(), d["date"].max()) for label, d in series.items()
        if len(d) > 0
    }

    # Build Plotly figure with CI ribbons and a window toggle
    fig = go.Figure()
    colors = {"1Y (365d)": "#1f77b4", "2Y (730d)": "#ff7f0e"}
    vis_map = {"1Y (365d)": True, "2Y (730d)": False}
    visibility = []

    for label, dfx in series.items():
        col = colors[label]
        # CI ribbon (upper then lower with fill)
        fig.add_trace(go.Scatter(
            x=dfx["date"], y=dfx["hi"], line=dict(width=0),
            hoverinfo="skip", showlegend=False, name=f"{label} CI upper",
            visible=vis_map[label]
        ))
        visibility.append(vis_map[label])
        fig.add_trace(go.Scatter(
            x=dfx["date"], y=dfx["lo"], line=dict(width=0), fill="tonexty",
            fillcolor=f"rgba({255 if label=='2Y (730d)' else 31}, {127 if label=='1Y (365d)' else 127}, {14 if label=='2Y (730d)' else 180}, 0.18)",
            hoverinfo="skip", showlegend=False, name=f"{label} CI lower",
            visible=vis_map[label]
        ))
        visibility.append(vis_map[label])
        # Mean difference line
        fig.add_trace(go.Scatter(
            x=dfx["date"], y=dfx["diff"], mode="lines", line=dict(color=col, width=2),
            name=f"Mean diff — {label}", visible=vis_map[label],
            hovertemplate="%{x|%Y-%m-%d}<br>Δ = %{y:.3%}<extra></extra>"
        ))
        visibility.append(vis_map[label])

    # Buttons to toggle window (3 traces per series: hi, lo (fill), mean)
    vis_1y = [True, True, True, False, False, False]
    vis_2y = [False, False, False, True, True, True]
    fig.update_layout(
        title="Rolling Monday − Others Mean Daily Log Return Difference",
        xaxis_title="Date", yaxis_title="Δ (Monday − others)",
        yaxis_tickformat=".2%", template="plotly_white",
        hovermode="x unified",
        legend=dict(title="Series"),
        margin=dict(t=70, b=50, l=60, r=30),
        updatemenus=[dict(
            type="buttons", direction="right", x=0.5, xanchor="center", y=1.12, yanchor="top",
            buttons=[
                dict(
                    label="1Y window",
                    method="update",
                    args=[
                        {"visible": vis_1y},
                        {"xaxis": {"range": list(extents.get("1Y (365d)", (df["date"].min(), df["date"].max())))}}
                    ],
                ),
                dict(
                    label="2Y window",
                    method="update",
                    args=[
                        {"visible": vis_2y},
                        {"xaxis": {"range": list(extents.get("2Y (730d)", (df["date"].min(), df["date"].max())))}}
                    ],
                ),
                dict(
                    label="Both",
                    method="update",
                    args=[
                        {"visible": [True]*6},
                        {"xaxis": {"autorange": True}}
                    ],
                ),
            ]
        )]
    )

    fig.add_hline(y=0, line_dash="dot", line_color="#888")
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.16, showarrow=False,
        text="r_t = ln(C_t/C_{t-1}). CI = Welch 95% for (μ_Mon − μ_Others) over rolling calendar windows."
    )

    import plotly.io as pio
    pio.write_html(fig, file=str(OUTFILE), include_plotlyjs="cdn", full_html=True)
    print(f"Saved: {OUTFILE}")


if __name__ == "__main__":
    main()
