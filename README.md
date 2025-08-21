# Bitcoin Blockspace Market Analysis

A comprehensive analysis of Bitcoin's blockchain as a marketplace for transaction space, examining fee seasonality, supply dynamics, and demand elasticity.

## 📊 Live Research Report

[View the interactive research paper](./paper/blockspace_research_paper.html) - Download and open in your browser for full interactivity.

## 🔬 Analysis Components

### HODL Waves Analysis
- Current UTXO age distribution showing supply concentration
- Over 30% of Bitcoin supply unmoved for 5+ years

### Fee Seasonality Patterns
- Systematic temporal cycles in transaction costs
- Weekend discounts of 30-50%
- Optimal transaction timing insights

### Multiple Time Horizons
- Sample period analysis (Jan 2023)
- Recent patterns (Past year)
- Long-term evolution (5-year view)

## 🛠 Technical Stack

- **Data Source**: BigQuery Bitcoin public dataset
- **Analysis**: Python (Polars, pandas-gbq)
- **Visualization**: Plotly (interactive charts)
- **Documentation**: Quarto Markdown

## 📁 Repository Structure

```
├── data/
│   ├── figs/          # Interactive HTML charts + PNG exports
│   └── raw/           # Processed data (Parquet files)
├── paper/
│   ├── blockspace_research_paper.qmd    # Source document
│   ├── blockspace_research_paper.html   # Rendered report
│   └── research_report.html             # Alternative HTML version
├── scripts/
│   ├── seasonality_heatmap.py          # Fee seasonality analysis
│   ├── seasonality_heatmap_year.py     # 1-year patterns
│   ├── seasonality_heatmap_5yr.py      # 5-year patterns
│   ├── hodl_waves.py                   # UTXO age distribution
│   └── temporal_cycles_heatmap.py      # Temporal pattern analysis
├── sql/
│   ├── seasonality.sql                 # Seasonality queries
│   ├── factors.sql                     # Factor construction
│   └── temporal_cycles.sql             # Temporal analysis
└── Makefile                            # Build automation

```

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/[username]/btc-blockspace-analysis.git
   cd btc-blockspace-analysis
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   pip install -r requirements.txt
   ```

3. **Run analysis scripts**
   ```bash
   python scripts/hodl_waves.py
   python scripts/seasonality_heatmap.py
   ```

4. **View the research report**
   Open `paper/blockspace_research_paper.html` in your browser

## 📈 Key Findings

- **Supply Concentration**: 30% of Bitcoin unmoved for 5+ years
- **Temporal Patterns**: Persistent fee cycles across multiple time horizons
- **Cost Optimization**: 30-50% savings possible through timing
- **Market Evolution**: Patterns stable despite institutional adoption

## 🔍 Research Applications

- **Trading**: Optimal transaction timing strategies
- **Exchanges**: Settlement cost optimization
- **Research**: Blockchain microstructure analysis
- **Development**: Fee prediction algorithms

## 📄 Academic Citation

```bibtex
@misc{blockspace2025,
  title={The Microstructure of Decentralized Blockspace: From Congestion to Returns},
  author={[Liam Murphy]},
  year={2025},
  url={https://github.com/[username]/btc-blockspace-analysis}
}
```


## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Research conducted using public Bitcoin blockchain data via Google BigQuery.*
