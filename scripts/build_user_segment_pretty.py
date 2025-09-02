#!/usr/bin/env python3
"""
Builds a styled Plotly HTML: "User Segment Analysis: Who Overpays When?"
Uses real data from data/raw/overpay_joint_fullness_hour_daytype_365d.csv
and renders an HTML similar to draftish.txt (but with real values).

Outputs: data/figs/user_segment_3d.html (overwrites if exists)
"""
from __future__ import annotations

import json
from pathlib import Path
import argparse

import pandas as pd


RAW_CSV = Path("data/raw/overpay_joint_fullness_hour_daytype_365d.csv")
OUT_HTML = Path("data/figs/user_segment_3d.html")


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Ensure expected columns exist
    required = {
        "fullness_quintile",
        "hour",
        "day_type",
        "day_name",
        "time_period",
        "tx_size_category",
        "median_overpay_ratio",
        "pct_2x_overpay",
        "std_overpay_ratio",
        "tx_count",
        "total_overpay_btc",
        "fullness_median",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in CSV: {sorted(missing)}")

    # Normalize/clean types
    num_cols = [
        "fullness_quintile",
        "hour",
        "median_overpay_ratio",
        "pct_2x_overpay",
        "std_overpay_ratio",
        "tx_count",
        "total_overpay_btc",
        "fullness_median",
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Keep a canonical order for categories
    tx_order = ["Dust", "Small", "Medium", "Large", "Whale"]
    period_order = ["Morning", "Afternoon", "Evening", "Night"]
    df["tx_size_category"] = pd.Categorical(df["tx_size_category"], categories=tx_order, ordered=True)
    df["time_period"] = pd.Categorical(df["time_period"], categories=period_order, ordered=True)
    return df


def prepare_traces(df: pd.DataFrame):
    # 1) Lines: Overpayment by User Type & Fullness
    # x as fullness % buckets (quintiles 1..5 -> 20,40,60,80,100)
    fullness_map = {1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
    t1 = (
        df.groupby(["tx_size_category", "fullness_quintile"])  # aggregate across time/day
          .agg(med=("median_overpay_ratio", "mean"))
          .reset_index()
    )
    # Build list per tx type ordered by quintile
    user_types = [c for c in df["tx_size_category"].cat.categories if pd.notna(c)]
    lines = []
    for tx in user_types:
        sub = t1[t1["tx_size_category"] == tx].sort_values("fullness_quintile")
        x = [fullness_map.get(int(q), None) for q in sub["fullness_quintile"].tolist()]
        y = sub["med"].fillna(0).tolist()
        lines.append({"name": tx, "x": x, "y": y})

    # 2) Bars: Time Period Effects by User Type (per period across types)
    t2 = (
        df.groupby(["time_period", "tx_size_category"])  # aggregate across fullness/hour/day
          .agg(med=("median_overpay_ratio", "mean"))
          .reset_index()
    )
    periods = [c for c in df["time_period"].cat.categories if pd.notna(c)]
    bars_periods = []
    for period in periods:
        sub = (
            t2[t2["time_period"] == period]
              .sort_values("tx_size_category")
        )
        bars_periods.append({
            "name": period,
            "x": sub["tx_size_category"].astype(str).tolist(),
            "y": sub["med"].fillna(0).tolist(),
        })

    # 3) Bars: Economic Impact Distribution (total BTC overpaid) by User Type split across fullness buckets
    t3 = (
        df.groupby(["fullness_quintile", "tx_size_category"])  # sum economic impact
          .agg(total=("total_overpay_btc", "sum"))
          .reset_index()
    )
    bars_impact = []
    for q in sorted(df["fullness_quintile"].dropna().unique()):
        sub = (
            t3[t3["fullness_quintile"] == q]
              .sort_values("tx_size_category")
        )
        bars_impact.append({
            "name": f"{fullness_map.get(int(q), int(q)*20)}% full",
            "x": sub["tx_size_category"].astype(str).tolist(),
            "y": sub["total"].fillna(0).tolist(),
        })

    # 4) Bubble scatter: behavior summary per user type
    t4 = (
        df.groupby(["tx_size_category"])  # averages across contexts
          .agg(
              pct2x=("pct_2x_overpay", "mean"),
              med=("median_overpay_ratio", "mean"),
              txc=("tx_count", "sum"),
              btc=("total_overpay_btc", "sum"),
          )
          .reset_index()
          .sort_values("tx_size_category")
    )
    # Scale sizes (diameter) mapped to [12, 48]
    if (t4["txc"] > 0).any():
        tx_min, tx_max = float(t4["txc"].min()), float(t4["txc"].max())
        if tx_max > tx_min:
            sizes = 12 + (t4["txc"] - tx_min) * (48 - 12) / (tx_max - tx_min)
        else:
            sizes = pd.Series([24] * len(t4))
    else:
        sizes = pd.Series([24] * len(t4))

    bubbles = {
        "x": (t4["pct2x"].fillna(0) * 100).tolist(),
        "y": t4["med"].fillna(0).tolist(),
        "text": t4["tx_size_category"].astype(str).tolist(),
        "size": sizes.round(2).tolist(),
        "color": t4["btc"].fillna(0).round(8).tolist(),  # BTC overpaid
    }

    return {
        "user_types": user_types,
        "fullness_levels": [20, 40, 60, 80, 100],
        "time_periods": periods,
        "lines": lines,
        "bars_periods": bars_periods,
        "bars_impact": bars_impact,
        "bubbles": bubbles,
    }


def render_html(payload: dict) -> str:
    # Use a plain template and substitute a JSON placeholder to avoid brace escaping issues
    template = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>User Segment Analysis: Who Overpays When?</title>
  <script src=\"https://cdn.plot.ly/plotly-latest.min.js\"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; text-align: center; margin-bottom: 10px; }
    .definitions { background: #f9f9f9; border-left: 4px solid #F7931A; padding: 20px; margin: 20px 0 30px 0; border-radius: 5px; }
    .definitions h3 { color: #F7931A; margin-top: 0; margin-bottom: 15px; }
    .def-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
    .def-item { padding: 10px; background: white; border-radius: 5px; border: 1px solid #e0e0e0; }
    .def-item strong { color: #2c3e50; display: block; margin-bottom: 5px; }
    .def-item .amount { color: #666; font-size: 14px; }
    .def-item .usd { color: #F7931A; font-size: 13px; margin-top: 3px; }
  #plotDiv { width: 100%; height: 900px; }
    .note { background: #fff9e6; border: 1px solid #ffd700; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 14px; color: #666; }
    .note strong { color: #F7931A; }
  </style>
  <script>
    window.addEventListener('DOMContentLoaded', function() {
      const payload = PAYLOAD_JSON;

      const userTypes = payload.user_types;
      const fullnessLevels = payload.fullness_levels;
      const timePeriods = payload.time_periods;

      // 1) Lines by user type
      const traces1 = payload.lines.map(l => ({
        x: l.x, y: l.y, type: 'scatter', mode: 'lines+markers', name: l.name,
        line: { width: 2 }, marker: { size: 8 }, legendgroup: 'users', xaxis: 'x', yaxis: 'y'
      }));

      // 2) Bars by time period
      const traces2 = payload.bars_periods.map(b => ({
        x: b.x, y: b.y, type: 'bar', name: b.name, legendgroup: 'periods', xaxis: 'x2', yaxis: 'y2'
      }));

      // 3) Bars: Economic impact distribution (BTC)
      const traces3 = payload.bars_impact.map(b => ({
        x: b.x, y: b.y, type: 'bar', name: b.name, showlegend: false, xaxis: 'x3', yaxis: 'y3'
      }));

      // 4) Bubble scatter
      const bubble = payload.bubbles;
      const trace4 = {
        x: bubble.x, y: bubble.y, mode: 'markers+text', type: 'scatter', text: bubble.text,
        textposition: 'top center', xaxis: 'x4', yaxis: 'y4',
        marker: {
          size: bubble.size, sizemode: 'diameter', sizemin: 6,
          color: bubble.color, colorscale: 'Viridis', showscale: true,
          colorbar: {
            title: 'BTC Overpaid', titleside: 'right', thickness: 15, len: 0.5, x: 1.02, y: 0.25
          }
        },
        showlegend: false
      };

      const data = [...traces1, ...traces2, ...traces3, trace4];

      const layout = {
        title: { text: 'User Segment Analysis: Who Overpays When?', font: { size: 20 } },
        grid: { rows: 2, columns: 2, pattern: 'independent', roworder: 'top to bottom' },
        xaxis:  { title: 'Block Fullness (%)', domain: [0, 0.45], anchor: 'y' },
        yaxis:  { title: 'Median Overpay Ratio', domain: [0.55, 1], anchor: 'x' },
        xaxis2: { title: 'User Type', domain: [0.55, 1], anchor: 'y2' },
        yaxis2: { title: 'Median Overpay Ratio', domain: [0.55, 1], anchor: 'x2' },
        xaxis3: { title: 'User Type', domain: [0, 0.45], anchor: 'y3' },
        yaxis3: { title: 'Total BTC Overpaid', domain: [0, 0.40], anchor: 'x3' },
        xaxis4: { title: '>2× Overpay (%)', domain: [0.55, 1], anchor: 'y4' },
        yaxis4: { title: 'Median Overpay Ratio', domain: [0, 0.40], anchor: 'x4' },
        annotations: [
          { text: 'Overpayment by User Type & Fullness', x: 0.225, y: 1.05, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 14, color: '#2c3e50' } },
          { text: 'Time Period Effects by User Type',   x: 0.775, y: 1.05, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 14, color: '#2c3e50' } },
          { text: 'Economic Impact Distribution',       x: 0.225, y: 0.48, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 14, color: '#2c3e50' } },
          { text: 'Behavioral Patterns',                x: 0.775, y: 0.48, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 14, color: '#2c3e50' } }
        ],
  legend: { orientation: 'h', y: -0.15, x: 0.5, xanchor: 'center', yanchor: 'top', bgcolor: 'rgba(255,255,255,0.9)', bordercolor: '#e0e0e0', borderwidth: 1, tracegroupgap: 30 },
  margin: { l: 60, r: 100, t: 80, b: 150 }, height: 900, showlegend: true
      };

      const config = { responsive: true, displayModeBar: true, displaylogo: false, modeBarButtonsToRemove: ['pan2d','lasso2d','select2d'] };
      Plotly.newPlot('plotDiv', data, layout, config);
    });
  </script>
</head>
<body>
  <div class=\"container\">
    <h1>User Segment Analysis: Who Overpays When?</h1>
    <div class=\"definitions\">
      <h3>Transaction Size Categories (at $100,000/BTC)</h3>
      <div class=\"def-grid\">
        <div class=\"def-item\"><strong>🔵 Dust</strong><div class=\"amount\">< 0.01 BTC</div><div class=\"usd\">< $1,000</div></div>
        <div class=\"def-item\"><strong>🟢 Small</strong><div class=\"amount\">0.01 - 0.1 BTC</div><div class=\"usd\">$1,000 - $10,000</div></div>
        <div class=\"def-item\"><strong>🟡 Medium</strong><div class=\"amount\">0.1 - 1 BTC</div><div class=\"usd\">$10,000 - $100,000</div></div>
        <div class=\"def-item\"><strong>🟠 Large</strong><div class=\"amount\">1 - 10 BTC</div><div class=\"usd\">$100,000 - $1M</div></div>
        <div class=\"def-item\"><strong>🔴 Whale</strong><div class=\"amount\">> 10 BTC</div><div class=\"usd\">> $1 Million</div></div>
      </div>
    </div>
    <div id=\"plotDiv\"></div>
    <div class=\"note\">
      <strong>Key Insights:</strong>
      <ul style=\"margin: 10px 0 0 0; padding-left: 25px;\">
        <li><strong>Dust transactions</strong> often overpay the most (low stakes, less optimization)</li>
        <li><strong>Whales</strong> tend to be more efficient, especially during congestion</li>
        <li><strong>Weekend mornings</strong> may show the highest overpayment across types</li>
        <li><strong>Economic impact</strong> concentrates in Medium and Large transactions</li>
      </ul>
    </div>
  </div>
  <script>/* Plot injected via payload above */</script>
</body>
</html>
"""
    return template.replace("PAYLOAD_JSON", json.dumps(payload))


def main():
    parser = argparse.ArgumentParser(description="Build styled user segment HTML from real CSV")
    parser.add_argument("--csv", default=str(RAW_CSV), help="Path to the joint CSV")
    parser.add_argument("--out", default=str(OUT_HTML), help="Path to output HTML")
    args = parser.parse_args()

    df = load_data(Path(args.csv))
    payload = prepare_traces(df)
    html = render_html(payload)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
