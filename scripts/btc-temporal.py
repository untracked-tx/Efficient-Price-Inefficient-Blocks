# app.py
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta

import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import sequential
import os
try:
    from dash import Dash, dcc, html, Input, Output, State, callback
    DASH_AVAILABLE = True
except Exception:
    DASH_AVAILABLE = False
from statsmodels.stats.anova import anova_lm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.stattools import durbin_watson
import statsmodels.api as sm
from scipy.stats import f_oneway
from scipy.stats import ttest_ind, gaussian_kde

# ---------- 1) LOAD + PREP DATA ----------
# Expect a CSV with at least: date, close
# If you have OHLCV, just rename your closing column to 'close'
CSV_PATH = Path("data/external/btcusd_daily.csv")  # <-- correct file

def load_data(path=CSV_PATH):
    df = pd.read_csv(path, parse_dates=["date"])
    # Convert price columns to numeric
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.sort_values("date").dropna(subset=["date", "close"])
    # Keep one row per calendar day (choose last obs per day if multiple)
    df["date"] = df["date"].dt.tz_localize(None)
    df = df.groupby(df["date"].dt.date).tail(1)  # if input has intraday rows
    df["date"] = pd.to_datetime(df["date"])
    df["ret"] = np.log(df["close"] / df["close"].shift(1))
    df["dow"] = df["date"].dt.day_name()
    df["year"] = df["date"].dt.year
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    df["dow"] = pd.Categorical(df["dow"], ordered=True, categories=order)
    return df.dropna(subset=["ret"])

df = load_data()

# Helper: filter by date range
def filter_range(df, start, end):
    return df[(df["date"] >= start) & (df["date"] <= end)]

# ---------- 2) FIGURE BUILDERS ----------
def fig_violin(df):
    fig = px.violin(
        df, x="dow", y="ret", box=True, points="outliers", color="dow",
        category_orders={"dow": list(df["dow"].cat.categories)},
        template="plotly_white"
    )
    fig.update_layout(
        title="BTC Daily Log Returns by Day of Week",
        yaxis_title="Log return",
        xaxis_title="Day of week",
        showlegend=False
    )
    return fig

def fig_one_to_rule(df):
    # Build a combined bar (mean return) + dot (share up days) chart
    by = df.groupby("dow", observed=False).agg(mean_ret=("ret","mean"), up_share=("ret", lambda s: (s>0).mean())).reset_index()
    by = by.sort_values("dow")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=by["dow"].astype(str), y=by["mean_ret"], name="Mean return", marker_color="#1f77b4"))
    fig.add_trace(go.Scatter(x=by["dow"].astype(str), y=by["up_share"], name="Up-day share", mode="markers+lines", yaxis="y2", marker=dict(color="#ff7f0e", size=8)))
    fig.update_layout(
        title="Average Daily Return by Weekday (Bars) with Up-Day Share (Dots)",
        template="plotly_white",
        xaxis_title="Day of week",
        yaxis=dict(title="Mean log return"),
        yaxis2=dict(title="Share up days", overlaying="y", side="right", range=[0,1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def export_figures_and_stats(df, outdir="data/figs/enhanced", overwrite=False):
    os.makedirs(outdir, exist_ok=True)

    def save_html(fig, path):
        if (not overwrite) and os.path.exists(path):
            return
        fig.write_html(path, include_plotlyjs='cdn')

    # Violin plot (+ alias expected by paper.qmd)
    vio = fig_violin(df)
    save_html(vio, os.path.join(outdir, "btc_violin_by_day.html"))
    save_html(vio, os.path.join(outdir, "daily_monday_effect.html"))
    # Ridgeline KDE by weekday
    save_html(fig_ridgeline(df), os.path.join(outdir, "btc_ridgeline_weekday_returns.html"))
    # Heatmap
    save_html(fig_heatmap(df), os.path.join(outdir, "btc_heatmap_year_weekday.html"))
    # Weekly cycle
    save_html(fig_weekly_cycle(df), os.path.join(outdir, "btc_weekly_cycle.html"))
    # Distribution overlay (Monday)
    save_html(fig_distribution_overlay(df, "Monday"), os.path.join(outdir, "btc_dist_overlay_monday.html"))
    # Executive summary figure expected by paper
    save_html(fig_one_to_rule(df), os.path.join(outdir, "one_figure_to_rule_them_all_interactive.html"))
    # Rolling t-stat
    roll = rolling_tstat(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roll["date"], y=roll["tstat"], mode="lines", name="2yr rolling t-stat (Mon vs Rest)", line=dict(color="blue")))
    fig.update_layout(title="Rolling 2-Year t-stat: Monday vs Rest", xaxis_title="Date", yaxis_title="t-stat", template="plotly_white")
    save_html(fig, os.path.join(outdir, "btc_rolling_tstat.html"))
    # Stats tables
    means = group_means_table(df)
    ols_nw = weekday_ols_newey_west(df)
    fval, pval = weekday_anova(df)
    tukey = weekday_tukey(df)
    mon = df[df["dow"] == "Monday"]["ret"]
    rest = df[df["dow"] != "Monday"]["ret"]
    cohen_d = cohens_d(mon, rest) if len(mon) > 5 and len(rest) > 5 else None
    cliff_delta = cliffs_delta(mon.values, rest.values) if len(mon) > 5 and len(rest) > 5 else None
    # Save stats as markdown
    with open(os.path.join(outdir, "btc_stats_summary.md"), "w", encoding="utf-8") as f:
        f.write("# Group Means by Weekday\n")
        f.write(means.to_markdown(index=False) + "\n\n")
        f.write("# OLS (Newey–West SE)\n")
        f.write(ols_nw.to_markdown() + "\n\n")
        f.write(f"# ANOVA F-test\nF = {fval:.3f}, p = {pval:.4g}\n\n")
        f.write("# Tukey HSD Pairwise\n")
        f.write(tukey.to_markdown(index=False) + "\n\n")
        f.write("# Effect Size: Monday vs Rest\n")
        f.write(f"Cohen's d: {cohen_d:.3f}\n" if cohen_d is not None else "Cohen's d: N/A\n")
        f.write(f"Cliff's δ: {cliff_delta:.3f}\n" if cliff_delta is not None else "Cliff's δ: N/A\n")

def export_report_html(outdir="data/figs/enhanced"):
        """Create a single lightweight HTML page that embeds the key figures via iframes.
        This avoids needing Dash export and gives one clean file for Quarto embedding.
        """
        os.makedirs(outdir, exist_ok=True)
        report_path = os.path.join(outdir, "btc_temporal_report.html")
        html_doc = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>BTC Weekday Effects — Report</title>
    <style>
        body {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }}
        .viz-container {{ max-width: 1100px; margin: 0 auto 28px auto; }}
        h1, h2 {{ margin: 14px 0; }}
        iframe {{ width: 100%; border: 0; box-shadow: 0 2px 12px #0001; border-radius: 10px; }}
        .caption {{ color: #666; font-size: 0.95rem; margin: 8px 0 20px 0; }}
    </style>
    <link rel=\"preconnect\" href=\"https://cdn.plot.ly\" />
    <link rel=\"preconnect\" href=\"https://cdnjs.cloudflare.com\" />
    <link rel=\"dns-prefetch\" href=\"https://cdn.plot.ly\" />
    <link rel=\"dns-prefetch\" href=\"https://cdnjs.cloudflare.com\" />
    <meta name=\"robots\" content=\"noindex\" />
    <meta charset=\"utf-8\" />
  
</head>
<body>
    <h1>BTC Day-of-Week Effects — Key Visuals</h1>
    <div class=\"viz-container\">
        <h2>Executive Summary</h2>
        <iframe src=\"one_figure_to_rule_them_all_interactive.html\" height=\"540\"></iframe>
        <div class=\"caption\">Average daily return by weekday (bars) with share of up days (dots).</div>
    </div>

    <div class=\"viz-container\">
        <h2>Distribution by Weekday</h2>
        <iframe src=\"daily_monday_effect.html\" height=\"520\"></iframe>
    </div>

    <div class=\"viz-container\">
        <h2>Average Daily Return Heatmap (Year × Weekday)</h2>
        <iframe src=\"btc_heatmap_year_weekday.html\" height=\"520\"></iframe>
    </div>

    <div class=\"viz-container\">
        <h2>Weekly Cycle (Mon→Sun Cumulative Mean)</h2>
        <iframe src=\"btc_weekly_cycle.html\" height=\"520\"></iframe>
    </div>

    <div class=\"viz-container\">
        <h2>Rolling 2-Year t-stat: Monday vs Rest</h2>
        <iframe src=\"btc_rolling_tstat.html\" height=\"420\"></iframe>
    </div>

    <div class=\"viz-container\">
        <h2>Distribution Overlay (Monday vs Rest)</h2>
        <iframe src=\"btc_dist_overlay_monday.html\" height=\"520\"></iframe>
    </div>

</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_doc)
        return report_path

def fig_heatmap(df):
    avg = df.groupby(["year","dow"], observed=False)["ret"].mean().reset_index()
    fig = px.density_heatmap(
        avg, x="dow", y="year", z="ret",
        category_orders={"dow": list(df["dow"].cat.categories)},
        color_continuous_scale="RdBu", template="plotly_white"
    )
    fig.update_layout(
        title="Average Daily Return Heatmap (Year × Weekday)",
        xaxis_title="", yaxis_title=""
    )
    return fig

def fig_weekly_cycle(df):
    # Align weeks: map each date to day-of-week index (0=Mon,...6=Sun)
    df = df.copy()
    df["dowi"] = df["dow"].cat.codes
    # Compute mean cumulative path within the week
    by_dowi = df.groupby("dowi", observed=False)["ret"].mean().reindex(range(7)).fillna(0)
    cum = by_dowi.cumsum()
    # Bootstrap CI ribbon
    boot_cum = []
    for _ in range(500):
        boot = df.sample(frac=1, replace=True)
        boot_by_dowi = boot.groupby("dowi", observed=False)["ret"].mean().reindex(range(7)).fillna(0)
        boot_cum.append(boot_by_dowi.cumsum().values)
    boot_cum = np.array(boot_cum)
    lower = np.percentile(boot_cum, 2.5, axis=0)
    upper = np.percentile(boot_cum, 97.5, axis=0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(df["dow"].cat.categories), y=cum.values, mode="lines+markers",
        name="Avg weekly cycle"
    ))
    fig.add_trace(go.Scatter(
        x=list(df["dow"].cat.categories), y=upper, mode="lines",
        line=dict(width=0), fill=None, showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=list(df["dow"].cat.categories), y=lower, mode="lines",
        line=dict(width=0), fill='tonexty', fillcolor='rgba(0,100,255,0.1)',
        name="95% CI"
    ))
    # Annotate major events (stub)
    # Example: fig.add_annotation(x="Friday", y=cum[4], text="ETF Launch", showarrow=True)
    fig.update_layout(
        title="Average ‘Weekly Cycle’ of Returns (Mon→Sun Cumulative Mean)",
        xaxis_title="Day of week", yaxis_title="Cumulative mean return",
        template="plotly_white"
    )
    return fig
# Effect size metrics
def cohens_d(x, y):
    nx, ny = len(x), len(y)
    pooled_std = np.sqrt(((nx-1)*np.var(x, ddof=1) + (ny-1)*np.var(y, ddof=1)) / (nx+ny-2))
    return (np.mean(x) - np.mean(y)) / pooled_std

def cliffs_delta(x, y):
    # Standard Cliff's delta: count all pairwise comparisons
    nx, ny = len(x), len(y)
    more = sum(xi > yj for xi in x for yj in y)
    less = sum(xi < yj for xi in x for yj in y)
    return (more - less) / (nx * ny)

# Rolling t-stat plot
def rolling_tstat(df, window=504):
    # 504 trading days ~ 2 years
    tstats = []
    dates = []
    for i in range(window, len(df)):
        dff = df.iloc[i-window:i]
        mon = dff[dff["dow"] == "Monday"]["ret"]
        rest = dff[dff["dow"] != "Monday"]["ret"]
        if len(mon) > 5 and len(rest) > 5:
            tstat, _ = ttest_ind(mon, rest, equal_var=False)
            tstats.append(tstat)
            dates.append(dff["date"].iloc[-1])
    return pd.DataFrame({"date": dates, "tstat": tstats})

def fig_distribution_overlay(df, focus_day="Monday"):
    sel = df[df["dow"] == focus_day]["ret"]
    rest = df[df["dow"] != focus_day]["ret"]
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=rest, name="Rest of week", opacity=0.5, nbinsx=80))
    fig.add_trace(go.Histogram(x=sel, name=focus_day, opacity=0.6, nbinsx=80))
    fig.update_layout(
        barmode="overlay", template="plotly_white",
        title=f"Distribution: {focus_day} vs Rest of Week",
        xaxis_title="Daily log return", yaxis_title="Count"
    )
    return fig

def fig_ridgeline(df):
    """Ridgeline (joyplot-style) stacked KDEs by weekday using Plotly."""
    cats = list(df["dow"].cat.categories)
    day_colors = {
        "Monday": "#636EFA",
        "Tuesday": "#EF553B",
        "Wednesday": "#00CC96",
        "Thursday": "#AB63FA",
        "Friday": "#FFA15A",
        "Saturday": "#19D3F3",
        "Sunday": "#FF6692",
    }
    # Trim tails for a stable x-range
    lo, hi = df["ret"].quantile([0.01, 0.99])
    xs = np.linspace(lo, hi, 400)
    fig = go.Figure()
    for i, day in enumerate(cats):
        vals = df[df["dow"] == day]["ret"].dropna().values
        if len(vals) < 10:
            continue
        kde = gaussian_kde(vals)
        ys = kde(xs)
        maxy = float(ys.max()) if float(ys.max()) > 0 else 1.0
        ys = ys / maxy * 0.8
        base = np.full_like(xs, i, dtype=float)
        poly_x = np.concatenate([xs, xs[::-1]])
        poly_y = np.concatenate([base + ys, base[::-1]])
        color = day_colors.get(day, "#999999")
        fig.add_trace(go.Scatter(
            x=poly_x, y=poly_y, mode="lines", fill="toself",
            name=day, line=dict(color=color, width=1), fillcolor=color+"33",
            hovertemplate=f"{day}: ret=%{{x:.4f}}<extra></extra>", showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[xs[0], xs[-1]], y=[i, i], mode="lines",
            line=dict(color="#bbbbbb", width=1), showlegend=False, hoverinfo="skip"
        ))
    fig.update_layout(
        title="Ridgeline: Return Distributions by Weekday (KDE)",
        template="plotly_white",
        xaxis_title="Daily log return",
        yaxis=dict(title="", tickmode="array", tickvals=list(range(len(cats))), ticktext=cats),
        margin=dict(t=60, b=40, l=60, r=30),
        height=520 + 8*len(cats)
    )
    return fig

# ---------- 3) STATS (ANOVA-ish + OLS dummies, lightweight) ----------

# OLS with Newey-West SE
def weekday_ols_newey_west(df):
    order = list(df["dow"].cat.categories)
    baseline = "Monday"
    df["dow_code"] = df["dow"].cat.codes
    model = ols("ret ~ C(dow)", data=df).fit(cov_type='HAC', cov_kwds={'maxlags':1})
    summary = model.summary2().tables[1]
    return summary

# ANOVA F-test
def weekday_anova(df):
    groups = [df[df["dow"] == d]["ret"] for d in df["dow"].cat.categories]
    fval, pval = f_oneway(*groups)
    return fval, pval

# Tukey HSD pairwise
def weekday_tukey(df):
    tukey = pairwise_tukeyhsd(df["ret"], df["dow"])
    return pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])

def group_means_table(df):
    means = df.groupby("dow", observed=False)["ret"].agg(["mean","std","count"]).reset_index()
    means.rename(columns={"mean":"mean_ret","std":"std_ret","count":"n"}, inplace=True)
    return means

"""Optional Dash app for interactive exploration.
This section is only active if Dash is installed.
"""
if DASH_AVAILABLE:
    # ---------- 4) DASH APP ----------
    app = Dash(__name__)
    app.title = "BTC Weekday Effects"

    min_date = df["date"].min()
    max_date = df["date"].max()
    default_start = max(min_date, max_date - relativedelta(years=3))

    app.layout = html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto", "fontFamily": "Inter, system-ui, sans-serif"},
        children=[
            html.H1("BTC Day-of-Week Effects — Interactive", style={"marginTop":"20px"}),

            # Controls
            html.Div(style={"display":"grid","gridTemplateColumns":"2fr 1fr 1fr 1fr","gap":"12px"}, children=[
                dcc.DatePickerRange(
                    id="daterange",
                    min_date_allowed=min_date, max_date_allowed=max_date,
                    start_date=default_start, end_date=max_date,
                    display_format="YYYY-MM-DD"
                ),
                dcc.Dropdown(
                    id="focus-day", options=[{"label":d, "value":d} for d in df["dow"].cat.categories],
                    value="Monday", clearable=False
                ),
                dcc.Checklist(
                    id="winsorize",
                    options=[{"label":" Winsorize 1% tails", "value":"win"}],
                    value=[],
                    style={"alignSelf":"center"}
                ),
                dcc.Dropdown(
                    id="regime", options=[
                        {"label": "All", "value": "all"},
                        {"label": "Pre-2017", "value": "pre2017"},
                        {"label": "2017–2020", "value": "2017_2020"},
                        {"label": "2020+", "value": "2020plus"}
                    ], value="all", clearable=False
                )
            ]),

            html.Div(style={"height":"10px"}),

            # Tabs
            dcc.Tabs(id="tabs", value="violin", children=[
                dcc.Tab(label="Violin (by Day)", value="violin"),
                dcc.Tab(label="Heatmap (Year × Weekday)", value="heatmap"),
                dcc.Tab(label="Weekly Cycle (Mon→Sun)", value="cycle"),
                dcc.Tab(label="Distribution Overlay", value="dist"),
                dcc.Tab(label="Stats", value="stats"),
                dcc.Tab(label="Rolling t-stat", value="rolling"),
            ]),
            html.Div(id="tab-content", style={"marginTop":"16px"}),

            html.Hr(),
            html.P("Tip: Use the date picker to scope to regimes (e.g., post-2020). All visuals and stats update live.",
                   style={"color":"#666"})
        ]
    )

    # ---------- 5) CALLBACKS ----------

    @callback(
        Output("tab-content", "children"),
        Input("tabs", "value"),
        Input("daterange", "start_date"),
        Input("daterange", "end_date"),
        Input("focus-day", "value"),
        Input("winsorize", "value"),
        Input("regime", "value"),
    )
    def render_tab(tab, start_date, end_date, focus_day, win, regime):
        dff = filter_range(df, pd.to_datetime(start_date), pd.to_datetime(end_date)).copy()
        # Regime split
        if regime == "pre2017":
            dff = dff[dff["date"] < pd.to_datetime("2017-01-01")]
        elif regime == "2017_2020":
            dff = dff[(dff["date"] >= pd.to_datetime("2017-01-01")) & (dff["date"] < pd.to_datetime("2020-01-01"))]
        elif regime == "2020plus":
            dff = dff[dff["date"] >= pd.to_datetime("2020-01-01")]

        # optional winsorization for prettier plots (does not affect station tests that need full tails)
        if "win" in win and len(dff) > 10:
            lo, hi = dff["ret"].quantile([0.01, 0.99])
            dff["ret"] = dff["ret"].clip(lo, hi)

        if tab == "violin":
            return dcc.Graph(figure=fig_violin(dff), config={"displayModeBar": True})
        elif tab == "heatmap":
            return dcc.Graph(figure=fig_heatmap(dff), config={"displayModeBar": True})
        elif tab == "cycle":
            return dcc.Graph(figure=fig_weekly_cycle(dff), config={"displayModeBar": True})
        elif tab == "dist":
            return dcc.Graph(figure=fig_distribution_overlay(dff, focus_day), config={"displayModeBar": True})
        elif tab == "rolling":
            roll = rolling_tstat(dff)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=roll["date"], y=roll["tstat"], mode="lines", name="2yr rolling t-stat (Mon vs Rest)", line=dict(color="blue")))
            fig.update_layout(title="Rolling 2-Year t-stat: Monday vs Rest", xaxis_title="Date", yaxis_title="t-stat", template="plotly_white")
            return dcc.Graph(figure=fig, config={"displayModeBar": True})
        elif tab == "stats":
            means = group_means_table(dff)
            ols_nw = weekday_ols_newey_west(dff)
            fval, pval = weekday_anova(dff)
            tukey = weekday_tukey(dff)
            # Effect sizes
            mon = dff[dff["dow"] == "Monday"]["ret"]
            rest = dff[dff["dow"] != "Monday"]["ret"]
            cohen_d = cohens_d(mon, rest) if len(mon) > 5 and len(rest) > 5 else None
            cliff_delta = cliffs_delta(mon.values, rest.values) if len(mon) > 5 and len(rest) > 5 else None

            return html.Div([
                html.H3("Group Means by Weekday"),
                dcc.Graph(
                    figure=px.bar(
                        means, x="dow", y="mean_ret",
                        category_orders={"dow": list(df["dow"].cat.categories)},
                        title="Average Return by Day (means with counts in hover)",
                        template="plotly_white"
                    ).update_traces(hovertemplate="Day=%{x}<br>Mean=%{y:.6f}")
                ),
                html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr 1fr 1fr","gap":"16px"}, children=[
                    html.Div([
                        html.H4("Summary Table"),
                        dcc.Markdown(means.to_markdown(index=False))
                    ]),
                    html.Div([
                        html.H4("OLS (Newey–West SE)"),
                        dcc.Markdown(ols_nw.to_markdown())
                    ]),
                    html.Div([
                        html.H4("ANOVA F-test"),
                        html.P(f"F = {fval:.3f}, p = {pval:.4g}"),
                        html.H4("Tukey HSD Pairwise"),
                        dcc.Markdown(tukey.to_markdown(index=False))
                    ]),
                    html.Div([
                        html.H4("Effect Size: Monday vs Rest"),
                        html.P(f"Cohen's d: {cohen_d:.3f}" if cohen_d is not None else "Cohen's d: N/A"),
                        html.P(f"Cliff's δ: {cliff_delta:.3f}" if cliff_delta is not None else "Cliff's δ: N/A")
                    ])
                ])
            ])

        return html.Div("Unknown tab")
else:
    app = None

# ---------- 6) RUN ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export BTC weekday effects figures and optional report")
    parser.add_argument("--outdir", default="data/figs/enhanced", help="Output directory for HTML/CSV")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing HTML files")
    parser.add_argument("--report-only", action="store_true", help="Only write the single-page report HTML")
    parser.add_argument("--dash-export", action="store_true", help="Also export the full Dash app to HTML (requires dash export)")
    args = parser.parse_args()

    # Export figures and report
    if not args.report_only:
        export_figures_and_stats(df, outdir=args.outdir, overwrite=args.overwrite)
        print(f"Exported main figures and stats to {args.outdir}/")
    report = export_report_html(outdir=args.outdir)
    print(f"Wrote single-page report HTML: {report}")

    # Optional: Export full Dash app as standalone HTML
    if args.dash_export:
    if args.dash_export and DASH_AVAILABLE and app is not None:
        try:
            import importlib
            dash_mod = importlib.import_module('dash')
            if hasattr(dash_mod, 'export'):
                dash_path = os.path.join(args.outdir, "btc_temporal_dashboard.html")
                dash_mod.export(app, dash_path)
                print(f"Exported full interactive dashboard to {dash_path}")
            else:
                print("Dash export not available in this Dash version.")
        except Exception as e:
            print(f"Dash export unavailable or failed: {e}")
