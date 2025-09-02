import os, math, numpy as np, pandas as pd, matplotlib.pyplot as plt
try:
    from scipy import stats; SCIPY=True
except: SCIPY=False

def find_price_columns(df):
    cols={c.lower():c for c in df.columns}
    d=next((cols[k] for k in ["date","timestamp","time","datetime"] if k in cols), df.columns[0])
    c=next((cols[k] for k in ["close","adj close","price","close_usd","btc_close","btc_usd"] if k in cols),
           next((col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])), df.columns[1]))
    return d,c

def load_prices_or_demo():
    p="data/external/btcusd_daily.csv"
    if os.path.exists(p):
        df=pd.read_csv(p); d,c=find_price_columns(df)
        df[d]=pd.to_datetime(df[d], utc=True, errors="coerce").dt.tz_localize(None)
    df=df[[d,c]].dropna().rename(columns={d:"date",c:"close"}).sort_values("date").set_index("date")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.asfreq("D").ffill()
    # demo
    np.random.seed(11); N=365*5
    dates=pd.date_range("2020-01-01", periods=N, freq="D")
    rets=np.random.normal(0.0002,0.04,size=N)
    return pd.DataFrame({"close":15000*np.exp(np.cumsum(rets))}, index=dates)

def daily_log(df): return np.log(df["close"]/df["close"].shift(1)).dropna()
def fri_fri(df):
    f=df[df.index.weekday==4]["close"]
    return f.pct_change().dropna()
def fri_mon(df):
    m=df[df.index.weekday==0]["close"]; out=[]
    for d in m.index:
        pf=d-pd.Timedelta(days=3)
        if pf in df.index: out.append(np.log(df.loc[d,"close"]/df.loc[pf,"close"]))
    return pd.Series(out, name="fri_to_mon_logret")
def other_daily(df): return daily_log(df)[daily_log(df).index.weekday!=0].rename("other_daily_logret")
def share_pos(x): x=pd.Series(x).dropna(); return float((x>0).mean()) if len(x) else float("nan")
def cohen_d(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)<2 or len(y)<2: return float("nan")
    s=np.sqrt(((len(x)-1)*x.var(ddof=1)+(len(y)-1)*y.var(ddof=1))/(len(x)+len(y)-2))
    return (x.mean()-y.mean())/s if s else float("nan")
def cliffs_delta(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)==0 or len(y)==0: return float("nan")
    if SCIPY:
        Ug=stats.mannwhitneyu(x,y,alternative="greater").statistic
        Ul=stats.mannwhitneyu(x,y,alternative="less").statistic
        return float((Ug-Ul)/(len(x)*len(y)))
    return float("nan")

df=load_prices_or_demo(); df=df.asfreq("D").ffill()
ff=fri_fri(df); fm=fri_mon(df); od=other_daily(df)

# Save data
ff.to_frame("fri_to_fri_return").to_csv("data/external/weekly_fri_to_fri_returns.csv", index_label="friday_date")
pd.DataFrame({"type":["Fri→Mon"]*len(fm)+["Other daily"]*len(od),
              "log_return":pd.concat([fm,od],axis=0).values}).to_csv("data/external/weekend_gap_vs_other_daily.csv", index=False)

# Weekly histogram
plt.figure(figsize=(7,5))
plt.hist(ff.values, bins=50, alpha=0.85)
plt.title("Fri→Fri Weekly Returns — Histogram")
plt.xlabel("Arithmetic weekly return"); plt.ylabel("Frequency")
txt=f"N={len(ff)} | mean={ff.mean():.4f} | median={ff.median():.4f} | %>0={100*share_pos(ff):.1f}%"
plt.figtext(0.5,-0.06,txt,ha="center",va="top"); plt.tight_layout()
plt.savefig("data/external/weekly_fri_to_fri_hist.png", bbox_inches="tight", dpi=180); plt.close()

# Weekend gap violin
plt.figure(figsize=(7,5))
plt.violinplot([fm.values, od.values], showmeans=True, showmedians=True)
plt.title("Weekend Gap (Fri→Mon log return) vs Other Daily Log Returns")
plt.ylabel("Log return"); plt.xticks([1,2],["Fri→Mon","Other daily"])
p = stats.mannwhitneyu(fm, od, alternative="two-sided").pvalue if SCIPY and len(fm)>0 and len(od)>0 else float("nan")
cap=f"N(F→M)={len(fm)}, N(other)={len(od)} | MWU p={p:.3g} | Cliff's δ={cliffs_delta(fm,od):.3f} | Cohen's d={cohen_d(fm,od):.3f}"
plt.figtext(0.5,-0.06,cap,ha="center",va="top"); plt.tight_layout()
plt.savefig("data/external/weekend_gap_violin.png", bbox_inches="tight", dpi=180); plt.close()
