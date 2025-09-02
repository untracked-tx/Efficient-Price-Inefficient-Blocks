# Visualize temporal cycles in Bitcoin blockspace
from pandas_gbq import read_gbq
import polars as pl
import plotly.express as px
import os

query = """
WITH tx_by_hour AS (
  SELECT
    EXTRACT(DAYOFWEEK FROM block_timestamp) AS dow,
    EXTRACT(HOUR FROM block_timestamp) AS hour_of_day,
    COUNT(1) AS tx_count,
    SAFE_DIVIDE(SUM(fee), SUM(size)) * 1000 AS avg_fee_per_kb
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE block_timestamp >= '2021-01-01'
  GROUP BY dow, hour_of_day
)
SELECT
  dow,
  hour_of_day,
  tx_count,
  avg_fee_per_kb
FROM tx_by_hour
ORDER BY dow, hour_of_day;
"""

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/figs", exist_ok=True)

# Run query and save to CSV/Parquet
# NOTE: Replace with your project_id
project_id = "elite-outpost-458213-u7"
df = read_gbq(query, project_id=project_id)
df.to_csv("data/temporal_cycles.csv", index=False)
df.to_parquet("data/raw/temporal_cycles.parquet", index=False)

# Load data
import pandas as pd
df_pd = pd.read_csv("data/temporal_cycles.csv")

# Pivot for heatmap
pivot = df_pd.pivot(index="dow", columns="hour_of_day", values="avg_fee_per_kb")

fig = px.imshow(
    pivot,
    labels=dict(x="Hour of Day", y="Day of Week", color="Avg Fee per kB"),
    x=list(range(24)),
    y=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
)
fig.update_layout(
    title="BTC Fee Cycles: Hourly & Weekly Patterns (2021+)",
    template="simple_white",
    font=dict(family="Helvetica, Arial, sans-serif", size=14),
    margin=dict(l=60, r=20, t=60, b=50),
    coloraxis_colorbar=dict(title="Avg Fee per kB")
)
fig.update_coloraxes(colorscale="Plasma")

# Save outputs
fig.write_html("data/figs/temporal_cycles_heatmap.html")
fig.write_image("data/figs/temporal_cycles_heatmap.png", scale=2, width=1400, height=700)
fig.show()
