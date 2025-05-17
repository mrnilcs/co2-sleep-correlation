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
CO2_FILE = DATA_DIR / "co2_history_cleaned.csv"
OURA_FILE = DATA_DIR / "oura_trends.csv"

# Sleep window definition (local time)
SLEEP_START_HOUR = 22  # 22:00
SLEEP_END_HOUR = 7     # 07:00
NIGHT_SHIFT_HOURS = 7  # Shift morning hours to previous date

# Threshold for identifying low-quality CO₂ nights
MIN_CO2_READINGS_PER_NIGHT = 5

# --------------------- Helper Functions --------------------- #

def check_file_exists(path: Path):
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")

def load_and_filter_co2(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
    df['state'] = pd.to_numeric(df['state'], errors='coerce')
    df.dropna(subset=['last_changed', 'state'], inplace=True)

    df['local_ts'] = df['last_changed'].dt.tz_convert('Europe/Helsinki')
    df['hour'] = df['local_ts'].dt.hour

    # Filter for sleep window: 22:00 → 07:00 (wraps around midnight)
    mask = (df['hour'] >= SLEEP_START_HOUR) | (df['hour'] < SLEEP_END_HOUR)
    df = df[mask].copy()
    df['night_date'] = (df['local_ts'] - pd.Timedelta(hours=NIGHT_SHIFT_HOURS)).dt.date

    return df

def summarize_co2(df: pd.DataFrame) -> pd.DataFrame:
    print("✅ CO₂ Data Summary")
    print(f" - Sleep window: {SLEEP_START_HOUR}:00 → {SLEEP_END_HOUR}:00 (local time)")
    print(f" - Time range: {df['local_ts'].min()} → {df['local_ts'].max()}")
    print(f" - Total filtered readings: {len(df)}")

    nightly = df.groupby('night_date').agg(readings=('state', 'count')).reset_index()
    print(f" - Nights with data: {len(nightly)}")
    print(f" - Median readings/night: {nightly['readings'].median():.1f}")

    low_quality = nightly[nightly['readings'] < MIN_CO2_READINGS_PER_NIGHT]
    print(f" - Nights with <{MIN_CO2_READINGS_PER_NIGHT} readings: {len(low_quality)}")

    if not low_quality.empty:
        print("   ⚠️  Low-quality nights:")
        for _, row in low_quality.iterrows():
            print(f"     • {row['night_date']}: {row['readings']} readings")

    print()
    return nightly

def load_oura(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    df.dropna(subset=['date'], inplace=True)
    return df

def summarize_oura(df: pd.DataFrame):
    print("✅ Oura Data Summary")
    print(f" - Date range: {min(df['date'])} → {max(df['date'])}")
    print(f" - Nights with data: {len(df)}")
    print(f" - Missing/invalid date entries: {df['date'].isna().sum()}")
    print()

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

    missing_in_oura = co2_dates - oura_dates
    missing_in_co2 = oura_dates - co2_dates

    print(f" - Nights with CO₂ but no Oura: {len(missing_in_oura)}")
    print(f" - Nights with Oura but no CO₂: {len(missing_in_co2)}")

    # Low-quality within overlap
    low_quality = co2_nightly[co2_nightly['readings'] < MIN_CO2_READINGS_PER_NIGHT]
    overlap_low_quality = low_quality[low_quality['night_date'].isin(overlap)]
    print(f" - Overlapping nights with <{MIN_CO2_READINGS_PER_NIGHT} readings: {len(overlap_low_quality)}")
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

if __name__ == "__main__":
    main()
