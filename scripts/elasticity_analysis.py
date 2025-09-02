
# Elasticity analysis: run query, save results, analyze, and visualize
from pandas_gbq import read_gbq
import polars as pl
import statsmodels.api as sm
import matplotlib.pyplot as plt
import os

query = """
WITH tx_by_hour AS (
	SELECT
		TIMESTAMP_TRUNC(block_timestamp, HOUR) AS hour_utc,
		COUNT(1) AS tx_count,
		SUM(fee) AS total_fee_sats,
		SUM(size) AS total_size_bytes,
		SAFE_DIVIDE(SUM(fee), SUM(size)) AS avg_fee_per_byte,
		SAFE_DIVIDE(SUM(fee), SUM(size)) * 1000 AS avg_fee_per_kb
	FROM
		`bigquery-public-data.crypto_bitcoin.transactions`
	WHERE
		block_timestamp BETWEEN '2023-05-01' AND '2023-05-08'
	GROUP BY hour_utc
)

SELECT
	hour_utc,
	EXTRACT(DAYOFWEEK FROM hour_utc) AS dow_utc,
	EXTRACT(HOUR FROM hour_utc) AS hour_of_day,
	tx_count,
	avg_fee_per_byte,
	avg_fee_per_kb,
	LEAD(tx_count, 10) OVER (ORDER BY hour_utc) AS tx_count_next_10
FROM tx_by_hour
ORDER BY hour_utc;
"""

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/figs", exist_ok=True)

# Run query and save to CSV/Parquet
df = read_gbq(query, project_id="elite-outpost-458213-u7")
df.to_csv("data/elasticity.csv", index=False)
df.to_parquet("data/raw/elasticity.parquet", index=False)

# Load the data
df_pl = pl.read_csv("data/elasticity.csv").to_pandas()

# Prepare the data for regression
X = sm.add_constant(df_pl["avg_fee_per_kb"])
y = df_pl["tx_count_next_10"]

# Perform OLS regression
ols = sm.OLS(y, X, missing="drop").fit()
print(ols.summary())

# Visualization
plt.figure(figsize=(10, 6))
plt.scatter(df_pl["avg_fee_per_kb"], df_pl["tx_count_next_10"], alpha=0.5, label="Data Points")
plt.plot(df_pl["avg_fee_per_kb"], ols.predict(X), color="red", label="Regression Line")
plt.xlabel("Median Fee per kB")
plt.ylabel("Next 10 Blocks Transaction Count")
plt.title("Elasticity Analysis: Fee vs Transaction Count")
plt.legend()
plt.grid(True)
plt.savefig("data/figs/elasticity_analysis.png")
plt.show()
