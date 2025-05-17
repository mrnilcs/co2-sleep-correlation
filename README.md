# 📊 Investigating the Relationship Between Indoor CO₂ Levels and Sleep Quality

This project aims to explore the potential **inverse correlation between indoor carbon dioxide (CO₂) concentration during sleep and sleep quality**, as measured by the Oura ring. Elevated CO₂ levels are known to impact cognitive performance and alertness; this study investigates whether similar effects extend to overnight sleep quality in a typical home environment.

---

## 🎯 Research Objective

**Hypothesis:**  
There is a statistically significant **negative correlation** between indoor CO₂ levels during sleep and the **Sleep Score** provided by the Oura ring.

The analysis evaluates whether variations in indoor air quality—particularly CO₂ levels measured overnight—can predict or explain changes in sleep quality metrics.

---

## 🧪 Methodology

### 1. **CO₂ Data Collection**
- CO₂ values were recorded using a Home Assistant-integrated **SCD4x sensor** running ESPHome on an M5Stack StampS3.
- Sampling intervals varied (1–60 seconds) due to changes in logging configuration over time.
- Data was exported via Home Assistant’s web history endpoint as CSV: [Home Assistant Sensor readings](http://homeassistant.local:8123/history?entity_id=sensor.lounge_airq_co2&start_date=2024-05-31T21%3A00%3A00.000Z&end_date=2025-05-17T15%3A00%3A00.000Z)


### 2. **Sleep Quality Data**
- Sleep scores were manually exported from [Oura Cloud Trends](https://cloud.ouraring.com/trends), selecting the **Sleep Score** graph as the nightly quality indicator.
- Each score corresponds to one night and includes composite factors like total sleep time, restfulness, REM, and deep sleep proportion.

### 3. **Data Processing Workflow**
- Time-series resampling was applied to normalize CO₂ measurement frequency using `pandas`.
- Nighttime windows (typically 22:00–07:00) were extracted per date.
- For each night, the following metrics were computed:
- Average CO₂ level
- Maximum CO₂ concentration
- Duration above specific thresholds (e.g., >1000 ppm)
- CO₂ slope (rate of accumulation overnight)

- The CO₂ metrics were then **joined with Oura's sleep scores** by date.

### 4. **Analysis Techniques**
- Pearson and Spearman correlation coefficients
- Linear regression and residual analysis
- Outlier filtering and time-lag sensitivity tests
- Visualization of temporal patterns and scatterplots

---

## 📂 Repository Structure

```
.
├── config/                      
│   └── airq_sensor.yaml         # ESPHome YAML configuration for the CO₂ sensor
│
├── data/                        
│   ├── co2_history.csv          # CO₂ data from Home Assistant
│   └── oura_2023-09-17_2025-06-01_trends.csv  # Sleep scores from Oura Cloud
│
├── scripts/
│   ├── extract_nightly_co2.py   # Computes nightly CO₂ averages and metrics
│   └── correlate_sleep_co2.py   # Joins Oura sleep data with CO₂ data and computes correlations
│
├── notebooks/
│   └── exploratory_analysis.ipynb  # Jupyter notebook for visualization and model prototyping
│
├── docs/
│   └── plots/                   # Generated graphs and summaries
│
└── README.md
```

### 📁 `data/` Folder Details

#### `co2_history.csv`
Exported from Home Assistant history API:

```
http://homeassistant.local:8123/history?entity_id=sensor.lounge_airq_co2&start_date=2024-05-31T21%3A00%3A00.000Z&end_date=2025-05-17T15%3A00%3A00.000Z
```

**Format:**
```csv
entity_id,state,last_changed
sensor.lounge_airq_co2,646.5701957884849,2024-09-17T11:00:00.000Z
sensor.lounge_airq_co2,638.7098164233333,2024-09-17T12:00:00.000Z
sensor.lounge_airq_co2,790.7031147094444,2024-09-17T13:00:00.000Z
```

**Notes:**
- Sampling intervals vary (1–60s)
- Some records are incomplete or missing timestamps
- Gaps exist due to sensor outages or system restarts

#### `oura_2023-09-17_2025-06-01_trends.csv`

Exported manually from [https://cloud.ouraring.com/trends](https://cloud.ouraring.com/trends)

**Format:**
```csv
date,Sleep Score
2023-09-17,78
2023-09-18,81
2023-09-19,69
```

**Notes:**
- One row per night
- Some nights may be missing (e.g., device not worn)
- Dates reflect end-of-night (e.g., 2023-09-17 = sleep that ended that morning)

---

## ⚠️ Data Quality Considerations

- Timestamps between sources do **not perfectly align**
- CO₂ readings contain **gaps and changing sampling frequency**
- Sleep scores may **not be available** for all nights
- Analysis includes logic for **interpolation, smoothing, and date alignment**
```

---

