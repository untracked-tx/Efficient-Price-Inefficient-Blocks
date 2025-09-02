-- Large Transaction Timing Analysis
-- Find when large transactions (>= threshold BTC) occur by weekday and hour
-- Aggregated data ready for heatmap visualization

WITH large_transactions AS (
  SELECT
    FORMAT_TIMESTAMP('%A', block_timestamp) AS day_name,
    EXTRACT(HOUR FROM block_timestamp) AS hour,
    EXTRACT(DAYOFWEEK FROM block_timestamp) AS day_of_week,
    output_value / 1e8 AS btc_amount,
    block_timestamp,
    hash AS tx_hash
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE output_value >= 100 * 1e8  -- 100 BTC threshold
    AND block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 YEAR)  -- Last 3 years
    AND NOT is_coinbase  -- Exclude coinbase transactions
)
SELECT 
  day_name,
  hour,
  day_of_week,
  COUNT(*) AS tx_count,
  AVG(btc_amount) AS avg_btc_amount,
  MIN(btc_amount) AS min_btc_amount,
  MAX(btc_amount) AS max_btc_amount,
  PERCENTILE_CONT(btc_amount, 0.5) OVER (PARTITION BY day_name, hour) AS median_btc_amount
FROM large_transactions
GROUP BY day_name, hour, day_of_week
ORDER BY day_of_week, hour
