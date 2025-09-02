#!/usr/bin/env python3
"""
Compute total fee overpayment (BTC) over anchored windows and render a compact graphic.

Definition (consistent with fee_overpayment_patterns.sql):
- Per block, compute median fee rate (sat per byte) across txs.
- A tx is an overpayment if its fee rate >= 2x the block median.
- Total overpayment BTC = sum of fees (in BTC) of these overpayment txs.

Windows are anchored to --end (default: 2025-08-01 per user request) and include:
- 6m: end - 6 months
- 1y: end - 1 year
- 3y: end - 3 years

Outputs:
- data/raw/overpay_totals_windows.csv
- data/figs/overpay_totals_windows.html
"""
import argparse
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

SQL = """
DECLARE end_date DATE DEFAULT DATE(@end_date);

WITH windows AS (
  SELECT '6m' AS label, DATE_SUB(end_date, INTERVAL 6 MONTH) AS start_date, end_date AS end_date UNION ALL
  SELECT '1y' AS label, DATE_SUB(end_date, INTERVAL 1 YEAR), end_date UNION ALL
  SELECT '3y' AS label, DATE_SUB(end_date, INTERVAL 3 YEAR), end_date
),
tx AS (
  SELECT
    w.label,
    t.block_number,
    t.block_timestamp,
    SAFE_DIVIDE(t.fee, NULLIF(t.size, 0)) AS fee_rate_sat_byte,
    t.fee / 1e8 AS fee_btc
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
  JOIN windows w
  ON DATE(t.block_timestamp) BETWEEN w.start_date AND w.end_date
  WHERE t.fee IS NOT NULL AND t.size > 0
),
block_medians AS (
  SELECT
    label,
    block_number,
    APPROX_QUANTILES(fee_rate_sat_byte, 100)[OFFSET(50)] AS median_fee_rate,
    COUNT(*) AS tx_count
  FROM tx
  GROUP BY label, block_number
  HAVING COUNT(*) >= 2
),
overp AS (
  SELECT
    x.label,
    x.fee_btc,
    x.fee_rate_sat_byte,
    m.median_fee_rate,
    x.fee_rate_sat_byte >= 2.0 * m.median_fee_rate AS is_overpayment
  FROM tx x
  JOIN block_medians m USING(label, block_number)
  WHERE m.median_fee_rate > 0
)
SELECT
  label,
  SUM(CASE WHEN is_overpayment THEN fee_btc END) AS total_overpayment_btc,
  COUNTIF(is_overpayment) AS overpayment_tx_count,
  COUNT(*) AS total_tx_count,
  SAFE_DIVIDE(COUNTIF(is_overpayment), COUNT(*)) AS overpayment_rate
FROM overp
GROUP BY label
ORDER BY CASE label WHEN '6m' THEN 1 WHEN '1y' THEN 2 ELSE 3 END;
"""


def run_bq(project: str, location: str, end_date: str) -> pd.DataFrame:
    import pandas_gbq
    job_config = {
        "query": {
            "parameterMode": "NAMED",
            "queryParameters": [
                {"name": "end_date", "parameterType": {"type": "STRING"}, "parameterValue": {"value": end_date}},
            ],
        }
    }
    print(f"Running BigQuery for end_date={end_date}…")
    df = pandas_gbq.read_gbq(SQL, project_id=project, location=location, dialect="standard", configuration=job_config, progress_bar_type=None)
    print(f"Rows: {len(df):,}")
    return df


def render_html(df: pd.DataFrame, out_html: Path, end_date: str):
    # Ensure label order
    cat_order = ["6m", "1y", "3y"]
    df["label"] = pd.Categorical(df["label"], categories=cat_order, ordered=True)
    df = df.sort_values("label")

    # Build three summary cards only (no chart)
    def fmt_btc(x: float) -> str:
        return f"{x:,.6f} BTC"

    def fmt_pct(x: float) -> str:
        return f"{x*100:.1f}%"

    def fmt_int(n: int) -> str:
        return f"{n:,}"

    palette = {"6m": "#6C8AE4", "1y": "#7CC6B2", "3y": "#F4A261"}
    label_title = {"6m": "Last 6 Months", "1y": "Last 1 Year", "3y": "Last 3 Years"}
    cards = []
    for row in df.itertuples(index=False):
        label = str(row.label)
        share_pct = fmt_pct(float(row.overpayment_rate))
        cards.append(
            f"""
            <div class='card' style='border-top:6px solid {palette.get(label, "#999")};'>
              <div class='card-head'>{label_title.get(label, label)}</div>
              <div class='pill' style='background:{palette.get(label, "#999")}1a;color:{palette.get(label, "#999")};'>
                {share_pct} overpay share
              </div>
              <div class='card-num'>{fmt_btc(float(row.total_overpayment_btc))}</div>
              <div class='card-sub'>overpay txs: {fmt_int(int(row.overpayment_tx_count))} ({fmt_pct(float(row.overpayment_rate))} of txs)</div>
            </div>
            """
        )

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8' />
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        <title>Overpayment Totals</title>
        <style>
          :root{{ --bg:#fff; --fg:#222; --muted:#666; --ring:#e9e9e9; }}
          @media (prefers-color-scheme: dark) {{ :root{{ --bg:#0f1115; --fg:#eaeaea; --muted:#aaa; --ring:#24262c; }} }}
          body{{ background:var(--bg); color:var(--fg); font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin:12px; }}
          .title{{ font-weight:700; font-size:1.05rem; margin: 4px 2px 12px 2px; }}
          .grid{{ display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; align-items:stretch; }}
          @media (max-width: 820px){{ .grid{{ grid-template-columns: 1fr; }} }}
          .card{{ border:1px solid var(--ring); border-radius:12px; padding:14px; background:linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0.00)); }}
          .card-head{{ font-size:0.95rem; color:var(--muted); margin-bottom:8px; }}
          .pill{{ display:inline-block; font-weight:700; font-size:0.85rem; padding:4px 8px; border-radius:999px; margin-bottom:8px; }}
          .card-num{{ font-weight:800; font-size:1.4rem; letter-spacing:0.2px; }}
          .card-sub{{ margin-top:6px; color:var(--muted); font-size:0.90rem; }}
          .footer{{ margin-top:10px; color:var(--muted); font-size:0.88rem; }}
        </style>
      </head>
      <body>
        <div class='title'>Total Fee Overpayment (≥ 2× block median) — anchored at {end_date}</div>
        <div class='grid'>
          {''.join(cards)}
        </div>
        <div class='footer'>Definition: tx counted as overpayment if fee rate ≥ 2× the block median fee rate (sat/byte). Windows: 6m, 1y, 3y.</div>
      </body>
    </html>
    """
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote {out_html}")


def main():
    ap = argparse.ArgumentParser(description="Overpayment totals (>=2x median) for 6m/1y/3y anchored windows")
    ap.add_argument("--project", required=True, help="GCP project id")
    ap.add_argument("--location", default="US")
    ap.add_argument("--end", default="2025-08-01", help="Anchor end date (YYYY-MM-DD)")
    ap.add_argument("--outdir", default="data/figs")
    ap.add_argument("--raw", default="data/raw/overpay_totals_windows.csv")
    args = ap.parse_args()

    df = run_bq(args.project, args.location, args.end)

    # Save CSV
    raw_path = Path(args.raw)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_path, index=False)
    print(f"Wrote {raw_path}")

    # Render HTML
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    render_html(df, outdir / "overpay_totals_windows.html", args.end)


if __name__ == "__main__":
    raise SystemExit(main())
