-- factors.sql
-- Daily on-chain factor table: HODL proxy, SOPR-lite, FeeShare
-- PARAMETERS: set @start_date and @end_date as desired
DECLARE start_date DATE DEFAULT DATE('2017-01-01');
DECLARE end_date   DATE DEFAULT CURRENT_DATE();

-- NOTE: You will also need a BTCUSD daily close table for SOPR-lite joins.
-- Create once from your chosen venue and load as your_dataset.btcusd_daily with columns:
--   day DATE, close_usd FLOAT64
-- Then replace `your_dataset.btcusd_daily` in the btcusd CTE below.

WITH
days AS (
  SELECT day
  FROM UNNEST(GENERATE_DATE_ARRAY(start_date, end_date)) AS day
),
btcusd AS (
  SELECT day, close_usd
  FROM `your_dataset.btcusd_daily`
  WHERE day BETWEEN start_date AND end_date
),

-- Block-level fees & subsidy
block_fees AS (
  SELECT
    DATE(TIMESTAMP_MILLIS(b.time)) AS day,
    b.height,
    -- Sum of tx fees (in satoshis) at block level
    SUM(t.fee) AS fees_sats,
    -- Subsidy in sats via halving schedule
    CAST(ROUND(5e9 * POW(0.5, FLOOR(b.height / 210000))) AS INT64) AS subsidy_sats
  FROM `bigquery-public-data.crypto_bitcoin.blocks` b
  JOIN `bigquery-public-data.crypto_bitcoin.transactions` t
    ON t.block_hash = b.hash
  WHERE DATE(TIMESTAMP_MILLIS(b.time)) BETWEEN start_date AND end_date
  GROUP BY day, b.height
),
daily_fee_share AS (
  SELECT
    day,
    SUM(fees_sats) AS fees_sats_day,
    SUM(subsidy_sats) AS subsidy_sats_day,
    SAFE_DIVIDE(SUM(fees_sats), SUM(fees_sats) + SUM(subsidy_sats)) AS fee_share
  FROM block_fees
  GROUP BY day
),

-- SOPR-lite: value-weighted (spent value / cost basis) for spent outputs per day
-- 1) Map each input to its originating output (value & creation day)
spent AS (
  SELECT i.transaction_hash AS spend_tx,
         i.spent_output_hash AS origin_tx,
         i.spent_output_index AS origin_idx
  FROM `bigquery-public-data.crypto_bitcoin.inputs` i
),
origin AS (
  SELECT o.transaction_hash AS origin_tx,
         o.index AS origin_idx,
         o.value AS value_sats,
         DATE(TIMESTAMP_MILLIS(o.time)) AS created_day
  FROM `bigquery-public-data.crypto_bitcoin.outputs` o
),
spend_times AS (
  SELECT t.hash AS spend_tx,
         DATE(TIMESTAMP_MILLIS(t.time)) AS spend_day
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
),
joined_spends AS (
  SELECT
    s.spend_tx,
    st.spend_day,
    o.value_sats,
    o.created_day
  FROM spent s
  JOIN origin o
    ON o.origin_tx = s.origin_tx AND o.origin_idx = s.origin_idx
  JOIN spend_times st
    ON st.spend_tx = s.spend_tx
  WHERE st.spend_day BETWEEN start_date AND end_date
),

sopr_daily AS (
  SELECT
    j.spend_day AS day,
    -- join USD close for numerator and denominator
    SUM( (j.value_sats/1e8) * bu_spend.close_usd )     AS spent_value_usd,
    SUM( (j.value_sats/1e8) * bu_create.close_usd )    AS cost_basis_usd,
    SAFE_DIVIDE(
      SUM( (j.value_sats/1e8) * bu_spend.close_usd ),
      NULLIF(SUM( (j.value_sats/1e8) * bu_create.close_usd ), 0)
    ) AS sopr_lite_vw
  FROM joined_spends j
  LEFT JOIN btcusd bu_spend  ON bu_spend.day  = j.spend_day
  LEFT JOIN btcusd bu_create ON bu_create.day = j.created_day
  GROUP BY day
),

-- HODL proxy (flow-based): share of spent value where age >= 365d
spend_age AS (
  SELECT
    j.spend_day AS day,
    SUM(j.value_sats) AS spent_sats_total,
    SUM(CASE WHEN j.created_day <= DATE_SUB(j.spend_day, INTERVAL 365 DAY)
             THEN j.value_sats ELSE 0 END) AS spent_sats_1yplus
  FROM joined_spends j
  GROUP BY day
),
hodl_flow AS (
  SELECT
    day,
    SAFE_DIVIDE(spent_sats_1yplus, NULLIF(spent_sats_total,0)) AS spent_1y_share
  FROM spend_age
)

-- FINAL daily factor table
SELECT
  d.day,
  dfs.fee_share,
  s.sopr_lite_vw,
  h.spent_1y_share AS hodl_proxy_1y_flow
FROM days d
LEFT JOIN daily_fee_share dfs USING (day)
LEFT JOIN sopr_daily s        USING (day)
LEFT JOIN hodl_flow h         USING (day)
ORDER BY d.day;