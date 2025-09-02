-- SQL script to extract data for elasticity test
WITH per_block AS (
  SELECT
    block_id,
    block_timestamp,
    AVG(avg_fee_per_kb) AS avg_fee_per_kb,
    SUM(n_tx) AS tx_count
  FROM `bigquery-public-data.crypto_bitcoin.blocks`
  WHERE block_timestamp BETWEEN '2023-05-01' AND '2023-05-08'
  GROUP BY block_id, block_timestamp
)
SELECT
  block_timestamp,
  avg_fee_per_kb,
  tx_count,
  LEAD(tx_count, 10) OVER (ORDER BY block_timestamp) AS tx_count_next_10
FROM per_block
ORDER BY block_timestamp;
