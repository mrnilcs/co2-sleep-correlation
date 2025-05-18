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
PLOT_DIR = Path(__file__).resolve().parent / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

def load_and_merge(target_column):
    # Load CO₂
    co2 = pd.read_csv(CO2_FILE)
    co2['last_changed'] = pd.to_datetime(co2['last_changed'], utc=True)
    co2['state'] = pd.to_numeric(co2['state'], errors='coerce')
    co2 = co2.dropna(subset=['state'])
    co2['local_time'] = co2['last_changed'].dt.tz_convert("Europe/Helsinki")
    co2['night'] = (co2['local_time'] - pd.Timedelta(hours=7)).dt.date

    # Nightly mean CO₂
    summary = co2.groupby('night')['state'].mean().reset_index()
    summary.columns = ['date', 'mean_co2']

    # Load Oura
    oura = pd.read_csv(OURA_FILE)
    oura['date'] = pd.to_datetime(oura['date']).dt.date

    # Merge and clean
    df = pd.merge(summary, oura, on='date')
    return df.dropna(subset=[target_column])

def plot_loess(df, target_column):
    x = df['mean_co2'].values
    y = df[target_column].values
    loess_fit = lowess(y, x, frac=0.3)

    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, alpha=0.5, label="Data", color="skyblue", edgecolor="k")
    plt.plot(loess_fit[:, 0], loess_fit[:, 1], label="LOESS", color="#1f77b4", linewidth=2.5)

    plt.xlabel("Mean CO₂ (ppm)")
    plt.ylabel(target_column)
    plt.title(f"{target_column} vs CO₂ (Nightly Average)")
    plt.legend()
    plt.tight_layout()

    filename = f"{target_column.replace(' ', '_').lower()}_vs_co2_nightly_avg.png"
    plt.savefig(PLOT_DIR / filename)
    plt.close()

def get_numeric_columns():
    df = pd.read_csv(OURA_FILE)
    df = df.drop(columns=[col for col in df.columns if 'date' in col.lower()])
    return df.select_dtypes(include='number').columns.tolist()

def run_all_metrics():
    metrics = get_numeric_columns()
    print(f"\n📈 Found {len(metrics)} numeric metrics to analyze...\n")

    for target_column in metrics:
        try:
            df = load_and_merge(target_column)
            if df.empty: 
                print(f"⚠️ {target_column}: No data available.")
                continue
            r, p = pearsonr(df['mean_co2'], df[target_column])
            print(f"✅ {target_column}: r={r:.3f}, p={p:.4f}")
            plot_loess(df, target_column)
        except Exception as e:
            print(f"❌ {target_column}: Error - {e}")

# --- Run ---
if __name__ == "__main__":
    run_all_metrics()
