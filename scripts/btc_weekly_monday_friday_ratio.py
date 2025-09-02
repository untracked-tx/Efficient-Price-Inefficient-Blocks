import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Load data
df = pd.read_csv('data/external/btcusd_daily.csv', parse_dates=['date'])
# Convert price columns to numeric
for col in ['open', 'high', 'low', 'close']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Ensure 'date' is sorted
if not df['date'].is_monotonic_increasing:
    df = df.sort_values('date')

# Filter for last 52 weeks (1 year)
end_date = df['date'].max()
start_date = end_date - timedelta(weeks=52)
df_year = df[df['date'] >= start_date].copy()

# Add weekday column
# Monday=0, Friday=4
df_year['weekday'] = df_year['date'].dt.weekday

# Group by week
weekly = []
for week_start in pd.date_range(start=start_date, end=end_date, freq='W-MON'):
    week_end = week_start + timedelta(days=4)  # Friday
    monday_row = df_year[df_year['date'] == week_start]
    friday_row = df_year[df_year['date'] == week_end]
    if not monday_row.empty and not friday_row.empty:
        monday_open = monday_row.iloc[0]['open']
        friday_open = friday_row.iloc[0]['open']
        ratio = (friday_open - monday_open) / monday_open
        weekly.append({
            'week_start': week_start,
            'monday_open': monday_open,
            'friday_open': friday_open,
            'ratio': ratio
        })

weekly_df = pd.DataFrame(weekly)

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=weekly_df['week_start'],
    y=weekly_df['ratio'],
    mode='lines+markers',
    line=dict(color='green'),
    marker=dict(color='red'),
    name='(Friday - Monday) / Monday'
))
fig.update_layout(
    title='Weekly BTC Price Change: (Friday Open - Monday Open) / Monday Open',
    xaxis_title='Week Start',
    yaxis_title='Ratio',
    template='plotly_white'
)

fig.write_html('data/figs/enhanced/btc_weekly_monday_friday_ratio.html', include_plotlyjs='cdn')
print('Chart saved to data/figs/enhanced/btc_weekly_monday_friday_ratio.html')
