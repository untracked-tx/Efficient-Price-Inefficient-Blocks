import pandas as pd, numpy as np
import plotly.express as px, plotly.graph_objects as go
import statsmodels.formula.api as smf
from pathlib import Path

INFILE = "data/external/btcusd_daily.csv"
OUTDIR = Path("data/figs"); OUTDIR.mkdir(parents=True, exist_ok=True)

# Load daily and compute returns
df = pd.read_csv(INFILE, parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)
if "close" not in df.columns: raise SystemExit("CSV must have 'close' column.")
df["close"] = pd.to_numeric(df["close"], errors="coerce")
df = df.dropna(subset=["close"]).copy()
df["ret_d"] = np.log(df["close"]).diff()
df = df.dropna(subset=["ret_d"]).copy()

# Weekday/Weekend flags
df["dow_i"] = df["date"].dt.dayofweek  # 0=Mon ... 6=Sun
dow_map = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
df["DOW"] = df["dow_i"].map(dow_map)
df["is_weekend"] = df["dow_i"].isin([5,6]).astype(int)

# ------- Figure A: Monday effect (boxplot by weekday)
figA = px.box(df, x="DOW", y="ret_d",
              title="Bitcoin: Daily Returns by Day of Week (Monday Effect)",
              labels={"ret_d":"Daily log return"})
figA.update_layout(template="plotly_white"); figA.update_yaxes(tickformat=".2%")
figA.write_html(OUTDIR/"daily_monday_effect.html", include_plotlyjs="cdn")

# ------- Figure B: Weekend vs Weekday distribution
dfW = df.copy()
dfW["Group"] = np.where(dfW["is_weekend"]==1, "Weekend (Sat+Sun)", "Weekday (Mon–Fri)")
figB = px.violin(dfW, x="Group", y="ret_d", box=True, points="all",
                 title="Weekend vs Weekday: Daily Return Distribution",
                 labels={"ret_d":"Daily log return"})
figB.update_layout(template="plotly_white"); figB.update_yaxes(tickformat=".2%")
figB.write_html(OUTDIR/"daily_weekend_effect.html", include_plotlyjs="cdn")

# ------- Figure C: Monday = weekend gap (Fri->Mon close-to-close)
# (Simple line: rolling average of Monday returns vs others)
monday = df[df["DOW"]=="Mon"][["date","ret_d"]].assign(group="Mon (Fri→Mon gap)")
others = df[df["DOW"]!="Mon"][["date","ret_d"]].assign(group="Other days")
roll = pd.concat([monday, others]).sort_values("date").copy()
roll["roll_mean"] = roll.groupby("group")["ret_d"].transform(lambda s: s.rolling(60, min_periods=30).mean())

figC = px.line(roll, x="date", y="roll_mean", color="group",
               title="Rolling Mean of Daily Returns: Monday (weekend gap) vs Other Days",
               labels={"roll_mean":"60-day rolling mean (log return)"})
figC.update_layout(template="plotly_white"); figC.update_yaxes(tickformat=".2%")
figC.write_html(OUTDIR/"daily_monday_gap_rolling.html", include_plotlyjs="cdn")

# ------- Figure D: Regression vs Monday (Newey–West SEs)
mod = smf.ols("ret_d ~ C(DOW, Treatment('Mon'))", data=df).fit(cov_type="HAC", cov_kwds={"maxlags":5})
coefs = mod.params.filter(like="C(DOW)")
ses   = mod.bse.filter(like="C(DOW)")
labs  = [lab.split("]")[1] for lab in coefs.index]  # 'Tue','Wed',...
order = ["Tue","Wed","Thu","Fri","Sat","Sun"]
coef_df = (pd.DataFrame({"Weekday": labs, "Coef_vs_Mon": coefs.values, "SE": ses.values})
             .set_index("Weekday").reindex(order).reset_index())
coef_df["up"] = coef_df["Coef_vs_Mon"] + 1.96*coef_df["SE"]
coef_df["dn"] = coef_df["Coef_vs_Mon"] - 1.96*coef_df["SE"]

figD = go.Figure()
figD.add_scatter(x=coef_df["Weekday"], y=coef_df["Coef_vs_Mon"], mode="markers",
                 error_y=dict(type="data", array=1.96*coef_df["SE"], visible=True),
                 name="β (vs Monday)")
figD.add_hline(y=0, line_dash="dot", line_color="gray")
figD.update_layout(title="Weekday Return Differences vs Monday (OLS, Newey–West SEs)",
                   yaxis_title="Avg daily log-return difference", template="plotly_white")
figD.update_yaxes(tickformat=".2%")
figD.write_html(OUTDIR/"daily_dow_regression.html", include_plotlyjs="cdn")

print("Saved:",
      OUTDIR/"daily_monday_effect.html",
      OUTDIR/"daily_weekend_effect.html",
      OUTDIR/"daily_monday_gap_rolling.html",
      OUTDIR/"daily_dow_regression.html")
