#!/usr/bin/env python3
"""
Joint regression on BigQuery joint dataset:
  median_overpay_ratio ~ C(fullness_quintile) + C(hour) + C(day_type)
                       + C(fullness_quintile):C(day_type)
                       + C(hour):C(day_type)

Outputs:
  - data/figs/overpay_interaction_regression_table.csv
  - data/figs/overpay_interaction_regression.html

Usage:
  python scripts/overpay_interaction_regression.py [--input data/raw/overpay_joint_fullness_hour_daytype_365d.csv]
"""
import argparse
from pathlib import Path
import glob
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import plotly.graph_objects as go
import plotly.io as pio


def find_latest_joint_csv() -> Path | None:
    paths = sorted(glob.glob("data/raw/overpay_joint_fullness_hour_daytype_*d.csv"))
    return Path(paths[-1]) if paths else None


def wald_joint_test(res, param_substrings: list[str]):
    """Joint robust Wald test for all params whose names contain any of the substrings.
    Returns dict with {k, df, stat, pval} or None if no matching params.
    """
    names = list(res.params.index)
    idxs = [i for i, n in enumerate(names) if any(s in n for s in param_substrings)]
    if not idxs:
        return None
    R = np.zeros((len(idxs), len(names)))
    for r, i in enumerate(idxs):
        R[r, i] = 1.0
    w = res.wald_test(R)
    stat = float(w.statistic) if np.ndim(w.statistic) == 0 else float(w.statistic[0][0])
    df = int(w.df_denom or w.df_num or len(idxs)) if hasattr(w, "df_denom") else len(idxs)
    pval = float(w.pvalue)
    return {"k": len(idxs), "df": df, "stat": stat, "pval": pval}


def main():
    ap = argparse.ArgumentParser(description="Joint regression: overpay ~ fullness + hour + weekend + interactions")
    ap.add_argument("--input", default=None, help="Path to joint CSV (default: latest overpay_joint_fullness_hour_daytype_*d.csv)")
    ap.add_argument("--outdir", default="data/figs", help="Output directory for HTML and CSV")
    args = ap.parse_args()

    inp = Path(args.input) if args.input else find_latest_joint_csv()
    if not inp or not inp.exists():
        raise SystemExit("No joint dataset found. Run scripts/3d-draft.py with --project first.")

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(inp)

    # Coerce dtypes
    for c in ["median_overpay_ratio", "fullness_quintile", "hour"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # build clean subset
    use = df.dropna(subset=["median_overpay_ratio", "fullness_quintile", "hour", "day_type"]).copy()

    # Formula with interactions
    formula = (
        "median_overpay_ratio ~ C(fullness_quintile) + C(hour) + C(day_type) "
        "+ C(fullness_quintile):C(day_type) + C(hour):C(day_type)"
    )
    res = smf.ols(formula, data=use).fit(cov_type="HC3")

    # Coefficients table
    summ = pd.DataFrame({
        "term": res.params.index,
        "coef": res.params.values,
        "se": res.bse.values,
        "t": res.tvalues,
        "p": res.pvalues,
        "ci_low": res.conf_int()[0].values,
        "ci_high": res.conf_int()[1].values,
    })
    summ.to_csv(outdir / "overpay_interaction_regression_table.csv", index=False)

    # Joint tests for interaction blocks
    jt_fullness = wald_joint_test(res, ["C(fullness_quintile):C(day_type)"])
    jt_hour = wald_joint_test(res, ["C(hour):C(day_type)"])

    # Build a compact HTML report
    header = f"""
    <h2 style='margin:0'>Joint Regression: Overpayment ~ Fullness + Hour + Weekend (+ interactions)</h2>
    <p style='color:#555;margin:6px 0 14px'>Robust OLS (HC3). N={len(use):,} • R²={res.rsquared:.3f}</p>
    """

    bullets = "<ul style='margin:0 0 14px 18px;color:#333'>"
    if jt_fullness:
        bullets += f"<li>Interaction Fullness×Weekend: χ²={jt_fullness['stat']:.1f} (df={jt_fullness['k']}), p={jt_fullness['pval']:.3g}</li>"
    if jt_hour:
        bullets += f"<li>Interaction Hour×Weekend: χ²={jt_hour['stat']:.1f} (df={jt_hour['k']}), p={jt_hour['pval']:.3g}</li>"
    bullets += "</ul>"

    # Pretty table (top lines: main effects + interactions only)
    def _keep(term: str) -> bool:
        return any(s in term for s in ["C(fullness_quintile)", "C(hour)", "C(day_type)"])
    view = summ[["term","coef","se","t","p","ci_low","ci_high"]].copy()
    view = view[view["term"].apply(_keep)]
    view["coef_fmt"] = view["coef"].map(lambda x: f"{x:.3f}")
    view["se_fmt"] = view["se"].map(lambda x: f"{x:.3f}")
    view["p_fmt"] = view["p"].map(lambda x: f"{x:.3g}")

    table = go.Figure(data=[go.Table(
        header=dict(values=["Term","Coef","SE","t","p","95% CI"], fill_color="#4C78A8", font=dict(color="white")),
        cells=dict(values=[
            view["term"], view["coef_fmt"], view["se_fmt"], view["t"].map(lambda x: f"{x:.2f}"), view["p_fmt"],
            view.apply(lambda r: f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]", axis=1)
        ], align="left")
    )])
    table.update_layout(title="Robust OLS coefficients (selected)", margin=dict(t=50,b=20,l=20,r=20), height=640)

    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<script src='https://cdn.plot.ly/plotly-2.30.0.min.js'></script>"
        "<style>body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:1100px;margin:20px auto;padding:0 16px;color:#111}</style>"
        "</head><body>"
        + header + bullets + table.to_html(full_html=False, include_plotlyjs=False)
        + f"<p style='margin-top:12px'><a href='../data/figs/overpay_interaction_regression_table.csv' target='_blank'>Download coefficients (CSV)</a></p>"
        + "</body></html>"
    )
    (outdir / "overpay_interaction_regression.html").write_text(html, encoding="utf-8")
    print(f"Saved: {outdir / 'overpay_interaction_regression.html'}")


if __name__ == "__main__":
    main()
