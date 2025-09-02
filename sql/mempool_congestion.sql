-- Mempool Congestion Heatmap
-- Note: BigQuery public Bitcoin dataset doesn't have mempool tables
-- This query uses transaction fees as a proxy for mempool congestion
-- Higher fees typically indicate mempool congestion

WITH fee_analysis AS (
  SELECT
    FORMAT_TIMESTAMP('%A', block_timestamp) AS day_name,
    EXTRACT(HOUR FROM block_timestamp) AS hour,
    EXTRACT(DAYOFWEEK FROM block_timestamp) AS day_of_week,
    fee,
    virtual_size,
    -- Calculate fee rate (sat/vB)
    CASE 
      WHEN virtual_size > 0 THEN fee * 1e8 / virtual_size 
      ELSE 0 
    END AS fee_rate_sat_vb,
    block_timestamp
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  WHERE block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 YEAR)
    AND NOT is_coinbase
    AND virtual_size > 0
    AND fee > 0
)
SELECT 
  day_name,
  hour,
  day_of_week,
  COUNT(*) AS tx_count,
  AVG(fee_rate_sat_vb) AS avg_fee_rate,
  PERCENTILE_CONT(fee_rate_sat_vb, 0.5) OVER (PARTITION BY day_name, hour) AS median_fee_rate,
  PERCENTILE_CONT(fee_rate_sat_vb, 0.75) OVER (PARTITION BY day_name, hour) AS p75_fee_rate,
  PERCENTILE_CONT(fee_rate_sat_vb, 0.95) OVER (PARTITION BY day_name, hour) AS p95_fee_rate,
  MIN(fee_rate_sat_vb) AS min_fee_rate,
  MAX(fee_rate_sat_vb) AS max_fee_rate
FROM fee_analysis
WHERE fee_rate_sat_vb BETWEEN 1 AND 10000  -- Filter extreme outliers
GROUP BY day_name, hour, day_of_week
ORDER BY day_of_week, hour
