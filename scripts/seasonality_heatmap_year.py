from pandas_gbq import read_gbq
import polars as pl
import plotly.express as px
import os

query = """
WITH tx_fees AS (
  SELECT
    b.timestamp AS block_time,
    t.fee / NULLIF(t.size, 0) AS fee_per_byte
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
  JOIN `bigquery-public-data.crypto_bitcoin.blocks` b
    ON t.block_hash = b.hash
  WHERE b.timestamp BETWEEN '2024-08-01' AND '2025-08-01'
    AND t.fee IS NOT NULL AND t.size IS NOT NULL AND t.size > 0
)
SELECT
  EXTRACT(DAYOFWEEK FROM block_time) AS dow,
  EXTRACT(HOUR FROM block_time) AS hod,
  APPROX_QUANTILES(fee_per_byte, 100)[OFFSET(50)] AS p50_fee
FROM tx_fees
GROUP BY dow, hod
ORDER BY dow, hod
"""

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/figs", exist_ok=True)

df = read_gbq(query, project_id="elite-outpost-458213-u7")
df.to_csv("seasonality_year.csv", index=False)
df.to_parquet("data/raw/seasonality_year.parquet", index=False)

df_pl = pl.read_csv("seasonality_year.csv")
pivot = df_pl.pivot(
    values="p50_fee",
    index="dow",
    on="hod"
).to_pandas()

fig = px.imshow(
  pivot,
  labels=dict(x="Hour of Day", y="Day of Week", color="Median Fee (sat/vB)"),
  x=pivot.columns,
  y=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
)
fig.update_layout(
  title="BTC Fee Seasonality (Past Year)",
  template="simple_white",
  font=dict(family="Helvetica, Arial, sans-serif", size=14),
  margin=dict(l=60, r=20, t=60, b=50),
  coloraxis_colorbar=dict(title="Median Fee (sat/vB)")
)
fig.update_coloraxes(colorscale="Viridis")

fig.write_html("data/figs/seasonality_heatmap_year.html")
fig.write_image("data/figs/seasonality_heatmap_year.png", scale=2, width=1400, height=700)
fig.show()
