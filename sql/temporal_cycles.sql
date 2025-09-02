-- SQL: Temporal cycles in Bitcoin blockspace
WITH tx_by_hour AS (
  SELECT
    EXTRACT(DAYOFWEEK FROM block_timestamp) AS dow,   -- 1=Sun … 7=Sat
    EXTRACT(HOUR FROM block_timestamp) AS hour_of_day,
    COUNT(1) AS tx_count,
    SAFE_DIVIDE(SUM(fee), SUM(size)) * 1000 AS avg_fee_per_kb
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE block_timestamp >= "2021-01-01"
  GROUP BY dow, hour_of_day
)
SELECT
  dow,
  hour_of_day,
  tx_count,
  avg_fee_per_kb
FROM tx_by_hour
ORDER BY dow, hour_of_day;
