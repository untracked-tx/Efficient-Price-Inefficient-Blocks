from pandas_gbq import read_gbq
import polars as pl
import plotly.express as px

# Block Fullness Heatmap
query = """
WITH block_fullness AS (
  SELECT
    TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
    AVG(weight / 4000000.0) AS avg_fullness,
    COUNT(*) AS n_blocks
  FROM `bigquery-public-data.crypto_bitcoin.blocks`
  WHERE timestamp BETWEEN '2023-01-01' AND '2023-02-01'
  GROUP BY 1
)
SELECT
  EXTRACT(DAYOFWEEK FROM hour) AS dow,
  EXTRACT(HOUR FROM hour) AS hod,
  APPROX_QUANTILES(avg_fullness, 100)[OFFSET(50)] AS p50_fullness
FROM block_fullness
GROUP BY dow, hod
ORDER BY dow, hod
"""

df = read_gbq(query, project_id="elite-outpost-458213-u7")
  df.to_csv("block_fullness.csv", index=False)
  df.to_parquet("data/raw/block_fullness.parquet", index=False)

df_pl = pl.read_csv("block_fullness.csv")
pivot = df_pl.pivot(
    values="p50_fullness",
    index="dow",
    on="hod"
).to_pandas()

fig = px.imshow(
  pivot,
  labels=dict(x="Hour of Day", y="Day of Week", color="Median Block Fullness"),
  x=pivot.columns,
  y=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
)
fig.update_layout(title="BTC Block Fullness Seasonality (Jan 2023 sample)")

# Save HTML and PNG to /data/figs/
fig.write_html("data/figs/block_fullness_heatmap.html")
fig.write_image("data/figs/block_fullness_heatmap.png")
