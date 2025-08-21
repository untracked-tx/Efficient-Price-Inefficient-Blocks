-- seasonality.sql
-- Hour-of-day × Day-of-week fee and fullness seasonality (UTC and optional local time)

DECLARE start_date DATE DEFAULT DATE('2019-01-01');
DECLARE end_date   DATE DEFAULT CURRENT_DATE();

WITH
blocks AS (
  SELECT
    TIMESTAMP_MILLIS(b.time) AS ts,
    DATE(TIMESTAMP_MILLIS(b.time)) AS day,
    EXTRACT(DAYOFWEEK FROM TIMESTAMP_MILLIS(b.time)) AS dow_utc,  -- 1=Sun ... 7=Sat
    EXTRACT(HOUR FROM TIMESTAMP_MILLIS(b.time)) AS hour_utc,
    b.weight,
    b.n_tx,
    b.hash
  FROM `bigquery-public-data.crypto_bitcoin.blocks` b
  WHERE DATE(TIMESTAMP_MILLIS(b.time)) BETWEEN start_date AND end_date
),
tx AS (
  SELECT
    t.block_hash,
    SAFE_DIVIDE(t.fee, NULLIF(t.size,0)) AS fee_per_byte
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
),
block_fee AS (
  SELECT
    bl.day,
    bl.dow_utc,
    bl.hour_utc,
    bl.weight,
    bl.n_tx,
    APPROX_QUANTILES(tx.fee_per_byte, 101)[OFFSET(50)] AS p50_fee_per_byte
  FROM blocks bl
  JOIN tx ON tx.block_hash = bl.hash
  GROUP BY bl.day, bl.dow_utc, bl.hour_utc, bl.weight, bl.n_tx
),
hourly AS (
  SELECT
    day,
    dow_utc,
    hour_utc,
    COUNT(*) AS blocks,
    AVG(SAFE_DIVIDE(weight, 4000000)) AS fullness_avg, -- 4M wu max
    APPROX_QUANTILES(p50_fee_per_byte, 101)[OFFSET(50)] AS p50_fee_per_byte_hour
  FROM block_fee
  GROUP BY day, dow_utc, hour_utc
),
-- Aggregate by DOW × HOUR across the sample
seasonality AS (
  SELECT
    dow_utc,
    hour_utc,
    AVG(fullness_avg) AS fullness_avg,
    APPROX_QUANTILES(p50_fee_per_byte_hour, 101)[OFFSET(50)] AS p50_fee_per_byte_median
  FROM hourly
  GROUP BY dow_utc, hour_utc
)

SELECT * FROM seasonality
ORDER BY dow_utc, hour_utc;