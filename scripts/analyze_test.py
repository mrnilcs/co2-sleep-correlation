#!/usr/bin/env python3
"""
explore_co2_vs_sleep.py
--------------------------------
Experimental correlation explorer for
  • co2_history_cleaned.csv
  • oura_trends.csv

Outputs the strongest CO₂ ↔ Oura relationships
across summary statistics and (optionally) early/late
sleep-window slices.

Author: Your Name
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, linregress

# ---------- Configuration ----------
DATA_DIR        = Path(__file__).resolve().parent.parent / "data"
CO2_FILE        = "co2_history_cleaned.csv"
OURA_FILE       = "oura_trends.csv"
TIMEZONE        = "Europe/Helsinki"
SLEEP_START_H   = 23   # 23:00
SLEEP_END_H     = 7    # 07:00 (next day)
NIGHT_SHIFT_H   = 7    # assign to previous date
EARLY_CUTOFF_H  = 3    # 23:00-02:59 = early, 03:00-06:59 = late
TOP_K           = 20   # how many rows to print
MIN_NIGHTS      = 10   # minimum overlap required
# -----------------------------------

def load_co2(full_path: Path) -> pd.DataFrame:
    df = pd.read_csv(full_path)
    df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors="coerce")
    df['state']        = pd.to_numeric(df['state'], errors="coerce")
    df.dropna(subset=['last_changed', 'state'], inplace=True)

    df['local']  = df['last_changed'].dt.tz_convert(TIMEZONE)
    df['hour']   = df['local'].dt.hour
    df['night']  = (df['local'] - pd.Timedelta(hours=NIGHT_SHIFT_H)).dt.date

    # keep only sleep-window readings
    mask = (df['hour'] >= SLEEP_START_H) | (df['hour'] < SLEEP_END_H)
    df   = df[mask]

    # early / late labels
    df['segment'] = np.where(df['hour'] < EARLY_CUTOFF_H, 'early', 'late')

    # nightly aggregates
    nightly = (
        df.groupby('night')
          .agg(mean_co2 = ('state', 'mean'),
               max_co2  = ('state', 'max'),
               std_co2  = ('state', 'std'))
          .reset_index()
          .rename(columns={'night': 'date'})
    )

    # segment aggregates
    segment = (
        df.groupby(['night', 'segment'])['state']
          .mean()
          .unstack()                      # cols: early / late
          .reset_index()
          .rename(columns={'night': 'date',
                           'early': 'early_mean_co2',
                           'late' : 'late_mean_co2'})
    )

    # combine
    return pd.merge(nightly, segment, on='date', how='left')

def load_oura(full_path: Path) -> pd.DataFrame:
    df = pd.read_csv(full_path)
    df['date'] = pd.to_datetime(df['date'], errors="coerce").dt.date
    return df.dropna(subset=['date'])

def correlate(df_sensor: pd.DataFrame, df_oura: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(df_sensor, df_oura, on='date')
    sensor_cols = ['mean_co2', 'max_co2', 'std_co2',
                   'early_mean_co2', 'late_mean_co2']
    results = []

    for s_col in sensor_cols:
        if s_col not in merged:
            continue
        X = merged[s_col]
        for o_col in merged.select_dtypes(include='number').columns:
            if o_col in sensor_cols:
                continue
            Y = merged[o_col]
            if len(Y) < MIN_NIGHTS:
                continue
            r, p = pearsonr(X, Y)
            slope, intercept, *_ = linregress(X, Y)
            results.append({
                'Sensor Stat' : s_col,
                'Sleep Metric': o_col,
                'N nights'    : len(Y),
                'r'           : round(r, 3),
                'p'           : round(p, 4),
                'slope'       : round(slope, 3)
            })

    res = pd.DataFrame(results)
    return res.sort_values('p')

def main() -> None:
    co2_path  = DATA_DIR / CO2_FILE
    oura_path = DATA_DIR / OURA_FILE

    if not co2_path.exists():
        sys.exit(f"❌ CO₂ file not found: {co2_path}")
    if not oura_path.exists():
        sys.exit(f"❌ Oura file not found: {oura_path}")

    print("📂 Data directory:", DATA_DIR)
    print("📈 Files:", CO2_FILE, "+", OURA_FILE)

    co2   = load_co2(co2_path)
    oura  = load_oura(oura_path)
    table = correlate(co2, oura)

    if table.empty:
        print("⚠️  Not enough overlapping nights for analysis.")
        return

    print(f"\n📊 Top {TOP_K} most significant correlations")
    print(table.head(TOP_K).to_string(index=False))

if __name__ == "__main__":
    main()
