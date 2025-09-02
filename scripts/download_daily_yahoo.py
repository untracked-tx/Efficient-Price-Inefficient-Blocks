import pandas as pd
import yfinance as yf
from pathlib import Path

OUT = Path("data/external/btcusd_daily.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Download full daily BTC-USD price history from Yahoo Finance (2014-present)
data = yf.download('BTC-USD', start='2014-09-17', end=None, interval='1d')
data = data.reset_index()
data = data.rename(columns={
    'Date': 'date',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'Volume': 'volume'
})
data = data[['date','open','high','low','close','volume']]
data.to_csv(OUT, index=False)
print(f"Wrote {OUT} with {len(data)} rows.")
