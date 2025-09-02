-- UTXO Age Movement Analysis
-- Calculate age of UTXOs when spent and analyze by weekday

WITH utxo_spent AS (
  SELECT 
    i.block_timestamp AS spend_time,
    o.block_timestamp AS creation_time,
    i.value / 1e8 AS value_btc,
    FORMAT_TIMESTAMP('%A', i.block_timestamp) AS spend_day_name,
    EXTRACT(HOUR FROM i.block_timestamp) AS spend_hour,
    -- Calculate age in days
    TIMESTAMP_DIFF(i.block_timestamp, o.block_timestamp, HOUR) / 24.0 AS age_days
  FROM `bigquery-public-data.crypto_bitcoin.inputs` i
  JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
    ON i.spent_transaction_hash = o.transaction_hash 
    AND i.spent_output_index = o.index
  WHERE i.block_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @years YEAR)
    AND o.block_timestamp IS NOT NULL
    AND i.block_timestamp > o.block_timestamp  -- Ensure proper ordering
    AND TIMESTAMP_DIFF(i.block_timestamp, o.block_timestamp, HOUR) / 24.0 < 2000  -- Filter unrealistic ages
),
age_buckets AS (
  SELECT 
    *,
    CASE 
      WHEN age_days < 1 THEN '< 1 day'
      WHEN age_days < 7 THEN '1-7 days'
      WHEN age_days < 30 THEN '1-4 weeks'
      WHEN age_days < 90 THEN '1-3 months'
      WHEN age_days < 180 THEN '3-6 months'
      WHEN age_days < 365 THEN '6-12 months'
      WHEN age_days < 730 THEN '1-2 years'
      WHEN age_days < 1095 THEN '2-3 years'
      WHEN age_days < 1460 THEN '3-4 years'
      ELSE '4+ years'
    END AS age_bucket
  FROM utxo_spent
)
SELECT 
  spend_day_name,
  spend_hour,
  age_bucket,
  COUNT(*) AS utxo_count,
  SUM(value_btc) AS total_value_btc,
  AVG(value_btc) AS avg_value_btc,
  AVG(age_days) AS avg_age_days
FROM age_buckets
GROUP BY spend_day_name, spend_hour, age_bucket
ORDER BY spend_day_name, spend_hour, age_bucket
