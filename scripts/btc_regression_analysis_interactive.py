import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.formula.api as smf
from scipy import stats
from pathlib import Path

INFILE = "data/external/btcusd_daily.csv"
OUTDIR = Path("data/figs"); OUTDIR.mkdir(parents=True, exist_ok=True)
CSV_OUT = OUTDIR / "btc_regression_coeffs_table.csv"
HTML_OUT = OUTDIR / "btc_regression_coeffs_interactive.html"

# Load data
_df = pd.read_csv(INFILE, parse_dates=["date"])
_df = _df.sort_values("date").reset_index(drop=True)
for col in ["open", "high", "low", "close", "volume"]:
    _df[col] = pd.to_numeric(_df[col], errors="coerce")
_df = _df.dropna().copy()
_df["returns"] = _df["close"].pct_change() * 100
_df = _df.dropna().copy()
_df["dow"] = _df["date"].dt.dayofweek

# Time periods
periods = [
    ("All Time", _df.index >= 0),
    ("5 Years", _df["date"] >= _df["date"].max() - pd.Timedelta(days=365*5)),
    ("2 Years", _df["date"] >= _df["date"].max() - pd.Timedelta(days=365*2)),
    ("1 Year", _df["date"] >= _df["date"].max() - pd.Timedelta(days=365)),
    ("6 Months", _df["date"] >= _df["date"].max() - pd.Timedelta(days=180)),
]
dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


# Collect regression and ANOVA results
rows = []
anova_rows = []
for pname, mask in periods:
    df = _df[mask].copy()
    # Prepare groups for ANOVA
    dow_groups = [df[df['dow'] == i]['returns'].values for i in range(7)]
    min_samples = min(len(g) for g in dow_groups)
    if min_samples < 10:
        continue
    # ANOVA
    f_stat, p_value = stats.f_oneway(*dow_groups)
    group_means = [np.mean(g) for g in dow_groups]
    grand_mean = df['returns'].mean()
    ss_between = sum(len(g) * (mean - grand_mean)**2 for g, mean in zip(dow_groups, group_means))
    ss_total = sum((df['returns'] - grand_mean)**2)
    eta_squared = ss_between / ss_total if ss_total > 0 else np.nan
    # Kruskal-Wallis
    kw_stat, kw_p = stats.kruskal(*dow_groups)
    # Regression
    model = smf.ols("returns ~ C(dow, Treatment(0))", data=df)
    res = model.fit(cov_type='HAC', cov_kwds={'maxlags': 5})
    # Store ANOVA/global results
    anova_rows.append({
        "Period": pname,
        "N": len(df),
        "ANOVA_F": f_stat,
        "ANOVA_p": p_value,
        "Eta_squared": eta_squared,
        "KW_H": kw_stat,
        "KW_p": kw_p,
        "R_squared": res.rsquared,
        "Reg_F": res.fvalue,
        "Reg_F_p": res.f_pvalue
    })
    # Store regression coefficients
    for i in range(1, 7):
        coef_name = f'C(dow, Treatment(0))[T.{i}]'
        if coef_name in res.params:
            rows.append({
                "Period": pname,
                "Day": dow_names[i],
                "Coefficient": res.params[coef_name],
                "SE": res.bse[coef_name],
                "P_value": res.pvalues[coef_name],
                "Significant": res.pvalues[coef_name] < 0.05
            })

# Save regression table
coef_df = pd.DataFrame(rows)
coef_df.to_csv(CSV_OUT, index=False)
print(f"Saved: {CSV_OUT}")
# Save ANOVA/global table
anova_df = pd.DataFrame(anova_rows)
anova_csv = OUTDIR / "btc_anova_summary_table.csv"
anova_df.to_csv(anova_csv, index=False)
print(f"Saved: {anova_csv}")

# Interactive Plotly figure for regression coefficients
fig = go.Figure()
period_labels = [p[0] for p in periods]

# Consistent colors per weekday (Tue→Sun)
day_colors = {
    'Tue': '#1f77b4',
    'Wed': '#ff7f0e',
    'Thu': '#2ca02c',
    'Fri': '#d62728',
    'Sat': '#9467bd',
    'Sun': '#8c564b',
}

for day in dow_names[1:]:
    ddf = coef_df[coef_df["Day"] == day]
    if len(ddf) > 0:
        color = day_colors.get(day, '#4C78A8')
        # Ensure period order is respected
        ddf = ddf.copy()
        ddf["Period"] = pd.Categorical(ddf["Period"], categories=period_labels, ordered=True)
        ddf = ddf.sort_values("Period")
        fig.add_trace(go.Scatter(
            x=ddf["Period"],
            y=ddf["Coefficient"],
            error_y=dict(type="data", array=1.96*ddf["SE"], visible=True),
            mode="lines+markers",
            name=day,
            marker=dict(size=9, color=color),
            line=dict(width=2, color=color),
            text=[f"p={p:.3f}" + ("*" if sig else "") for p, sig in zip(ddf["P_value"], ddf["Significant"])],
            hovertemplate=f"{day}: Coef=%{{y:.3f}}%<br>95% CI ±%{{error_y.array:.3f}}<br>%{{text}}<extra></extra>"
        ))
fig.add_hline(y=0, line_dash="dash", line_color="#888888")
fig.update_layout(
    title="Weekday dummy coefficients (HAC SE, baseline = Monday) across time windows",
    xaxis_title="Period",
    yaxis_title="Coefficient vs Monday (%)",
    template="plotly_white",
    legend_title="Day of Week",
    font=dict(family="Open Sans, Arial", size=15),
    height=540,
    width=950,
    margin=dict(t=60, b=60, l=70, r=30)
)
fig.update_xaxes(categoryorder='array', categoryarray=period_labels)
fig.write_html(str(HTML_OUT), include_plotlyjs="cdn", full_html=True)
print(f"Saved: {HTML_OUT}")

# Interactive summary table for ANOVA/global results
import plotly.io as pio
anova_table_fig = go.Figure(data=[go.Table(
    header=dict(values=["Period", "N", "ANOVA F", "ANOVA p", "Eta²", "KW H", "KW p", "R²", "Reg F", "Reg F p"],
                fill_color="#4C78A8", font=dict(color="white", size=14), align="center"),
    cells=dict(values=[anova_df[c] for c in ["Period", "N", "ANOVA_F", "ANOVA_p", "Eta_squared", "KW_H", "KW_p", "R_squared", "Reg_F", "Reg_F_p"]],
               fill_color="#F3F3F3", align="center", font=dict(size=13)))
])
anova_table_fig.update_layout(
    title="ANOVA & Regression Summary Across Time Periods",
    height=480,
    width=1100,
    margin=dict(t=60, b=40, l=30, r=30)
)
anova_html = OUTDIR / "btc_anova_summary_interactive.html"
pio.write_html(anova_table_fig, file=str(anova_html), include_plotlyjs="cdn", full_html=True)
print(f"Saved: {anova_html}")
