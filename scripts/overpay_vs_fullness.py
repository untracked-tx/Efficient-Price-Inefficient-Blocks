#!/usr/bin/env python3
"""
Overpayment vs Block Fullness (BTC)
- Queries BigQuery public Bitcoin tables
- Defines "clearing fee" as p10 fee rate within each block (sat/vB)
- Overpayment ratio per tx = fee_rate / clearing_fee
- Aggregates to block-level median overpayment
- Bins blocks by fullness deciles and plots median with IQR ribbon

Usage:
  python scripts/overpay_vs_fullness.py --project YOUR_PROJECT [--years 2] [--start 2019-01-01 --end 2025-01-01] [--location US]
"""
import argparse, sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go

SQL_TEMPLATE = """
DECLARE start_date DATE DEFAULT {start_date};
DECLARE end_date   DATE DEFAULT {end_date};

WITH
blocks AS (
  SELECT
    b.hash,
    b.number AS height,
    b.timestamp AS ts,
    DATE(b.timestamp) AS day,
    SAFE_DIVIDE(b.weight, 4000000.0) AS fullness
  FROM `bigquery-public-data.crypto_bitcoin.blocks` b
  WHERE DATE(b.timestamp) BETWEEN start_date AND end_date
),
tx AS (
  SELECT
    t.block_hash,
    t.hash AS txid,
    t.fee,
    t.size,
    SAFE_DIVIDE(4.0 * t.fee, NULLIF(t.size,0)) AS fee_sat_per_vb
  FROM `bigquery-public-data.crypto_bitcoin.transactions` t
),
j AS (
  SELECT
  bl.height, bl.day, bl.fullness,
  tx.txid, tx.fee_sat_per_vb, tx.size
  FROM blocks bl
  JOIN tx ON tx.block_hash = bl.hash
  WHERE tx.fee_sat_per_vb IS NOT NULL AND tx.fee_sat_per_vb > 0 AND tx.size > 0
),
clearing AS (
  -- robust clearing price proxy per block = p10 fee rate among nonzero-fee txs
  SELECT
    height,
    GREATEST(1.0, APPROX_QUANTILES(fee_sat_per_vb, 1001)[OFFSET(100)]) AS clearing_fee_vb
  FROM j
  GROUP BY height
),
per_tx AS (
  SELECT
    j.height, j.day, j.fullness,
    j.fee_sat_per_vb,
    c.clearing_fee_vb,
    SAFE_DIVIDE(j.fee_sat_per_vb, c.clearing_fee_vb) AS overpay_ratio
  FROM j
  JOIN clearing c USING(height)
),
per_block AS (
  SELECT
    height, day, fullness,
    APPROX_QUANTILES(overpay_ratio, 101)[OFFSET(50)] AS median_overpay,
    APPROX_QUANTILES(overpay_ratio, 101)[OFFSET(25)] AS q25_overpay,
    APPROX_QUANTILES(overpay_ratio, 101)[OFFSET(75)] AS q75_overpay
  FROM per_tx
  GROUP BY height, day, fullness
),
deciles AS (
  SELECT
    *, NTILE(10) OVER(ORDER BY fullness) AS full_ntile
  FROM per_block
)
SELECT
  full_ntile,
  APPROX_QUANTILES(fullness, 101)[OFFSET(50)] AS fullness_median,
  APPROX_QUANTILES(median_overpay, 101)[OFFSET(50)] AS overpay_median,
  APPROX_QUANTILES(q25_overpay, 101)[OFFSET(50)] AS overpay_q25,
  APPROX_QUANTILES(q75_overpay, 101)[OFFSET(50)] AS overpay_q75,
  COUNT(*) AS blocks_in_bin
FROM deciles
GROUP BY full_ntile
ORDER BY full_ntile;
"""

def parse_args():
  p = argparse.ArgumentParser()
  p.add_argument("--project", required=True, help="GCP project id")
  p.add_argument("--location", default="US")
  p.add_argument("--years", type=int, default=2, help="Lookback in years (ignored if --start provided)")
  p.add_argument("--start", type=str, default=None, help="YYYY-MM-DD (optional)")
  p.add_argument("--end", type=str, default=None, help="YYYY-MM-DD (optional)")
  p.add_argument("--outdir", default="data/figs")
  p.add_argument("--tabs", action="store_true", help="Generate tabbed HTML comparing last 6 months vs last 2 years")
  return p.parse_args()

def build_sql(start, end):
    s = f"DATE('{start}')" if start else f"DATE_SUB(CURRENT_DATE(), INTERVAL {{years}} YEAR)"
    e = f"DATE('{end}')" if end else "CURRENT_DATE()"
    return SQL_TEMPLATE.format(start_date=s, end_date=e)

def build_sql_expr(start_expr: str, end_expr: str):
  """Build SQL using raw BigQuery date expressions (e.g., DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH))."""
  return SQL_TEMPLATE.format(start_date=start_expr, end_date=end_expr)

def run_bq(sql, project, location):
    import pandas_gbq  # lazy import
    print("Running BigQuery…")
    df = pandas_gbq.read_gbq(sql, project_id=project, location=location, dialect="standard", progress_bar_type=None)
    print(f"Rows: {len(df):,}")
    return df

def make_fig(df, out_html, window_label: str | None = None):
  df = df.sort_values("full_ntile")
  x = df["fullness_median"].values
  y = df["overpay_median"].values
  yq25 = df["overpay_q25"].values
  yq75 = df["overpay_q75"].values

  fig = go.Figure()
  # IQR ribbon
  fig.add_trace(go.Scatter(
    x=np.r_[x, x[::-1]], y=np.r_[yq75, yq25[::-1]],
    fill="toself", line=dict(width=0),
    fillcolor="rgba(100,100,200,0.20)", name="IQR (25–75%)"
  ))
  # Median line
  fig.add_trace(go.Scatter(
    x=x, y=y, mode="lines+markers",
    name="Median overpayment ratio"
  ))
  # Reference line at 1× (no overpay)
  fig.add_hline(y=1.0, line_dash="dot", line_color="gray")

  subtitle = f" — {window_label}" if window_label else ""
  fig.update_layout(
    title=f"Fee Overpayment vs Block Fullness (BTC){subtitle}\nOverpayment = fee_rate / in-block clearing_fee (p10 sat/vB)",
    xaxis_title="Block fullness (median per decile)",
    yaxis_title="Overpayment ratio (×)",
    template="plotly_white"
  )
  fig.update_yaxes(tickformat=".1f")
  fig.write_html(out_html, include_plotlyjs="cdn")
  print(f"Wrote {out_html}")

  return fig

def fig_to_inline_html(fig: go.Figure) -> str:
  """Return a Plotly div (no full HTML) suitable for embedding in a custom page."""
  return fig.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False})

def write_tabbed_html(panels, out_path: Path):
  """Compose a minimal tabbed HTML from (label, inner_html_div) panels.
  panels: list of (label, html_div_no_plotlyjs)
  """
  # Basic CSS/JS tabs
  css = """
  <style>
  .tabs { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; }
  .tab-buttons { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .tab-buttons button { padding: 6px 10px; border: 1px solid #ccc; background: #f6f6f6; cursor: pointer; border-radius: 6px; }
  .tab-buttons button.active { background: #eaeaea; font-weight: 600; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  </style>
  """
  js = """
  <script>
  function activateTab(idx) {
    const contents = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-buttons button');
    contents.forEach((c,i)=>{ c.classList.toggle('active', i===idx); });
    buttons.forEach((b,i)=>{ b.classList.toggle('active', i===idx); });
  }
  window.addEventListener('DOMContentLoaded', ()=> activateTab(0));
  </script>
  """
  # Compose body
  btns = "".join([f"<button onclick=\"activateTab({i})\">{label}</button>" for i,(label,_) in enumerate(panels)])
  sections = []
  for i,(label,body) in enumerate(panels):
    sections.append(f"<div class='tab-content{' active' if i==0 else ''}'>\n{body}\n</div>")
  body_html = f"""
  <div class="tabs">
    <div class="tab-buttons">{btns}</div>
    {''.join(sections)}
  </div>
  """
  html = f"""
  <!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Fee Overpayment vs Block Fullness — Comparison</title>
      <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
      {css}
    </head>
    <body>
      <h2 style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;">Fee Overpayment vs Block Fullness — Comparison</h2>
      <p style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; color:#555;">Overpayment = fee_rate / in-block clearing_fee (p10 sat/vB)</p>
      {body_html}
      {js}
    </body>
  </html>
  """
  out_path.write_text(html, encoding="utf-8")
  print(f"Wrote {out_path}")

def main():
  args = parse_args()

  outdir = Path(args.outdir)
  outdir.mkdir(parents=True, exist_ok=True)
  raw_dir = Path("data/raw")
  raw_dir.mkdir(parents=True, exist_ok=True)

  if args.tabs:
    # Two windows: last 6 months, last 2 years
    win_defs = [
      ("Last 6 months", "DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)", "CURRENT_DATE()", "6mo"),
      ("Last 2 years",  "DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)",  "CURRENT_DATE()", "2yr"),
    ]
    panels = []
    for label, start_expr, end_expr, slug in win_defs:
      sql = build_sql_expr(start_expr, end_expr)
      df = run_bq(sql, args.project, args.location)
      # write CSV labeled
      csv_path = raw_dir / f"overpay_vs_fullness_deciles_{slug}.csv"
      df.to_csv(csv_path, index=False)
      print(f"Wrote {csv_path}")
      # per-panel HTML and individual file
      fig = make_fig(df, outdir / f"overpay_vs_fullness_{slug}.html", label)
      panels.append((label, fig_to_inline_html(fig)))
    # compose tabs
    write_tabbed_html(panels, outdir / "overpay_vs_fullness_tabs.html")
  else:
    # Single-window behavior (backward compatible)
    if args.start is None:
      sql = build_sql(None, None).replace("{years}", str(args.years))
      window_label = f"Last {args.years} years"
    else:
      sql = build_sql(args.start, args.end or args.start)
      window_label = f"{args.start} to {args.end or args.start}"

    df = run_bq(sql, args.project, args.location)

    # Also write CSV for downstream merges (e.g., 3D combined visuals)
    csv_path = raw_dir / "overpay_vs_fullness_deciles.csv"
    df.to_csv(csv_path, index=False)
    print(f"Wrote {csv_path}")

    make_fig(df, outdir / "overpay_vs_fullness.html", window_label)

if __name__ == "__main__":
    sys.exit(main())
