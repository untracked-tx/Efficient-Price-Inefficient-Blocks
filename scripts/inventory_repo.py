from __future__ import annotations
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
PAPER_QMD = ROOT / "paper" / "paper.qmd"
FIGS_DIR = ROOT / "data" / "figs"
RAW_DIR = ROOT / "data" / "raw"
SCRIPTS_DIR = ROOT / "scripts"
REPORT = ROOT / "docs" / "inventory_report.md"

FIG_TO_SCRIPT_HINTS = {
    "overpay_totals_windows.html": "overpay_totals_windows.py",
    "bitcoin-bus-interactive.html": "(static HTML)",
    "user_segment_3d.html": "build_user_segment_pretty.py",
    "mempool_heatmap.html": "mempool_heatmap.py",
    "seasonality_heatmap_year.html": "seasonality_heatmap_year.py",
    "seasonality_heatmap_5yr.html": "seasonality_heatmap_5yr.py",
    "fee_overpayment_patterns_5yr_interactive.html": "visualize_fee_overpayment_patterns.py",
    "interaction_heatmaps.html": "3d-draft.py",
    "overpay_interaction_regression.html": "overpay_interaction_regression.py",
    "btc_weekday_lead_dashboard.html": "btc_weekly_lead.py",
    "rolling_monday_diff.html": "rolling_monday_difference.py",
    "btc_regression_coeffs_interactive.html": "btc_regression_analysis_interactive.py",
    "btc_anova_summary_interactive.html": "btc_regression_analysis_interactive.py",
    "heatmap_month_weekday_returns.html": "price_appendix_figs.py",
    "3d_surface_overpayment.html": "3d-draft.py",
    "3d_interactive_explore.html": "3d-draft.py",
}

HREF_PATTERN = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_refs(text: str) -> set[Path]:
    refs: set[Path] = set()
    for m in HREF_PATTERN.finditer(text):
        raw = m.group(1)
        if raw.startswith("http:") or raw.startswith("https:"):
            continue
        # Normalize and resolve relative to paper dir
        rp = (PAPER_QMD.parent / raw).resolve()
        refs.add(rp)
    return refs


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    paper_text = read_text(PAPER_QMD)
    refs = extract_refs(paper_text)

    figs_all = sorted([p for p in FIGS_DIR.glob("**/*") if p.is_file()])
    figs_used = sorted([p for p in refs if p.is_file() and FIGS_DIR in p.parents])
    figs_used_names = {p.name for p in figs_used}

    figs_unused = [p for p in figs_all if p.name not in figs_used_names]

    # Raw data references (optional)
    raw_refs = sorted([p for p in refs if p.is_file() and RAW_DIR in p.parents])

    # Scripts mapping
    scripts_all = sorted([p.name for p in SCRIPTS_DIR.glob("*.py")])
    inferred_used_scripts = set()
    fig_to_script = {}
    for f in figs_used:
        hint = FIG_TO_SCRIPT_HINTS.get(f.name)
        if hint:
            fig_to_script[f.name] = hint
            if hint.endswith(".py"):
                inferred_used_scripts.add(hint)
        else:
            fig_to_script[f.name] = "(unknown generator)"

    scripts_unused = [s for s in scripts_all if s not in inferred_used_scripts and s != Path(__file__).name]

    # Group unused figs by extension for quick skim
    by_ext: dict[str, list[Path]] = defaultdict(list)
    for p in figs_unused:
        by_ext[p.suffix.lower()].append(p)

    # Write report
    lines: list[str] = []
    lines.append("# Repository Inventory Report\n")
    lines.append(f"Root: {ROOT}")
    lines.append("")

    lines.append("## Figures referenced in paper (data/figs)")
    for p in figs_used:
        gen = fig_to_script.get(p.name, "")
        rel = p.relative_to(ROOT)
        lines.append(f"- {rel}  — generator: {gen}")
    if not figs_used:
        lines.append("- (none found)")
    lines.append("")

    lines.append("## Figures present but not referenced in paper (data/figs)")
    if figs_unused:
        for ext, items in sorted(by_ext.items()):
            lines.append(f"### {ext or '(no ext)'} — {len(items)} files")
            for p in sorted(items):
                lines.append(f"- {p.relative_to(ROOT)}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Raw data files referenced in paper (data/raw)")
    if raw_refs:
        for p in raw_refs:
            lines.append(f"- {p.relative_to(ROOT)}")
    else:
        lines.append("- (none found)")
    lines.append("")

    lines.append("## Scripts likely used (inferred from figures)")
    if inferred_used_scripts:
        for s in sorted(inferred_used_scripts):
            lines.append(f"- scripts/{s}")
    else:
        lines.append("- (none inferred)")
    lines.append("")

    lines.append("## Other scripts (candidates to review)")
    for s in sorted(scripts_unused):
        lines.append(f"- scripts/{s}")
    lines.append("")

    lines.append("## Suggestions\n")
    lines.append("- Consider archiving unreferenced figures to data/figs/unused/ to declutter.")
    lines.append("- Remove or consolidate scripts that are superseded or not tied to current paper.")
    lines.append("- Keep generators for any figures you plan to keep in the paper; delete the rest after backing up.")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
