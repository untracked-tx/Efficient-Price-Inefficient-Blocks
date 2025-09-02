"""
Utility functions for creating both PNG and HTML visualizations.
"""
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

def save_dual_output(fig, base_name, figs_dir="data/figs", title="", data=None):
    """
    Save both PNG and HTML versions of a matplotlib figure.
    
    Args:
        fig: matplotlib figure object
        base_name: base filename without extension
        figs_dir: directory for output files
        title: title for the interactive plot
        data: optional data dict for interactive features
    """
    figs_path = Path(figs_dir)
    figs_path.mkdir(parents=True, exist_ok=True)
    
    # Save PNG
    png_path = figs_path / f"{base_name}.png"
    fig.savefig(png_path, bbox_inches="tight", dpi=150)
    print(f"✅ Saved PNG: {png_path}")
    
    # Save HTML (interactive)
    try:
        html_path = figs_path / f"{base_name}.html"
        save_interactive_html(fig, html_path, title, data)
        print(f"✅ Saved HTML: {html_path}")
    except ImportError:
        print("⚠️  Install plotly for HTML output: pip install plotly")
    except Exception as e:
        print(f"⚠️  HTML output failed: {e}")

def save_interactive_html(fig, html_path, title="", data=None):
    """Convert matplotlib figure to interactive HTML using plotly."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    
    # This is a basic converter - each visualization type should implement its own
    # For now, create a simple HTML file with the matplotlib figure embedded
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: #333; text-align: center; }}
            .note {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="note">
                <p><strong>Note:</strong> This is a static HTML version. For interactive features, 
                the visualization script needs plotly-specific implementations.</p>
                <p>Generated on: {Path().resolve()}</p>
            </div>
            <div id="chart-container">
                <p>Interactive chart would be embedded here with plotly.js</p>
                <p>PNG version available as: {html_path.with_suffix('.png')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(html_path, 'w') as f:
        f.write(html_content)

def create_heatmap_html(data, x_labels, y_labels, title, output_path, colorscale='YlOrRd'):
    """Create an interactive heatmap using plotly."""
    try:
        import plotly.graph_objects as go
        import plotly.offline as pyo
        
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            colorscale=colorscale,
            hovertemplate='X: %{x}<br>Y: %{y}<br>Value: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="X Axis",
            yaxis_title="Y Axis",
            width=900,
            height=500
        )
        
        pyo.plot(fig, filename=str(output_path), auto_open=False)
        return True
    except ImportError:
        return False

def create_bar_chart_html(x_data, y_data, title, output_path, x_title="X", y_title="Y"):
    """Create an interactive bar chart using plotly."""
    try:
        import plotly.graph_objects as go
        import plotly.offline as pyo
        
        fig = go.Figure(data=[go.Bar(x=x_data, y=y_data)])
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title=y_title,
            width=900,
            height=500
        )
        
        pyo.plot(fig, filename=str(output_path), auto_open=False)
        return True
    except ImportError:
        return False

def create_line_chart_html(x_data, y_data, title, output_path, x_title="X", y_title="Y"):
    """Create an interactive line chart using plotly."""
    try:
        import plotly.graph_objects as go
        import plotly.offline as pyo
        
        fig = go.Figure(data=[go.Scatter(x=x_data, y=y_data, mode='lines+markers')])
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title=y_title,
            width=900,
            height=500
        )
        
        pyo.plot(fig, filename=str(output_path), auto_open=False)
        return True
    except ImportError:
        return False
