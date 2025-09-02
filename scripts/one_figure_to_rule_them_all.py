import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

CSV_PATH = "data/external/btcusd_daily.csv"
SAVE_PATH = "data/figs/one_figure_to_rule_them_all.png"

# Load daily price data
_df = pd.read_csv(CSV_PATH, parse_dates=["date"])
_df = _df.sort_values("date").reset_index(drop=True)
if "close" not in _df.columns:
    raise SystemExit("CSV must have 'close' column.")
_df["close"] = pd.to_numeric(_df["close"], errors="coerce")
_df = _df.dropna(subset=["close"]).copy()

# Compute daily percent returns
_df["ret"] = _df["close"].pct_change()
_df = _df.dropna(subset=["ret"]).copy()

# Map weekdays
weekday_num = _df["date"].dt.dayofweek  # 0=Mon ... 6=Sun
weekday_map = {0:"Mon", 1:"Tue", 2:"Wed", 3:"Thu", 4:"Fri", 5:"Sat", 6:"Sun"}
weekday = weekday_num.map(weekday_map)

# Aggregate: mean return and share of "up" days
_grp = pd.DataFrame({
    "weekday": weekday.values,
    "ret": _df["ret"].values
})

stats = _grp.groupby("weekday").agg(
    mean_ret=("ret", "mean"),
    up_share=("ret", lambda x: np.mean(x > 0))
)

# Ensure all weekdays present
desired_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
stats = stats.reindex(desired_order)

# Compute weekend/weekday averages
weekend_avg = stats.loc[["Sat", "Sun"], "mean_ret"].mean()
weekdays_avg = stats.loc[["Mon", "Tue", "Wed", "Thu", "Fri"], "mean_ret"].mean()

# Sort bars for pattern recognition
stats = stats.sort_values("mean_ret")

# Prep plotting data in percent
bar_labels = stats.index.tolist()
bar_heights = stats["mean_ret"].values * 100.0
up_pct = (stats["up_share"].values * 100.0)

# Caption with years
start_year = _df["date"].min().year
end_year = _df["date"].max().year

weekend_pct = weekend_avg * 100.0
weekdays_pct = weekdays_avg * 100.0

caption = (
    f"Average Bitcoin daily return by weekday (UTC close, {start_year}–{end_year}). "
    f"Weekends = {weekend_pct:.2f}%, weekdays = {weekdays_pct:.2f}%. "
    f"Bars = mean return; dots = share of up days."
)

plt.rcParams.update({
    "figure.dpi": 120,
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.labelsize": 13
})
fig, ax = plt.subplots(figsize=(9.5, 5.5))

bar_color = "#4C78A8"
dot_color = "#222222"
text_color = "#222222"

x = np.arange(len(bar_labels))
bars = ax.bar(x, bar_heights, color=bar_color, width=0.72, edgecolor="none")

ax.axhline(0, color="#888888", linewidth=1.0, alpha=0.5)

y_min, y_max = min(0, bar_heights.min()), bar_heights.max()
y_range = y_max - y_min if y_max != y_min else 1.0
dot_offset = 0.02 * y_range
label_offset = 0.01 * y_range

for i, (bx, bh, up) in enumerate(zip(x, bar_heights, up_pct)):
    dot_y = bh + dot_offset
    ax.scatter([bx], [dot_y], s=30, color=dot_color, zorder=3)
    ax.text(bx, dot_y + label_offset, f"{up:.0f}%", ha="center", va="bottom", color=text_color, fontsize=11)

ax.set_xticks(x, bar_labels)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}%"))
ax.set_ylabel("Average daily return (%)")
ax.set_title("Average Bitcoin daily return by weekday")

ax.grid(False)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)
for spine in ["left", "bottom"]:
    ax.spines[spine].set_color("#BBBBBB")
    ax.spines[spine].set_linewidth(0.8)

ann_text = f"Weekends avg {weekend_pct:.2f}%, Weekdays avg {weekdays_pct:.2f}%."
ax.text(0.99, 0.98, ann_text, transform=ax.transAxes, ha="right", va="top", color=text_color, fontsize=12)

fig.subplots_adjust(bottom=0.22, top=0.88, left=0.12, right=0.98)
fig.text(0.5, 0.06, caption, ha="center", va="center", color="#333333", fontsize=11)

plt.tight_layout(rect=[0, 0.12, 1, 0.92])
fig.savefig(SAVE_PATH, dpi=200)
print(f"Saved figure to: {SAVE_PATH}")
