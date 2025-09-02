#!/usr/bin/env python3
import argparse, subprocess, sys
from pathlib import Path

def run(cmd, title, ignore_errors=False):
    print(f"\n{'='*60}\n{title}\n{'='*60}\n$ {' '.join(cmd)}")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("❌ Error:\n", p.stderr)
        if not ignore_errors:
            return False
        print("⚠️  Continuing despite error...")
    else:
        print("✅ Success.")
        if p.stdout:
            print(p.stdout[-500:])
    return True

def main():
    ap = argparse.ArgumentParser("Run 4 Bitcoin visuals")
    ap.add_argument("--project", help="GCP project id (for BigQuery pulls)")
    ap.add_argument("--years", type=int, default=2, help="Years of chain data to pull")
    ap.add_argument("--visualize_only", action="store_true", help="Skip data pulls")
    args = ap.parse_args()

    base = Path(__file__).resolve().parent.parent
    ok = True

    # 1) Large Transaction Timing (pull + viz)
    if not args.visualize_only:
        cmd = [sys.executable, str(base/"scripts"/"pull_large_transaction_timing.py"),
               "--years", str(args.years)]
        if args.project: cmd += ["--project", args.project]
        ok &= run(cmd, "1) Pull Large Transaction Timing")
    ok &= run([sys.executable, str(base/"scripts"/"visualize_large_transaction_timing.py")],
              "1) Visualize Large Transaction Timing", ignore_errors=False)

    # 2) Block Time Variance (pull + viz)
    if not args.visualize_only:
        cmd = [sys.executable, str(base/"scripts"/"pull_block_time_variance.py"),
               "--years", str(args.years)]
        if args.project: cmd += ["--project", args.project]
        ok &= run(cmd, "2) Pull Block Time Variance")
    ok &= run([sys.executable, str(base/"scripts"/"visualize_block_time_variance.py")],
              "2) Visualize Block Time Variance", ignore_errors=False)

    # 3) Weekend Gap Analysis (viz only; uses your daily price CSV)
    ok &= run([sys.executable, str(base/"scripts"/"visualize_weekend_gap_analysis.py")],
              "3) Visualize Weekend Gap Analysis", ignore_errors=False)

    # 4) Fee Overpayment Patterns (pull + viz)
    if not args.visualize_only:
        cmd = [sys.executable, str(base/"scripts"/"pull_fee_overpayment_patterns.py"),
               "--years", str(args.years)]
        if args.project: cmd += ["--project", args.project]
        ok &= run(cmd, "4) Pull Fee Overpayment Patterns")
    ok &= run([sys.executable, str(base/"scripts"/"visualize_fee_overpayment_patterns.py")],
              "4) Visualize Fee Overpayment Patterns", ignore_errors=False)

    print("\n" + "="*60)
    print("🎉 DONE" if ok else "⚠️  Completed with errors. See logs above.")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
