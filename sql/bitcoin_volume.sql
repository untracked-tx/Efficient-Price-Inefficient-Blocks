-- Bitcoin Volume Analysis
-- Calculate Bitcoin transaction volume by hour and day for correlation analysis

WITH bitcoin_volume AS (
  SELECT 
    DATE(block_timestamp) AS date,
    FORMAT_TIMESTAMP('%A', block_timestamp) AS day_name,
    EXTRACT(HOUR FROM block_timestamp) AS hour,
    SUM(output_value) / 1e8 AS volume_btc,
    COUNT(*) AS tx_count
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @years YEAR)
    AND output_value IS NOT NULL
  GROUP BY date, day_name, hour
)
SELECT 
  date,
  day_name,
  hour,
  volume_btc,
  tx_count,
  -- Daily totals for correlation analysis
  SUM(volume_btc) OVER (PARTITION BY date) AS daily_volume_btc,
  SUM(tx_count) OVER (PARTITION BY date) AS daily_tx_count
FROM bitcoin_volume
ORDER BY date, hour
