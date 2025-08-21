from pandas_gbq import read_gbq
import polars as pl
import plotly.express as px
import numpy as np
import os

# HODL Waves: Stacked area chart of UTXO age distribution
# This query estimates the age of each UTXO and groups by age buckets
query = """
WITH utxo_ages AS (
  SELECT
    outputs.value AS value,
    DATE_DIFF(CURRENT_DATE(), DATE(outputs.block_timestamp), DAY) AS age_days
  FROM `bigquery-public-data.crypto_bitcoin.outputs` outputs
  LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` inputs
    ON outputs.transaction_hash = inputs.spent_transaction_hash
    AND outputs.index = inputs.spent_output_index
  WHERE inputs.spent_transaction_hash IS NULL -- unspent outputs only
)
SELECT
  CASE
    WHEN age_days < 30 THEN '<1m'
    WHEN age_days < 90 THEN '1-3m'
    WHEN age_days < 180 THEN '3-6m'
    WHEN age_days < 365 THEN '6-12m'
    WHEN age_days < 730 THEN '1-2y'
    WHEN age_days < 1825 THEN '2-5y'
    ELSE '5y+'
  END AS age_bucket,
  SUM(value) AS total_value
FROM utxo_ages
GROUP BY age_bucket
ORDER BY age_bucket
"""

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/figs", exist_ok=True)

df = read_gbq(query, project_id="elite-outpost-458213-u7")
# Save raw data as CSV and Parquet
df.to_csv("hodl_waves.csv", index=False)
df.to_parquet("data/raw/hodl_waves.parquet", index=False)

# Calculate percent of total supply in each bucket
supply = df['total_value'].sum()
df['pct_supply'] = df['total_value'] / supply * 100

# Plot as stacked bar (single snapshot)
fig = px.bar(
  df,
  x='age_bucket',
  y='pct_supply',
  labels={'pct_supply': '% of Supply', 'age_bucket': 'UTXO Age Bucket'},
  title='Bitcoin HODL Waves (Current UTXO Age Distribution)'
)
fig.update_layout(
  template="simple_white",
  font=dict(family="Helvetica, Arial, sans-serif", size=14),
  margin=dict(l=60, r=20, t=60, b=50),
  yaxis_title='% of Supply',
  xaxis_title='UTXO Age Bucket'
)

# Save HTML and PNG to /data/figs/
fig.write_html("data/figs/hodl_waves.html")
fig.write_image("data/figs/hodl_waves.png")
