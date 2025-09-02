import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
warnings.filterwarnings('ignore')

# --- CONFIG ---
INFILE = "data/external/btcusd_daily.csv"
plt.style.use('seaborn-v0_8-whitegrid')

# --- Load and prepare data ---
df = pd.read_csv(INFILE, parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)

# Clean numeric columns
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.dropna().copy()

# Calculate returns
df["returns"] = df["close"].pct_change() * 100  # As percentage
df["log_returns"] = np.log(df["close"] / df["close"].shift(1)) * 100
df = df.dropna().copy()

# Add day of week
df["dow"] = df["date"].dt.dayofweek  # 0=Monday, 6=Sunday
df["day_name"] = df["date"].dt.day_name()

print("="*70)
print("BITCOIN DAY-OF-WEEK ANALYSIS: ANOVA & REGRESSION")
print("="*70)
print(f"Data range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Total trading days: {len(df):,}")
print(f"Mean daily return: {df['returns'].mean():.3f}%")
print(f"Daily volatility: {df['returns'].std():.2f}%")

# Define time periods to analyze
time_periods = [
    ('All Time (2014-Present)', df.index >= 0),
    ('Last 5 Years', df['date'] >= df['date'].max() - pd.Timedelta(days=365*5)),
    ('Last 2 Years', df['date'] >= df['date'].max() - pd.Timedelta(days=365*2)),
    ('Last Year', df['date'] >= df['date'].max() - pd.Timedelta(days=365)),
    ('Last 6 Months', df['date'] >= df['date'].max() - pd.Timedelta(days=180)),
]

# Store results for comparison
anova_results = []
regression_results = []
dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# --- ANALYSIS FOR EACH TIME PERIOD ---
for period_name, mask in time_periods:
    period_df = df[mask].copy()
    
    print(f"\n{'='*70}")
    print(f"PERIOD: {period_name}")
    print(f"{'='*70}")
    print(f"Date range: {period_df['date'].min().date()} to {period_df['date'].max().date()}")
    print(f"N = {len(period_df)} days")
    
    # --- 1. ANOVA ---
    print("\n1. ANOVA RESULTS:")
    print("-" * 40)
    
    # Prepare groups for ANOVA
    dow_groups = [period_df[period_df['dow'] == i]['returns'].values for i in range(7)]
    
    # Check if we have enough data for each day
    min_samples = min(len(g) for g in dow_groups)
    if min_samples < 10:
        print(f"Insufficient data (min samples per day: {min_samples})")
        continue
    
    # Perform ANOVA
    f_stat, p_value = stats.f_oneway(*dow_groups)
    
    # Calculate effect size (eta-squared)
    group_means = [np.mean(g) for g in dow_groups]
    grand_mean = period_df['returns'].mean()
    ss_between = sum(len(g) * (mean - grand_mean)**2 for g, mean in zip(dow_groups, group_means))
    ss_total = sum((period_df['returns'] - grand_mean)**2)
    eta_squared = ss_between / ss_total
    
    print(f"F-statistic: {f_stat:.4f}")
    print(f"P-value: {p_value:.6f} {'***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else ''}")
    print(f"Effect size (η²): {eta_squared:.6f} ({eta_squared*100:.3f}% of variance)")
    
    # Kruskal-Wallis (non-parametric alternative)
    kw_stat, kw_p = stats.kruskal(*dow_groups)
    print(f"\nKruskal-Wallis (non-parametric):")
    print(f"H-statistic: {kw_stat:.4f}, p-value: {kw_p:.6f}")
    
    # Day-by-day means for context
    print("\nMean returns by day:")
    day_stats = []
    for i, name in enumerate(dow_names):
        mean_ret = group_means[i]
        std_ret = np.std(dow_groups[i])
        n = len(dow_groups[i])
        day_stats.append({'Day': name, 'Mean': mean_ret, 'Std': std_ret, 'N': n})
        print(f"  {name}: {mean_ret:>7.3f}% (σ={std_ret:.2f}%, n={n})")
    
    # --- 2. REGRESSION ---
    print("\n2. REGRESSION RESULTS:")
    print("-" * 40)
    
    # OLS with Monday as baseline
    model = smf.ols("returns ~ C(dow, Treatment(0))", data=period_df)
    results = model.fit(cov_type='HAC', cov_kwds={'maxlags': 5})
    
    print(f"R-squared: {results.rsquared:.4f}")
    print(f"F-statistic: {results.fvalue:.3f} (p={results.f_pvalue:.6f})")
    
    print("\nCoefficients (vs Monday baseline):")
    for i in range(1, 7):
        coef_name = f'C(dow, Treatment(0))[T.{i}]'
        if coef_name in results.params:
            coef = results.params[coef_name]
            se = results.bse[coef_name]
            pval = results.pvalues[coef_name]
            sig = '***' if pval < 0.001 else '**' if pval < 0.01 else '*' if pval < 0.05 else ''
            print(f"  {dow_names[i]}: {coef:>7.3f}% (SE={se:.3f}, p={pval:.3f}) {sig}")
    
    # Store results
    anova_results.append({
        'Period': period_name,
        'N': len(period_df),
        'ANOVA_p': p_value,
        'KW_p': kw_p,
        'Eta_squared': eta_squared,
        'R_squared': results.rsquared,
        'Reg_F_p': results.f_pvalue
    })
    
    # Store regression coefficients
    for i in range(1, 7):
        coef_name = f'C(dow, Treatment(0))[T.{i}]'
        if coef_name in results.params:
            regression_results.append({
                'Period': period_name,
                'Day': dow_names[i],
                'Coefficient': results.params[coef_name],
                'P_value': results.pvalues[coef_name]
            })

# --- SUMMARY TABLE ---
print("\n" + "="*70)
print("SUMMARY: ANOVA & REGRESSION ACROSS TIME PERIODS")
print("="*70)

summary_df = pd.DataFrame(anova_results)
summary_df['ANOVA_sig'] = summary_df['ANOVA_p'].apply(lambda p: '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '')
summary_df['Variance_explained'] = summary_df['Eta_squared'] * 100

print("\nStatistical Significance Across Time:")
print(summary_df[['Period', 'N', 'ANOVA_p', 'ANOVA_sig', 'Variance_explained', 'R_squared']].to_string(index=False))

# --- VISUALIZATION ---
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Plot mean returns by day for each period
for idx, (period_name, mask) in enumerate(time_periods[:6]):
    if idx >= 6:
        break
    
    ax = axes[idx // 3, idx % 3]
    period_df = df[mask].copy()
    
    if len(period_df) > 100:
        means = []
        errors = []
        for i in range(7):
            day_returns = period_df[period_df['dow'] == i]['returns']
            means.append(day_returns.mean())
            errors.append(day_returns.sem() * 1.96)  # 95% CI
        
        colors = ['green' if m > 0 else 'red' for m in means]
        bars = ax.bar(dow_names, means, yerr=errors, capsize=5, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_title(f'{period_name}\n(n={len(period_df)})', fontsize=10)
        ax.set_ylabel('Mean Return (%)')
        ax.grid(True, alpha=0.3)
        
        # Add ANOVA p-value
        dow_groups = [period_df[period_df['dow'] == i]['returns'].values for i in range(7)]
        if all(len(g) > 5 for g in dow_groups):
            _, p_val = stats.f_oneway(*dow_groups)
            ax.text(0.95, 0.95, f'p={p_val:.3f}', transform=ax.transAxes, 
                   ha='right', va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

plt.suptitle('Day-of-Week Returns Across Different Time Periods', fontsize=14, y=1.02)
plt.tight_layout()
fig.savefig('data/figs/btc_regression_returns.png', dpi=150)
print('Saved: data/figs/btc_regression_returns.png')
plt.close(fig)

# --- COEFFICIENT STABILITY PLOT ---
if regression_results:
    coef_df = pd.DataFrame(regression_results)
    fig2, ax = plt.subplots(figsize=(12, 6))
    for day in dow_names[1:]:
        day_data = coef_df[coef_df['Day'] == day]
        if len(day_data) > 0:
            x_pos = list(range(len(day_data)))
            ax.plot(x_pos, day_data['Coefficient'], marker='o', label=day, linewidth=2)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax.set_xticks(range(len(time_periods)))
    ax.set_xticklabels([p[0].split('(')[0].strip() for p in time_periods], rotation=45, ha='right')
    ax.set_ylabel('Coefficient vs Monday (%)')
    ax.set_title('Regression Coefficients Across Time Periods')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig2.savefig('data/figs/btc_regression_coeffs.png', dpi=150)
    print('Saved: data/figs/btc_regression_coeffs.png')
    plt.close(fig2)

# --- KEY FINDINGS ---
print("\n" + "="*70)
print("KEY FINDINGS")
print("="*70)

# Check for consistency
significant_periods = summary_df[summary_df['ANOVA_p'] < 0.05]
print(f"\n1. STATISTICAL SIGNIFICANCE:")
print(f"   • {len(significant_periods)}/{len(summary_df)} periods show significant day-of-week effects")
print(f"   • Average variance explained: {summary_df['Variance_explained'].mean():.3f}%")
print(f"   • Maximum variance explained: {summary_df['Variance_explained'].max():.3f}%")

# Check coefficient stability
if regression_results:
    coef_df = pd.DataFrame(regression_results)
    print(f"\n2. COEFFICIENT STABILITY:")
    for day in dow_names[1:]:
        day_coefs = coef_df[coef_df['Day'] == day]['Coefficient'].values
        if len(day_coefs) > 1:
            # Check if coefficients change sign
            signs = np.sign(day_coefs)
            if not all(s == signs[0] for s in signs):
                print(f"   • {day}: Coefficients CHANGE SIGN across periods (unstable)")
            else:
                print(f"   • {day}: Consistent {'positive' if signs[0] > 0 else 'negative'} (μ={np.mean(day_coefs):.3f}%)")

print(f"\n3. PRACTICAL IMPLICATIONS:")
print(f"   • Effect sizes are {'negligible' if summary_df['Eta_squared'].max() < 0.01 else 'small'}")
print(f"   • Day-of-week explains <{summary_df['Variance_explained'].max():.1f}% of return variance")
print(f"   • Patterns {'are NOT' if len(significant_periods) < len(summary_df)/2 else 'may be'} stable across time")

print(f"\n4. RECOMMENDATION FOR FUTURE RESEARCH:")
print(f"   • Day-of-week effects are statistically weak and temporally unstable")
print(f"   • Consider investigating: volatility clustering, momentum effects, or market microstructure")
print(f"   • Focus on economic significance, not just statistical significance")

print("\n" + "="*70)