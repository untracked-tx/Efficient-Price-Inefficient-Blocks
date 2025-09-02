-- Block Time Variance Analysis
-- Calculate time differences between consecutive blocks and analyze by day of week

WITH block_times AS (
  SELECT 
    number,
    timestamp,
    FORMAT_TIMESTAMP('%A', timestamp) AS day_name,
    EXTRACT(HOUR FROM timestamp) AS hour,
    LAG(timestamp) OVER (ORDER BY number) AS prev_timestamp
  FROM `bigquery-public-data.crypto_bitcoin.blocks`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @years YEAR)
    AND number > 0  -- Skip genesis block
),
intervals AS (
  SELECT 
    number,
    timestamp,
    day_name,
    hour,
    TIMESTAMP_DIFF(timestamp, prev_timestamp, SECOND) AS interval_seconds
  FROM block_times
  WHERE prev_timestamp IS NOT NULL
    AND TIMESTAMP_DIFF(timestamp, prev_timestamp, SECOND) > 0
    AND TIMESTAMP_DIFF(timestamp, prev_timestamp, SECOND) < 7200  -- Filter out unrealistic intervals (>2 hours)
)
SELECT 
  day_name,
  hour,
  COUNT(*) AS block_count,
  AVG(interval_seconds) AS avg_interval_seconds,
  STDDEV(interval_seconds) AS std_interval_seconds,
  MIN(interval_seconds) AS min_interval_seconds,
  MAX(interval_seconds) AS max_interval_seconds,
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(50)] AS median_interval_seconds,
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(25)] AS q25_interval_seconds,
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(75)] AS q75_interval_seconds
FROM intervals
GROUP BY day_name, hour
ORDER BY day_name, hour
