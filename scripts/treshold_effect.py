import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.stats import pearsonr
from pathlib import Path

# --- Configuration ---
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CO2_FILE = DATA_DIR / "co2_history.csv"
OURA_FILE = DATA_DIR / "oura_trends.csv"
TARGET_COLUMN = "Restfulness Score"  # ← Change this to "REM Sleep Duration", "Respiratory Rate", etc.

#date,Total Sleep Score,Lowest Resting Heart Rate,Awake Time,Restfulness Score,Bedtime End,Sleep Efficiency Score,REM Sleep Score,Restless Sleep,Light Sleep Duration,Sleep Efficiency,Sleep Latency,Respiratory Rate,Bedtime Start,Sleep Latency Score,REM Sleep Duration,Total Sleep Duration,Average Resting Heart Rate,Sleep Timing,Total Bedtime ,Sleep Timin Score,Deep Sleep Score,Sleep Score,Deep Sleep Duration

TIME_WINDOWS = {
    "full_night": (23, 7),
    "early_night": (23, 3),
    "late_night": (3, 7),
    "very_early": (22, 23),
    "mid_night": (1, 5),
}

def load_and_merge(start_h, end_h):
    co2 = pd.read_csv(CO2_FILE)
    co2['last_changed'] = pd.to_datetime(co2['last_changed'], utc=True)
    co2['state'] = pd.to_numeric(co2['state'], errors='coerce')
    co2 = co2.dropna(subset=['state'])
    co2['local_time'] = co2['last_changed'].dt.tz_convert("Europe/Helsinki")
    co2['hour'] = co2['local_time'].dt.hour
    co2['night'] = (co2['local_time'] - pd.Timedelta(hours=7)).dt.date

    if start_h < end_h:
        co2 = co2[(co2['hour'] >= start_h) & (co2['hour'] < end_h)]
    else:
        co2 = co2[(co2['hour'] >= start_h) | (co2['hour'] < end_h)]

    summary = co2.groupby('night')['state'].mean().reset_index()
    summary.columns = ['date', 'mean_co2']

    oura = pd.read_csv(OURA_FILE)
    oura['date'] = pd.to_datetime(oura['date']).dt.date

    df = pd.merge(summary, oura, on='date')
    return df.dropna(subset=[TARGET_COLUMN])

def plot_loess(df, label):
    x = df['mean_co2'].values
    y = df[TARGET_COLUMN].values
    loess_fit = lowess(y, x, frac=0.3)

    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, alpha=0.5, label="Data", color="skyblue", edgecolor="k")
    plt.plot(loess_fit[:, 0], loess_fit[:, 1], label="LOESS", color="#1f77b4", linewidth=2.5)

    plt.xlabel("Mean CO₂ (ppm)")
    plt.ylabel(TARGET_COLUMN)
    plt.title(f"{TARGET_COLUMN} vs CO₂ ({label.replace('_', ' ').title()})")
    plt.legend()
    plt.tight_layout()
    plt.show()

def compare_windows():
    results = []
    for label, (start, end) in TIME_WINDOWS.items():
        df = load_and_merge(start, end)
        if df.empty: continue

        r, p = pearsonr(df['mean_co2'], df[TARGET_COLUMN])
        results.append({
            'Window': label,
            'Start': start,
            'End': end,
            'Nights': len(df),
            'r': round(r, 3),
            'p': round(p, 4)
        })

    results_df = pd.DataFrame(results).sort_values(by='r', key=np.abs, ascending=False)
    print(f"\n🧪 Correlation between CO₂ and {TARGET_COLUMN} by Time Window:")
    print(results_df.to_string(index=False))
    return results_df

# --- Run ---
if __name__ == "__main__":
    results_df = compare_windows()
    selected_label = results_df.iloc[0]['Window']  # Pick the most correlated window automatically

    if selected_label in TIME_WINDOWS:
        start_h, end_h = TIME_WINDOWS[selected_label]
        df = load_and_merge(start_h, end_h)
        plot_loess(df, selected_label)
