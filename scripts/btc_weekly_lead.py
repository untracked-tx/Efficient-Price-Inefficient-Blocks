#!/usr/bin/env python3
"""
BTC Weekday Lead Dashboard
- Input: daily CSV with columns: date,open,high,low,close,volume  (UTC)
- Output: one polished HTML with tabs + timeframe switcher you can embed in Quarto.

Figures per timeframe:
  1) Weekday distributions (violins of log returns)
  2) Up-day rate by weekday (% positive close-to-close)
  3) Weekend gap vs Weekday overnight (Fri close→Mon open vs typical overnight)
  4) Rolling 2-yr t-stat (Monday vs rest) with ±2 reference
  5) Year × Weekday heatmap (mean log return)

Customize TIMEFRAMES below as you like.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from scipy import stats
from datetime import datetime, timedelta

# =================== CONFIG ===================
INFILE  = "data/external/btcusd_daily.csv"
OUTFILE = "data/figs/btc_weekday_lead_dashboard.html"
ROLLING_WINDOW_DAYS = 730  # ~2 years
TEMPLATE = "plotly_white"
FONT_FAMILY = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

# Define timeframes (label -> (start, end) or function(df)->mask)
def _now(df): return df["date"].max().normalize()

TIMEFRAMES = [
    ("All",               lambda df: (df["date"] >= df["date"].min()) & (df["date"] <= df["date"].max())),
    ("2014–2016",         lambda df: (df["date"] <  pd.Timestamp("2017-01-01"))),
    ("2017–2019",         lambda df: (df["date"] >= pd.Timestamp("2017-01-01")) & (df["date"] < pd.Timestamp("2020-01-01"))),
    ("2020–2022",         lambda df: (df["date"] >= pd.Timestamp("2020-01-01")) & (df["date"] < pd.Timestamp("2023-01-01"))),
    ("2023–Now",          lambda df: (df["date"] >= pd.Timestamp("2023-01-01"))),
    ("Last 1Y",           lambda df: (df["date"] >= (_now(df) - pd.Timedelta(days=365)))),
    ("Last 2Y",           lambda df: (df["date"] >= (_now(df) - pd.Timedelta(days=2*365)))),
]
# ==============================================

# ---------- Helpers ----------
def cliffs_delta_from_mwu(x, y):
    """Compute Cliff's delta from Mann–Whitney U (fast, handles ties via SciPy)."""
    if len(x) == 0 or len(y) == 0:
        return np.nan
    u = stats.mannwhitneyu(x, y, alternative="two-sided", method="auto").statistic
    n, m = len(x), len(y)
    # With ties, SciPy's U ~ count(x>y) + 0.5*ties; formula still ok as effect estimate
    return 2 * (u / (n * m)) - 1

def rolling_monday_tstat(df, window_days=730):
    """Compute rolling Welch t-stat (Monday vs others) over a calendar-day window."""
    out_dates, out_t = [], []
    arr = df[["date", "ret", "dow"]].to_numpy(object)
    # Pointer-based rolling window using date thresholds
    left = 0
    for right in range(len(arr)):
        # expand window to include current date
        end_date = arr[right, 0]
        start_date = end_date - pd.Timedelta(days=window_days)
        # move left bound
        while left < right and arr[left, 0] < start_date:
            left += 1
        w = arr[left:right+1]
        mon = np.array([r for (d, r, dow) in w if dow == "Monday"], dtype=float)
        rest = np.array([r for (d, r, dow) in w if dow != "Monday"], dtype=float)
        if len(mon) >= 8 and len(rest) >= 40:
            t, _ = stats.ttest_ind(mon, rest, equal_var=False)
            out_dates.append(end_date)
            out_t.append(t)
    return pd.DataFrame({"date": out_dates, "tstat": out_t})

def weekend_vs_overnight(df):
    """Return dataframe with 'type' in {'Weekend gap','Weekday overnight'} and 'ret' for open_{t+1}/close_t."""
    rows = []
    for i in range(len(df) - 1):
        d0, d1 = df.iloc[i], df.iloc[i+1]
        r = np.log(d1["open"] / d0["close"])
        if d0["date"].weekday() == 4 and d1["date"].weekday() == 0:
            rows.append({"date": d1["date"], "type": "Weekend gap", "ret": r})
        else:
            rows.append({"date": d1["date"], "type": "Weekday overnight", "ret": r})
    return pd.DataFrame(rows)

def nice_title(s):  # small helper to keep titles tidy
    return s.replace("log ", "log ").replace("Weekday", "Weekday")

# ---------- Load & prepare data ----------
df = pd.read_csv(INFILE, parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)
for c in ["open","high","low","close","volume"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=["open","close"]).copy()

# Returns and keys
df["ret"] = np.log(df["close"] / df["close"].shift(1))
df = df.dropna(subset=["ret"]).copy()
order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
df["dow"] = pd.Categorical(df["date"].dt.day_name(), categories=order, ordered=True)
df["year"] = df["date"].dt.year

# Precompute once
overnight_full = weekend_vs_overnight(df)

# ---------- Figure builders (per timeframe) ----------
def fig_violins(dff, tf_label):
    fig = px.violin(
        dff, x="dow", y="ret", box=True, points="outliers",
        category_orders={"dow": order}, template=TEMPLATE, color="dow",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(
        title=nice_title(f"BTC daily log returns by weekday — {tf_label}"),
        xaxis_title="", yaxis_title="Daily log return",
        showlegend=False, font=dict(family=FONT_FAMILY), height=520, margin=dict(t=60, l=60, r=30, b=60)
    )
    return fig

def fig_upday_rate(dff, tf_label):
    rate = dff.assign(up=(dff["ret"]>0).astype(int)).groupby("dow", observed=False)["up"].mean().reindex(order)
    fig = px.bar(
        rate.reset_index().rename(columns={"up":"Up-day rate"}),
        x="dow", y="Up-day rate", category_orders={"dow": order},
        template=TEMPLATE, color="dow", color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(
        title=f"% days with positive return (by weekday) — {tf_label}",
        xaxis_title="", yaxis_title="Share of up days",
        yaxis_tickformat=".0%", showlegend=False, font=dict(family=FONT_FAMILY),
        height=480, margin=dict(t=60, l=60, r=30, b=60)
    )
    return fig

def fig_weekend_gap(dff, tf_label):
    ov = overnight_full.loc[(overnight_full["date"]>=dff["date"].min()) & (overnight_full["date"]<=dff["date"].max())].copy()
    # stats
    wend = ov.loc[ov["type"]=="Weekend gap","ret"].values
    wday = ov.loc[ov["type"]=="Weekday overnight","ret"].values
    p = stats.mannwhitneyu(wend, wday, alternative="two-sided", method="auto").pvalue if len(wend)>0 and len(wday)>0 else np.nan
    delta = cliffs_delta_from_mwu(wend, wday) if len(wend)>0 and len(wday)>0 else np.nan

    fig = px.violin(ov, x="type", y="ret", color="type", box=True, points="outliers",
                    template=TEMPLATE, color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(
        title=f"Weekend gap vs typical overnight (log returns) — {tf_label}",
        xaxis_title="", yaxis_title="Overnight log return",
        showlegend=False, font=dict(family=FONT_FAMILY),
        height=520, margin=dict(t=60, l=60, r=30, b=60),
        annotations=[dict(
            text=f"Mann–Whitney p = {p:.3f} • Cliff’s δ = {delta:+.2f}" if np.isfinite(p) else "Insufficient data",
            x=0.5, y=1.09, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#444")
        )]
    )
    return fig

def fig_rolling_tstat(dff, tf_label):
    r = rolling_monday_tstat(dff, window_days=ROLLING_WINDOW_DAYS)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=r["date"], y=r["tstat"], mode="lines", name="t-stat"))
    fig.add_hline(y= 2, line_dash="dot", line_color="#999")
    fig.add_hline(y=-2, line_dash="dot", line_color="#999")
    fig.update_layout(
        title=f"Rolling Monday vs rest (Welch t-stat, {ROLLING_WINDOW_DAYS}-day window) — {tf_label}",
        xaxis_title="", yaxis_title="t-stat",
        template=TEMPLATE, font=dict(family=FONT_FAMILY),
        height=420, margin=dict(t=60, l=60, r=30, b=60)
    )
    return fig

def fig_heatmap(dff, tf_label):
    m = dff.groupby(["year","dow"], observed=False)["ret"].mean().reset_index()
    fig = px.imshow(
        m.pivot(index="year", columns="dow", values="ret").reindex(columns=order),
        color_continuous_scale="RdBu", origin="lower", aspect="auto", zmin=-m["ret"].abs().max(), zmax=m["ret"].abs().max()
    )
    fig.update_layout(
        title=f"Mean daily log return — Year × Weekday — {tf_label}",
        xaxis_title="", yaxis_title="Year", template=TEMPLATE, font=dict(family=FONT_FAMILY),
        height=520, margin=dict(t=60, l=60, r=30, b=60), coloraxis_colorbar=dict(title="Mean log return")
    )
    return fig

# ---------- Build all figures across timeframes ----------
fragments = []  # list of (tab, tf_label, html_fragment)
tabs = [
    ("violins",      "Weekday distributions"),
    ("upday",        "Up-day %"),
    ("weekend_gap",  "Weekend gap"),
    ("rolling_t",    "Rolling Monday effect"),
    ("heatmap",      "Year × Weekday"),
]

for tf_label, mask_fn in TIMEFRAMES:
    dff = df.loc[mask_fn(df)].copy()
    if len(dff) < 200:
        # skip too-small windows
        continue
    dff["dow"] = pd.Categorical(dff["date"].dt.day_name(), categories=order, ordered=True)
    dff["year"] = dff["date"].dt.year

    figs = {
        "violins":     fig_violins(dff, tf_label),
        "upday":       fig_upday_rate(dff, tf_label),
        "weekend_gap": fig_weekend_gap(dff, tf_label),
        "rolling_t":   fig_rolling_tstat(dff, tf_label),
        "heatmap":     fig_heatmap(dff, tf_label),
    }
    for key, _label in tabs:
        frag = pio.to_html(figs[key], full_html=False, include_plotlyjs=False)
        fragments.append((key, tf_label, frag))

# ---------- Assemble one pretty HTML ----------
CSS = f"""
:root {{
  --bg:#ffffff; --ink:#111; --muted:#666; --brand:#2563eb;
}}
* {{ box-sizing:border-box; }}
body {{
  margin: 0 auto; max-width: 1100px; padding: 28px 18px 40px; background: var(--bg);
  color: var(--ink); font-family: {FONT_FAMILY};
}}
h1 {{ font-weight: 700; letter-spacing: -0.015em; margin: 0 0 8px; }}
.subtitle {{ color: var(--muted); margin-bottom: 16px; }}
.controls {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin: 14px 0 12px; }}
.select, .tab {{
  border:1px solid #e5e7eb; background:#f9fafb; padding:8px 12px; border-radius:10px; cursor:pointer;
}}
.select:focus-visible, .tab:focus-visible {{ outline: 2px solid var(--brand); }}
.tabs {{ display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0 14px; }}
.tab[aria-selected="true"] {{ background:#eef2ff; border-color:#c7d2fe; color:#1e40af; }}
.panel {{ display:none; }}
.panel.active {{ display:block; }}
footer {{ margin-top: 18px; color:var(--muted); font-size: 13px; }}
hr {{ border:0; border-top:1px solid #eee; margin: 20px 0; }}
"""

JS = """
(function(){
  const tfSel = document.getElementById('tf');
  const tabs = Array.from(document.querySelectorAll('.tab'));
  function sync(){
    const tab = document.querySelector('.tab[aria-selected="true"]').dataset.tab;
    const tf  = tfSel.value;
    document.querySelectorAll('.panel').forEach(p => {
      p.classList.toggle('active', p.dataset.tab===tab && p.dataset.tf===tf);
    });
  }
  // init tab click
  tabs.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      tabs.forEach(b=>b.setAttribute('aria-selected', 'false'));
      btn.setAttribute('aria-selected', 'true');
      sync();
    });
  });
  tfSel.addEventListener('change', sync);
  // initial state
  if(!document.querySelector('.tab[aria-selected="true"]')) {
    (tabs[0]||{}).setAttribute && tabs[0].setAttribute('aria-selected','true');
  }
  sync();
})();
"""

# Build the controls
tf_options = "".join(f'<option value="{label}">{label}</option>' for (label, _) in TIMEFRAMES)

# Group fragments into panels
panels_html = []
for tab_key, tab_label in tabs:
    for tf_label, _ in TIMEFRAMES:
        # find fragment
        frag = next((h for (k, t, h) in fragments if k==tab_key and t==tf_label), None)
        if frag is None: 
            continue
        panels_html.append(
            f'<div class="panel" data-tab="{tab_key}" data-tf="{tf_label}">{frag}</div>'
        )

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BTC Weekday Effects — Lead Graphic</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>{CSS}</style>
</head>
<body>
  <h1>BTC Day-of-Week Effects</h1>
  <div class="subtitle">Daily <b>log</b> returns from close-to-close (UTC). Explore by timeframe and view.</div>

  <div class="controls">
    <label for="tf" style="font-weight:600;">Timeframe</label>
    <select id="tf" class="select">
      {tf_options}
    </select>
    <div class="tabs" role="tablist" aria-label="Views">
      <button class="tab" role="tab" aria-selected="true"  data-tab="violins">Weekday distributions</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="upday">Up-day %</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="weekend_gap">Weekend gap</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="rolling_t">Rolling Monday effect</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="heatmap">Year × Weekday</button>
    </div>
  </div>

  <div id="panels">
    {''.join(panels_html)}
  </div>

  <footer>
    Methods: daily log return r = ln(Cₜ/Cₜ₋₁); weekdays by UTC; weekend gap = ln(O₍Mon₎/C₍Fri₎).
    Mann–Whitney test + Cliff’s δ for gap vs overnight; rolling Welch t-stat (window {ROLLING_WINDOW_DAYS} days).
  </footer>

  <script>{JS}</script>
</body>
</html>
"""

# Write the HTML
import pathlib
pathlib.Path(OUTFILE).parent.mkdir(parents=True, exist_ok=True)
with open(OUTFILE, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"Saved lead graphic to: {OUTFILE}")
