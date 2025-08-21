-- elasticity.sql
-- Build a per-block and per-hour panel with throughput, fees, and supply-side instruments

DECLARE start_date DATE DEFAULT DATE('2019-01-01');
DECLARE end_date   DATE DEFAULT CURRENT_DATE();

WITH
blocks AS (
  SELECT
    b.hash,
    b.height,
    TIMESTAMP_MILLIS(b.time) AS ts,
    DATE(TIMESTAMP_MILLIS(b.time)) AS day,
    EXTRACT(HOUR FROM TIMESTAMP_MILLIS(b.time)) AS hour_utc,
    b.weight,
    b.n_tx
  FROM `bigquery-public-data.crypto_bitcoin.blocks` b
  WHERE DATE(TIMESTAMP_MILLIS(b.time)) BETWEEN start_date AND end_date
),
tx AS (
  SELECT
    t.block_hash,
    t.size,
    t.weight,
    t.fee,
    SAFE_DIVIDE(t.fee, NULLIF(t.size,0)) AS fee_per_byte  -- sat/byte
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
),
block_metrics AS (
  SELECT
    bl.hash,
    bl.height,
    bl.ts,
    bl.day,
    bl.hour_utc,
    bl.weight AS weight_used,
    bl.n_tx    AS tx_count,
    APPROX_QUANTILES(tx.fee_per_byte, 101)[OFFSET(50)] AS p50_fee_per_byte,
    APPROX_QUANTILES(tx.fee_per_byte, 101)[OFFSET(10)] AS p10_fee_per_byte,
    MIN(tx.fee_per_byte) AS min_fee_per_byte
  FROM blocks bl
  JOIN tx ON tx.block_hash = bl.hash
  GROUP BY bl.hash, bl.height, bl.ts, bl.day, bl.hour_utc, bl.weight, bl.n_tx
),
-- Inter-block times and supply shocks
ibt AS (
  SELECT
    m.*,
    TIMESTAMP_DIFF(m.ts, LAG(m.ts) OVER (ORDER BY m.ts), SECOND) AS ibt_seconds
  FROM block_metrics m
),
per_hour AS (
  SELECT
    DATE_TRUNC(day, DAY) AS day,
    EXTRACT(HOUR FROM ts) AS hour_utc,
    COUNT(*) AS blocks_in_hour,
    SUM(weight_used) AS weight_used_hour,
    SUM(tx_count) AS tx_count_hour,
    APPROX_QUANTILES(p50_fee_per_byte, 101)[OFFSET(50)] AS p50_fee_per_byte_hour
  FROM ibt
  GROUP BY day, hour_utc
),
instruments AS (
  SELECT
    ph.day,
    ph.hour_utc,
    ph.blocks_in_hour,
    -- Simple supply shock: realized blocks - expected (6 per hour)
    (ph.blocks_in_hour - 6) AS supply_shock_blocks,
    -- Average inter-block time surprise can be computed if desired at hourly granularity
    ph.weight_used_hour,
    ph.tx_count_hour,
    ph.p50_fee_per_byte_hour
  FROM per_hour ph
)

SELECT * FROM instruments
ORDER BY day, hour_utc;