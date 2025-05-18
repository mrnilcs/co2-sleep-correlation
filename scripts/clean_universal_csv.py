#!/usr/bin/env python3
"""
clean_sensor_csv.py

Generic sensor CSV cleaner:
- Removes rows with non-numeric sensor values
- Converts timestamp and filters by sleep window (default 22:00–07:00)
- Groups by night and drops nights with <min readings
- Saves cleaned output as a new CSV

Author: Your Name
"""

import pandas as pd
from pathlib import Path

# --- Configuration --- #
sensor_name = "pm10"  # <- Change this to match your sensor (e.g., 'co2', 'pm10', 'temperature')
input_path = Path(__file__).resolve().parent.parent / "data" / f"{sensor_name}_history.csv"
output_path = input_path.parent / f"{sensor_name}_history_cleaned.csv"

timezone = "Europe/Helsinki"
sleep_start_hour = 22
sleep_end_hour = 7
min_readings_per_night = 5
timestamp_column = "last_changed"
value_column = "state"

# --- Load CSV --- #
df = pd.read_csv(input_path)

# --- Clean and Preprocess --- #
# Convert value column to numeric
df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
df = df.dropna(subset=[value_column])

# Parse timestamp column and convert to local time
df[timestamp_column] = pd.to_datetime(df[timestamp_column], utc=True, errors="coerce")
df = df.dropna(subset=[timestamp_column])
df["local_ts"] = df[timestamp_column].dt.tz_convert(timezone)
df["hour"] = df["local_ts"].dt.hour

# Filter rows to match sleep window (crosses midnight)
df = df[(df["hour"] >= sleep_start_hour) | (df["hour"] < sleep_end_hour)].copy()

# Assign 'night' grouping using 7-hour shift (aligns post-midnight data)
df["night_date"] = (df["local_ts"] - pd.Timedelta(hours=7)).dt.date

# Remove nights with too few readings
night_counts = df["night_date"].value_counts()
valid_nights = night_counts[night_counts >= min_readings_per_night].index
df = df[df["night_date"].isin(valid_nights)]

# Round values if they appear to be integers
if pd.api.types.is_float_dtype(df[value_column]):
    if df[value_column].dropna().between(0, 5000).all():
        df[value_column] = df[value_column].round().astype(int)

# --- Save Output --- #
df.to_csv(output_path, index=False)

# --- Summary --- #
print(f"✅ Cleaned file saved to: {output_path}")
print(f" - Original rows: {len(night_counts)} nights")
print(f" - Nights retained (≥{min_readings_per_night} readings): {len(valid_nights)}")
print(f" - Final rows: {len(df)}")
