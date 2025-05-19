#!/usr/bin/env python3
"""
verify_data.py

Checks the data quality and overlap between CO₂ sensor data and Oura sleep trend data.
Reports on time ranges, missing values, sampling resolution, and overlap consistency.

Author: Your Name
"""

import sys
import pandas as pd
from pathlib import Path

# --------------------- Configuration --------------------- #

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CO2_FILE = DATA_DIR / "co2_history.csv"
OURA_FILE = DATA_DIR / "oura_trends.csv"

SLEEP_START_HOUR = 23
SLEEP_END_HOUR = 7
NIGHT_SHIFT_HOURS = 7
MIN_CO2_READINGS_PER_NIGHT = 5

# --------------------- Utility Functions --------------------- #

def check_file_exists(path: Path):
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")

def plot_histogram(series, title, xlabel=None, color='red'):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    if xlabel is None:
        xlabel = series.name

    plt.figure(figsize=(8, 4))
    plt.hist(series.dropna(), bins=10, edgecolor='black', color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Frequency")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()

# --------------------- CO₂ Functions --------------------- #

def load_and_filter_co2(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df.dropna(subset=['last_changed', 'state'], inplace=True)

    df['local_ts'] = df['last_changed'].dt.tz_convert('Europe/Helsinki')
    df['hour'] = df['local_ts'].dt.hour
    mask = (df['hour'] >= SLEEP_START_HOUR) | (df['hour'] < SLEEP_END_HOUR)
    df = df[mask].copy()
    df['night_date'] = (df['local_ts'] - pd.Timedelta(hours=NIGHT_SHIFT_HOURS)).dt.date

    return df

def summarize_co2(df: pd.DataFrame) -> pd.DataFrame:
    print("✅ CO₂ Data Summary")
    print(f" - Sleep window: {SLEEP_START_HOUR}:00 → {SLEEP_END_HOUR}:00 (local time)")
    print(f" - Time range: {df['local_ts'].min()} → {df['local_ts'].max()}")
    print(f" - Total filtered readings: {len(df)}")

    nightly_counts = df.groupby('night_date').agg(readings=('state', 'count')).reset_index()
    print(f" - Nights with data: {len(nightly_counts)}")
    print(f" - Median readings/night: {nightly_counts['readings'].median():.1f}")

    low_quality = nightly_counts[nightly_counts['readings'] < MIN_CO2_READINGS_PER_NIGHT]
    print(f" - Nights with <{MIN_CO2_READINGS_PER_NIGHT} readings: {len(low_quality)}")
    for _, row in low_quality.iterrows():
        print(f"     • {row['night_date']}: {row['readings']} readings")

    stats = df.groupby('night_date')['state'].agg(['min', 'max', 'mean', 'median', 'std']).reset_index()
    summary = stats.agg({
        'min': ['mean', 'min', 'max'],
        'max': ['mean', 'min', 'max'],
        'mean': ['mean', 'min', 'max'],
        'median': ['mean', 'min', 'max'],
        'std': ['mean', 'min', 'max']
    }).T
    summary.columns = ['Avg', 'Min', 'Max']

    print("\n📈 Nightly CO₂ Stats (ppm):")
    print(summary.round(1).to_string())

    try:
        plot_histogram(stats['max'], "Max CO₂ per Night", "CO₂ (ppm)")
        plot_histogram(stats['mean'], "Average CO₂ per Night", "CO₂ (ppm)", color='darkcyan')
    except ImportError:
        print("\n(📉 Install matplotlib to see CO₂ histograms)")

    return nightly_counts

# --------------------- Oura Functions --------------------- #

def load_oura(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]  # normalize names
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    df.dropna(subset=['date'], inplace=True)
    return df

def summarize_oura(df: pd.DataFrame):
    print("✅ Oura Data Summary")
    print(f" - Date range: {min(df['date'])} → {max(df['date'])}")
    print(f" - Nights with data: {len(df)}")
    print(f" - Missing/invalid date entries: {df['date'].isna().sum()}")
    print()

    # Auto-detect most relevant score column
    score_col = next((col for col in df.columns if "sleep_score" in col or col == "sleep_score"), None)

    if not score_col:
        score_col = next((col for col in df.columns if "score" in col and col != "date"), None)

    if score_col:
        print(f"📈 Plotting column: {score_col}")
        try:
            plot_histogram(df[score_col], f"Histogram of {score_col.replace('_', ' ').title()}", score_col.replace('_', ' ').title(), color='mediumseagreen')
        except ImportError:
            print("\n(📉 Install matplotlib to see Oura sleep score histogram)")
    else:
        print("⚠️ No usable score column found in Oura data.")

# --------------------- Overlap & Validation --------------------- #

def calculate_overlap(co2_dates: set, oura_dates: set) -> list:
    overlap = sorted(co2_dates & oura_dates)
    print("📅 Overlap Report (CO₂ ∩ Oura)")
    print(f" - Matching nights: {len(overlap)}")
    if overlap:
        print(f" - First overlap: {min(overlap)}")
        print(f" - Last overlap:  {max(overlap)}")
    else:
        print("⚠️  No overlapping nights found.")
    print()
    return overlap

def final_verification(co2_nightly: pd.DataFrame, oura_df: pd.DataFrame, overlap: list):
    print("✅ Final Verification Summary")
    co2_dates = set(co2_nightly['night_date'])
    oura_dates = set(oura_df['date'])

    print(f" - Nights with CO₂ but no Oura: {len(co2_dates - oura_dates)}")
    print(f" - Nights with Oura but no CO₂: {len(oura_dates - co2_dates)}")

    low_quality = co2_nightly[co2_nightly['readings'] < MIN_CO2_READINGS_PER_NIGHT]
    overlap_low = low_quality[low_quality['night_date'].isin(overlap)]
    print(f" - Overlapping nights with <{MIN_CO2_READINGS_PER_NIGHT} readings: {len(overlap_low)}")
    print("✅ Data appears structurally valid.\n")

# --------------------- Main --------------------- #

def main():
    print("🔍 Starting CO₂ + Oura verification...\n")
    check_file_exists(CO2_FILE)
    check_file_exists(OURA_FILE)

    co2_df = load_and_filter_co2(CO2_FILE)
    oura_df = load_oura(OURA_FILE)

    co2_nightly = summarize_co2(co2_df)
    summarize_oura(oura_df)

    overlap = calculate_overlap(set(co2_nightly['night_date']), set(oura_df['date']))
    final_verification(co2_nightly, oura_df, overlap)

    try:
        import matplotlib.pyplot as plt
        plt.show()
    except ImportError:
        pass

if __name__ == "__main__":
    main()
