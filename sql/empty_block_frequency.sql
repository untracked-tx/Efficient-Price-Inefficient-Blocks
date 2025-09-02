-- Empty Block Frequency Analysis
-- Find blocks that only contain the coinbase transaction (empty blocks)

WITH block_tx_counts AS (
  SELECT 
    b.number,
    b.timestamp,
    FORMAT_TIMESTAMP('%A', b.timestamp) AS day_name,
    EXTRACT(HOUR FROM b.timestamp) AS hour,
    COALESCE(b.transaction_count, 0) AS tx_count
  FROM `bigquery-public-data.crypto_bitcoin.blocks` b
  WHERE b.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @years YEAR)
)
SELECT 
  day_name,
  hour,
  COUNT(*) AS total_blocks,
  COUNTIF(tx_count <= 1) AS empty_blocks,
  COUNTIF(tx_count > 1) AS non_empty_blocks,
  SAFE_DIVIDE(COUNTIF(tx_count <= 1), COUNT(*)) * 100 AS empty_block_percentage,
  AVG(tx_count) AS avg_tx_count,
  MIN(tx_count) AS min_tx_count,
  MAX(tx_count) AS max_tx_count
FROM block_tx_counts
GROUP BY day_name, hour
ORDER BY day_name, hour
