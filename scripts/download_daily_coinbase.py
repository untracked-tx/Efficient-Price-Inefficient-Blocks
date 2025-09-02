import requests, pandas as pd, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path("data/external/btcusd_daily.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def fetch_candles(start, end):
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": 86400  # 1 day
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    # Coinbase returns rows: [time, low, high, open, close, volume]
    cols = ["time","low","high","open","close","volume"]
    return pd.DataFrame(r.json(), columns=cols)

end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
start = end - timedelta(days=365*6)  # ~6 years; adjust if you want more
cursor = start
parts = []
while cursor < end:
    window_end = min(cursor + timedelta(days=300), end)
    parts.append(fetch_candles(cursor, window_end))
    time.sleep(0.2)  # be polite
    cursor = window_end

df = pd.concat(parts, ignore_index=True)
df["date"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.date
df = df.sort_values("date").drop_duplicates("date")
df = df[["date","open","high","low","close","volume"]]
df.to_csv(OUT, index=False)
print(f"Wrote {OUT} with {len(df)} rows.")
