#!/usr/bin/env python3
"""
Test script to verify dual PNG/HTML output functionality.
This can be used to test without running expensive BigQuery operations.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))
from viz_utils import save_dual_output, create_heatmap_html

def test_dual_output():
    """Test the dual output functionality with sample data."""
    print("🧪 Testing dual PNG/HTML output functionality...")
    
    # Create sample heatmap data
    import matplotlib.pyplot as plt
    
    # Sample data: 7 days x 24 hours
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours = list(range(24))
    data = np.random.rand(7, 24) * 100  # Random data for testing
    
    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(data, aspect="auto", cmap="viridis")
    
    # Add labels
    ax.set_xticks(range(24))
    ax.set_xticklabels([str(h) for h in hours])
    ax.set_yticks(range(7))
    ax.set_yticklabels(days)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Day of Week")
    ax.set_title("Test Heatmap - Dual Output")
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Test Values")
    
    plt.tight_layout()
    
    # Test the dual output function
    try:
        save_dual_output(fig, "test_heatmap", title="Test Dual Output")
        print("✅ Basic dual output test passed")
    except Exception as e:
        print(f"❌ Basic dual output test failed: {e}")
        return False
    
    # Test interactive heatmap
    try:
        html_path = Path("data/figs/test_interactive_heatmap.html")
        success = create_heatmap_html(
            data=data,
            x_labels=[str(h) for h in hours],
            y_labels=days,
            title="Test Interactive Heatmap",
            output_path=html_path
        )
        
        if success:
            print("✅ Interactive heatmap test passed")
        else:
            print("⚠️  Interactive heatmap test failed (plotly not installed)")
    except Exception as e:
        print(f"❌ Interactive heatmap test failed: {e}")
    
    plt.close()
    
    # Check if files were created
    png_path = Path("data/figs/test_heatmap.png")
    html_path = Path("data/figs/test_heatmap.html")
    
    if png_path.exists():
        print(f"✅ PNG file created: {png_path}")
    else:
        print(f"❌ PNG file not found: {png_path}")
        
    if html_path.exists():
        print(f"✅ HTML file created: {html_path}")
    else:
        print(f"⚠️  HTML file not found: {html_path}")
    
    print("\n🎯 Test completed! Check data/figs/ for test output files.")
    return True

if __name__ == "__main__":
    test_dual_output()
