-- Fee Overpayment Patterns Analysis
-- Identify transactions paying significantly more than median fee in the same block

WITH block_fees AS (
  SELECT 
  block_number,
  block_timestamp,
  `hash` AS tx_hash,
  fee / size AS fee_rate_sat_byte,
  fee / 1e8 AS fee_btc,
  size,
  virtual_size
  FROM `bigquery-public-data.crypto_bitcoin.transactions`
  -- Use DATE arithmetic for BigQuery compatibility
  WHERE DATE(block_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL @years YEAR)
    AND fee IS NOT NULL
    AND size > 0
    AND virtual_size > 0
),
block_medians AS (
  SELECT 
    block_number,
    APPROX_QUANTILES(fee_rate_sat_byte, 100)[OFFSET(50)] AS median_fee_rate,
    COUNT(*) AS tx_count
  FROM block_fees
  GROUP BY block_number
  HAVING COUNT(*) >= 2  -- Only blocks with multiple transactions
),
overpayment_analysis AS (
  SELECT 
    bf.block_number,
    bf.block_timestamp,
    FORMAT_TIMESTAMP('%A', bf.block_timestamp) AS day_name,
    EXTRACT(HOUR FROM bf.block_timestamp) AS hour,
    bf.tx_hash,
    bf.fee_rate_sat_byte,
    bf.fee_btc,
    bm.median_fee_rate,
    bf.fee_rate_sat_byte / bm.median_fee_rate AS fee_ratio,
    CASE 
      WHEN bf.fee_rate_sat_byte >= bm.median_fee_rate * 2 THEN true
      ELSE false
    END AS is_overpayment
  FROM block_fees bf
  JOIN block_medians bm ON bf.block_number = bm.block_number
  WHERE bm.median_fee_rate > 0
)
SELECT 
  day_name,
  hour,
  COUNT(*) AS total_transactions,
  COUNTIF(is_overpayment) AS overpayment_transactions,
  SAFE_DIVIDE(COUNTIF(is_overpayment), COUNT(*)) * 100 AS overpayment_percentage,
  AVG(fee_ratio) AS avg_fee_ratio,
  AVG(CASE WHEN is_overpayment THEN fee_ratio END) AS avg_overpayment_ratio,
  SUM(CASE WHEN is_overpayment THEN fee_btc END) AS total_overpayment_btc,
  AVG(median_fee_rate) AS avg_median_fee_rate
FROM overpayment_analysis
GROUP BY day_name, hour
ORDER BY day_name, hour
