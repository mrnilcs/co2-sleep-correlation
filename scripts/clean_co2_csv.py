#!/usr/bin/env python3
"""
clean_co2_csv.py

Cleans the CO₂ CSV export by:
- Removing rows with non-numeric 'state' values
- Filtering to sleep window (22:00 to 07:00, local time)
- Grouping by night and removing nights with <5 readings
- Saving the cleaned result to a new CSV file

Author: Your Name
"""

import pandas as pd
from pathlib import Path

# --- Configuration --- #
input_path = Path(__file__).resolve().parent.parent / "data" / "co2_history.csv"
output_path = input_path.parent / "co2_history_cleaned.csv"
timezone = "Europe/Helsinki"
sleep_start_hour = 22
sleep_end_hour = 7
min_readings_per_night = 5

# --- Load and Clean Raw Data --- #
df = pd.read_csv(input_path)

# Convert 'state' to numeric (CO₂ ppm)
df['state'] = pd.to_numeric(df['state'], errors='coerce')
df = df.dropna(subset=['state'])

# Convert timestamps
df['last_changed'] = pd.to_datetime(df['last_changed'], utc=True, errors='coerce')
df = df.dropna(subset=['last_changed'])
df['local_ts'] = df['last_changed'].dt.tz_convert(timezone)
df['hour'] = df['local_ts'].dt.hour

# Filter to sleep window (crosses midnight)
df = df[(df['hour'] >= sleep_start_hour) | (df['hour'] < sleep_end_hour)].copy()

# Assign night date (using 7-hour shift to match sleep night)
df['night_date'] = (df['local_ts'] - pd.Timedelta(hours=7)).dt.date

# Remove nights with <5 readings
counts = df['night_date'].value_counts()
valid_nights = counts[counts >= min_readings_per_night].index
df = df[df['night_date'].isin(valid_nights)]

# Final cleanup: round and cast state
df['state'] = df['state'].round().astype(int)

# --- Save Cleaned File --- #
df.to_csv(output_path, index=False)

print(f"✅ Cleaned file saved to: {output_path}")
print(f" - Original rows: {len(df)}")
print(f" - Retained nights with ≥{min_readings_per_night} readings: {len(valid_nights)}")
