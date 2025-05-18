#!/usr/bin/env python3
"""
auto_analyze_universal_sleep.py

Computes Pearson correlations between nightly average sensor values
(e.g. CO₂ or PM10) and numeric Oura sleep metrics.

Author: Your Name
"""

import sys
import pandas as pd
from scipy.stats import pearsonr
from pathlib import Path

# --- Configuration --- #
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SENSOR_FILE = "temperature_history_cleaned.csv"
OURA_FILE = "oura_trends.csv"
TIMEZONE = "Europe/Helsinki"
SLEEP_START_HOUR = 23
SLEEP_END_HOUR = 7
NIGHT_SHIFT_HOURS = 7


def load_sensor_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df = df.dropna(subset=['last_changed', 'state'])

    df['local_ts'] = df['last_changed'].dt.tz_convert(TIMEZONE)
    df['hour'] = df['local_ts'].dt.hour

    df = df[(df['hour'] >= SLEEP_START_HOUR) | (df['hour'] < SLEEP_END_HOUR)].copy()
    df['night'] = (df['local_ts'] - pd.Timedelta(hours=NIGHT_SHIFT_HOURS)).dt.date

    nightly = df.groupby('night')['state'].mean().reset_index()
    nightly.columns = ['date', 'avg_sensor']
    return nightly


def load_oura_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    return df.dropna(subset=['date'])


def compute_correlations(nightly: pd.DataFrame, oura: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(nightly, oura, on='date')
    results = []

    for col in merged.select_dtypes(include='number').columns:
        if col == 'avg_sensor':
            continue
        x, y = merged['avg_sensor'], merged[col]
        if len(x) >= 10:
            r, p = pearsonr(x, y)
            results.append({
                'Metric': col,
                'N': len(x),
                'Pearson r': round(r, 3),
                'p-value': round(p, 4)
            })

    return pd.DataFrame(results).sort_values(by='p-value', key=lambda x: x.abs(), ascending=False)


def main():
    sensor_path = DATA_DIR / SENSOR_FILE
    oura_path = DATA_DIR / OURA_FILE

    if not sensor_path.exists():
        sys.exit(f"❌ Sensor file not found: {sensor_path}")
    if not oura_path.exists():
        sys.exit(f"❌ Oura file not found: {oura_path}")

    print(f"📂 Using data from: {DATA_DIR}")
    print(f"📈 Sensor file: {SENSOR_FILE}")

    sensor_df = load_sensor_data(sensor_path)
    oura_df = load_oura_data(oura_path)

    summary = compute_correlations(sensor_df, oura_df)

    if summary.empty:
        print("❌ Not enough data for correlation.")
    else:
        print("\n📊 Correlation Summary:")
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
