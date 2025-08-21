#!/usr/bin/env python3
"""
Run a SQL file on BigQuery (Standard SQL) and write the result to a local Parquet file.

Usage:
  python scripts/run_query.py --project YOUR_PROJECT --location US --sql sql/factors.sql --out data/raw/factors.parquet
"""
import argparse
from pathlib import Path
import pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="GCP project id")
    p.add_argument("--location", default="US")
    p.add_argument("--sql", required=True, help="Path to SQL file")
    p.add_argument("--out", required=True, help="Output parquet path")
    args = p.parse_args()

    sql = Path(args.sql).read_text()

    # Lazy import to avoid forcing install if unused
    import pandas_gbq  # type: ignore

    print(f"Running query from {args.sql} ...")
    df = pandas_gbq.read_gbq(
        sql,
        project_id=args.project,
        dialect="standard",
        location=args.location,
        progress_bar_type=None
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {len(df):,} rows to {out_path} ...")
    df.to_parquet(out_path, index=False)
    print("Done.")

if __name__ == "__main__":
    main()