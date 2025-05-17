#!/usr/bin/env python3
"""
auto_analyze_co2_sleep.py

Analyzes correlation between nightly CO₂ levels and all numeric Oura sleep metrics.
Automatically loads and aligns data, filters for sleep-time CO₂, computes correlations,
and plots the strongest result.

Author: Your Name
"""

import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress, t
from pathlib import Path

# --------------------- Configuration --------------------- #
CO2_FILENAME = "co2_history_cleaned.csv"
OURA_FILENAME = "oura_trends_2.csv"
SLEEP_START_HOUR = 23
NIGHT_SHIFT_HOURS = 7
TIMEZONE = "Europe/Helsinki"

# --------------------- Data Loading --------------------- #

def resolve_data_directory(user_dir: str | None) -> Path:
    if user_dir:
        path = Path(user_dir).expanduser().resolve()
    else:
        path = Path(__file__).resolve().parent.parent / "data"
    if not path.exists():
        sys.exit(f"❌ Data directory not found: {path}")
    return path

def load_and_prepare_co2(path: Path) -> pd.DataFrame:
    SLEEP_END_HOUR = 7  # filter from 23:00 to 03:00

    df = pd.read_csv(path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df = df.dropna(subset=['last_changed', 'state'])

    df['local_ts'] = df['last_changed'].dt.tz_convert(TIMEZONE)
    df['hour'] = df['local_ts'].dt.hour

    # Filter CO₂ readings from 23:00 to 03:00 (spanning midnight)
    df = df[(df['hour'] >= SLEEP_START_HOUR) | (df['hour'] < SLEEP_END_HOUR)].copy()

    # Shift timestamp back to assign CO₂ to the correct night
    df['night_date'] = (df['local_ts'] - pd.Timedelta(hours=NIGHT_SHIFT_HOURS)).dt.date

    return df.groupby('night_date').agg(
        avg_co2=('state', 'mean'),
        max_co2=('state', 'max'),
        readings=('state', 'count')
    ).reset_index().rename(columns={'night_date': 'date'})

def load_and_prepare_oura(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    return df.dropna(subset=['date'])

# --------------------- Analysis --------------------- #

def analyze_correlations(nightly: pd.DataFrame, oura: pd.DataFrame) -> pd.DataFrame:
    results = []
    numeric_cols = oura.select_dtypes(include='number').columns

    for col in numeric_cols:
        merged = pd.merge(oura[['date', col]], nightly, on='date', how='inner').dropna()
        if len(merged) < 10:
            continue
        slope, intercept, r, p_value, stderr = linregress(merged['avg_co2'], merged[col])
        ci_range = t.ppf(0.975, df=len(merged)-2) * stderr
        ci_low, ci_high = slope - ci_range, slope + ci_range

        results.append({
            'Metric': col,
            'N': len(merged),
            'Pearson r': round(r, 3),
            'R²': round(r**2, 3),
            'p-value': round(p_value, 4),
            'Slope': round(slope, 3),
            'CI Lower': round(ci_low, 3),
            'CI Upper': round(ci_high, 3)
        })

    df = pd.DataFrame(results)
    return df.sort_values(by='Pearson r', key=lambda x: x.abs(), ascending=False)

# --------------------- Visualization --------------------- #

def plot_strongest_correlation(summary: pd.DataFrame, nightly: pd.DataFrame, oura: pd.DataFrame):
    if summary.empty:
        print("No valid metrics to plot.")
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

    ci_text = f"95% CI: [{top['CI Lower']}, {top['CI Upper']}]"
    plt.title(f"{metric} vs. Avg Nighttime CO₂\n{ci_text}")
    plt.xlabel("Avg CO₂ (ppm)")
    plt.ylabel(metric)
    plt.grid(True, linestyle=':')
    plt.legend()
    plt.tight_layout()

    output_path = Path(__file__).resolve().parent.parent / "plots" / f"co2_vs_{metric.replace(' ', '_').lower()}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.show()

# --------------------- Main --------------------- #

def main():
    parser = argparse.ArgumentParser(description="Analyze nightly CO₂ vs Oura sleep metrics")
    parser.add_argument("--data-dir", help="Path to your data folder")
    args = parser.parse_args()

    data_dir = resolve_data_directory(args.data_dir)
    co2_path = data_dir / CO2_FILENAME
    oura_path = data_dir / OURA_FILENAME

    if not co2_path.exists():
        sys.exit(f"❌ Missing file: {co2_path}")
    if not oura_path.exists():
        sys.exit(f"❌ Missing file: {oura_path}")

    print(f"📂 Using data from: {data_dir}")
    nightly = load_and_prepare_co2(co2_path)
    oura = load_and_prepare_oura(oura_path)

    summary = analyze_correlations(nightly, oura)

    print("\n📊 Correlation Summary:")
    if summary.empty:
        print("No correlations found.")
    else:
        print(summary.to_string(index=False))

        # Show merged data used for strongest correlation
        top_metric = summary.iloc[0]['Metric']
        merged_data = pd.merge(
            oura[['date', top_metric]], nightly, on='date', how='inner'
        ).dropna()

        print("\n📄 Data used for strongest correlation (top 10 rows):")
        print(merged_data.sort_values(by=top_metric, ascending=False).head(10).to_string(index=False))

        print("\n📄 Data used for strongest correlation (bottom 10 rows):")
        print(merged_data.sort_values(by=top_metric, ascending=True).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
