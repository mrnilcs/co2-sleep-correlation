#!/usr/bin/env python3
"""
auto_analyze_co2_sleep.py

This script analyzes correlations between nightly indoor CO₂ levels and
all numeric sleep metrics exported from Oura Cloud Trends.

- Automatically locates the ../data folder relative to script location.
- Accepts an optional --data-dir to override the path.
- Prints a summary of correlation results.
- Visualizes the strongest correlation (by absolute Pearson r).

Author: Your Name
"""

import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path

def resolve_data_directory(user_dir: str | None) -> Path:
    """Determine data directory from CLI input or default relative path."""
    if user_dir:
        data_dir = Path(user_dir).expanduser().resolve()
    else:
        # Default to ../data relative to this script
        data_dir = Path(__file__).resolve().parent.parent / "data"
    if not data_dir.exists():
        sys.exit(f"❌ Data directory not found: {data_dir}")
    return data_dir

def load_and_prepare_co2(co2_path: Path) -> pd.DataFrame:
    """Load and preprocess CO₂ time series from Home Assistant."""
    df = pd.read_csv(co2_path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df = df.dropna(subset=['last_changed', 'state'])
    df['local_ts'] = df['last_changed'].dt.tz_convert('Europe/Helsinki')

    # Filter for sleep window: 22:00–07:00 (assign to previous night)
    mask = (df['local_ts'].dt.hour >= 4) | (df['local_ts'].dt.hour < 9)
    df = df[mask].copy()
    df['night_date'] = (df['local_ts'] - pd.Timedelta(hours=7)).dt.date

    return df.groupby('night_date').agg(
        avg_co2=('state', 'mean'),
        max_co2=('state', 'max')
    ).reset_index().rename(columns={'night_date': 'date'})

def load_and_prepare_oura(oura_path: Path) -> pd.DataFrame:
    """Load Oura trend data and extract numeric metrics with valid dates."""
    df = pd.read_csv(oura_path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    return df.dropna(subset=['date'])

def analyze_correlations(nightly: pd.DataFrame, oura: pd.DataFrame) -> pd.DataFrame:
    """Merge and compute correlations for all numeric sleep metrics."""
    results = []
    numeric_cols = oura.select_dtypes(include='number').columns

    for col in numeric_cols:
        merged = pd.merge(oura[['date', col]], nightly, on='date', how='inner').dropna()
        if len(merged) < 10:
            continue  # skip low-sample metrics
        slope, intercept, r_value, p_value, std_err = linregress(merged['avg_co2'], merged[col])
        results.append({
            'Metric': col,
            'N': len(merged),
            'Pearson r': round(r_value, 3),
            'R²': round(r_value**2, 3),
            'p-value': round(p_value, 4),
            'Slope': round(slope, 3),
        })

    return pd.DataFrame(results).sort_values('Pearson r')

def plot_strongest_correlation(summary: pd.DataFrame, nightly: pd.DataFrame, oura: pd.DataFrame):
    """Plot and save the strongest (most negative) correlation found."""
    if summary.empty:
        print("No sufficient data for plotting.")
        return

    top = summary.iloc[0]
    metric = top['Metric']
    merged = pd.merge(oura[['date', metric]], nightly, on='date', how='inner').dropna()

    slope = top['Slope']
    intercept = linregress(merged['avg_co2'], merged[metric]).intercept

    plt.figure(figsize=(8, 5))
    plt.scatter(merged['avg_co2'], merged[metric], alpha=0.7, label='Nightly data')
    plt.plot(merged['avg_co2'], slope * merged['avg_co2'] + intercept,
             color='orange', label=f"Fit line (r={top['Pearson r']})")

    plt.title(f"{metric} vs. Avg Nighttime CO₂")
    plt.xlabel("Average Nighttime CO₂ (ppm)")
    plt.ylabel(metric)
    plt.grid(True, linestyle=':')
    plt.legend()
    plt.tight_layout()
    output_path = Path('docs') / f"co2_vs_{metric.replace(' ', '_').lower()}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Analyze CO₂ vs Oura sleep metrics")
    parser.add_argument("--data-dir", help="Path to your data folder (default: ../data)")
    args = parser.parse_args()

    data_dir = resolve_data_directory(args.data_dir)
    co2_path = data_dir / "co2_history.csv"
    oura_path = data_dir / "annika_oura_2024-09-19_2025-05-17_trends.csv"

    if not co2_path.exists() or not oura_path.exists():
        sys.exit(f"❌ Missing file(s) in: {data_dir}")

    print(f"📂 Using data from: {data_dir}")
    nightly = load_and_prepare_co2(co2_path)
    oura = load_and_prepare_oura(oura_path)
    summary = analyze_correlations(nightly, oura)

    print("\n📊 Correlation Summary:")
    if summary.empty:
        print("No valid correlations found.")
    else:
        print(summary.to_string(index=False))
        plot_strongest_correlation(summary, nightly, oura)

if __name__ == "__main__":
    main()
