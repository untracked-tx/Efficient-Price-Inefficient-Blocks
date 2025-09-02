#!/usr/bin/env python3
"""
Complete pipeline for Large Transaction Timing analysis.
Pulls data from BigQuery and creates visualization.
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{description}")
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run complete Large Transaction Timing pipeline")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--years", type=int, default=3, help="Years of data")
    parser.add_argument("--min_btc", type=float, default=100, help="Minimum BTC threshold")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    
    # Step 1: Pull data from BigQuery
    pull_cmd = [
        sys.executable, 
        str(base_dir / "scripts" / "pull_large_transaction_timing.py"),
        "--project", args.project,
        "--years", str(args.years),
        "--min_btc", str(args.min_btc)
    ]
    
    if not run_command(pull_cmd, "Step 1: Pulling large transaction data from BigQuery"):
        return 1
    
    # Step 2: Create visualization
    viz_cmd = [
        sys.executable,
        str(base_dir / "scripts" / "visualize_large_transaction_timing.py"),
        "--min_btc", str(args.min_btc)
    ]
    
    if not run_command(viz_cmd, "Step 2: Creating heatmap visualization"):
        return 1
    
    print("\n✅ Large Transaction Timing pipeline completed successfully!")
    print(f"📊 Check data/figs/large_transaction_timing_heatmap.png for the visualization")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
