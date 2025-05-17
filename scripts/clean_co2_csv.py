#!/usr/bin/env python3
"""
clean_co2_csv.py

Cleans the CO₂ CSV export by:
- Removing rows with non-numeric 'state' values
- Converting remaining values to integers (no decimals)
- Saving the cleaned result to a new CSV file

Author: Your Name
"""

import pandas as pd
from pathlib import Path

# --- Configuration --- #
input_path = Path(__file__).resolve().parent.parent / "data" / "co2_history.csv"
output_path = input_path.parent / "co2_history_cleaned.csv"

# --- Load and Clean --- #
df = pd.read_csv(input_path)

# Convert 'state' to numeric, coercing errors to NaN
df['state'] = pd.to_numeric(df['state'], errors='coerce')

# Drop rows with invalid or missing 'state'
df = df.dropna(subset=['state'])

# Round to nearest integer and convert to int type
df['state'] = df['state'].round().astype(int)

# --- Save Cleaned File --- #
df.to_csv(output_path, index=False)

print(f"✅ Cleaned file saved to: {output_path}")
print(f" - Original rows: {len(df)}")
print(f" - Cleaned rows:  {len(df)}")
print(" - All state values are now integers.")
