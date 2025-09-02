#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/make_snapshot.sh [YYYY-MM-DD]
DATE_INPUT=${1:-$(date -u +%F)}
SNAP_DIR="paper/assets_snapshot_${DATE_INPUT}"
OLD_DIR="paper/assets_snapshot_2025-08-28"
mkdir -p "$SNAP_DIR"

# List of asset basenames we want in the snapshot (match previous snapshot contents)
assets=(
  btc_anova_summary_interactive.html
  btc_anova_summary_table.csv
  btc_regression_coeffs_interactive.html
  btc_regression_coeffs_table.csv
  btc_weekday_lead_dashboard.html
  daily_monday_effect.html
  daily_monday_gap_rolling.html
  fee_overpayment_patterns_1yr_interactive.html
  fee_overpayment_patterns_3yr_interactive.html
  fee_overpayment_patterns_5yr_interactive.html
  heatmap_month_weekday_returns.html
  mempool_heatmap.html
  seasonality_heatmap_5yr.html
  seasonality_heatmap_year.html
  weekend_gap_violin.png
  weekly_fri_to_fri_hist.png
)

COPIED=()
for name in "${assets[@]}"; do
  src=""
  if [ -f "data/figs/$name" ]; then
    src="data/figs/$name"
  elif [ -f "$OLD_DIR/$name" ]; then
    src="$OLD_DIR/$name"
  fi
  if [ -n "$src" ]; then
    cp -f "$src" "$SNAP_DIR/$name"
    COPIED+=("$src")
  fi
done

# Always include the current paper styles for reproducibility
if [ -f "paper/styles.scss" ]; then
  cp -f "paper/styles.scss" "$SNAP_DIR/styles.scss"
  COPIED+=("paper/styles.scss")
fi

# Build manifest
{
  echo "Snapshot manifest for $SNAP_DIR"
  echo "Created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "Root: $(pwd)"
  echo ""
  echo "Files:"
  for src in "${COPIED[@]}"; do
    base=$(basename "$src")
    size=$(wc -c < "$src" | tr -d ' ')
    mtime=$(date -r "$src" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || stat -c '%y' "$src" 2>/dev/null | cut -d. -f1 | tr ' ' 'T')
    if command -v sha256sum >/dev/null 2>&1; then
      hash=$(sha256sum "$src" | awk '{print $1}')
    else
      hash="(sha256sum not available)"
    fi
  printf -- "- %s\n  source: %s\n  size: %s bytes\n  modified: %s\n  sha256: %s\n\n" "$base" "$src" "$size" "$mtime" "$hash"
  done
} > "$SNAP_DIR/manifest.txt"

# Remove the old snapshot folder if present
if [ -d "$OLD_DIR" ]; then
  rm -rf "$OLD_DIR"
fi

# Print summary
printf -- "Created %s with %d files\n" "$SNAP_DIR" "${#COPIED[@]}"
ls -1 "$SNAP_DIR" | sed 's/^/ - /'
