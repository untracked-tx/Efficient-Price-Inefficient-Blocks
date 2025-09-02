-- Large Transaction Timing Analysis
-- Find transactions with large output values and analyze their timing patterns
-- Parameters: years (default 3), min_btc (default 100)

WITH large_txs AS (
  SELECT
    hash,
    block_timestamp,
    FORMAT_TIMESTAMP('%A', block_timestamp) AS day_name,
    EXTRACT(HOUR FROM block_timestamp) AS hour,
    output_value / 1e8 AS output_btc
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE output_value > @min_btc * 1e8
    AND block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @years YEAR)
    AND output_value IS NOT NULL
)
SELECT 
  day_name,
  hour,
  COUNT(*) AS tx_count,
  SUM(output_btc) AS total_btc,
  AVG(output_btc) AS avg_btc,
  MIN(output_btc) AS min_btc,
  MAX(output_btc) AS max_btc
FROM large_txs
GROUP BY day_name, hour
ORDER BY day_name, hour
