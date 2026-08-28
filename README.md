# 📈 Advanced Financial Forecasting & Risk Analysis Engine

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B.svg)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-Machine%20Learning-F7931E.svg)
![Finance](https://img.shields.io/badge/Domain-Corporate%20Finance-008000.svg)

An end-to-end, interactive financial modeling and machine learning platform built with Python and Streamlit. This engine bridges the gap between traditional corporate finance and modern data science by automating 3-statement financial roll-forwards, applying ensemble machine learning for predictive forecasting, and stress-testing metrics with interactive sensitivity and risk dashboards.

---

## ✨ Key Features

### 🤖 Advanced ML Forecasting (`ml_forecaster.py`)
- Replaces static linear growth assumptions with a robust **Machine Learning Ensemble**.
- Combines **Ridge, ElasticNet, Huber, Random Forest, Gradient Boosting, and Extra Trees** regressors.
- Integrates **Holt's Double Exponential Smoothing** to anchor time-series trends.
- Validates models using **Time-Series Walk-Forward Cross Validation** to assign ensemble weights dynamically.
- Generates **80% Confidence Intervals** using a 200-iteration residual bootstrap.

### 📊 Data-Driven Scenario Engine (`scenario_engine.py`)
- Moves away from arbitrary standard-deviation spreads.
- Calculates **percentile-driven scenarios** (75th / 55th / 25th percentiles of actual historical performance) for Good, Base, and Bad cases.
- Utilizes a **momentum-weighted base forecast** (60% most-recent year + 40% 2-year average) to respect historical stability while responding to immediate trends.

### 🌊 Interactive Sensitivity Analysis (`sensitivity.py`)
Replaces traditional, hard-to-read tornado charts with investor-friendly visuals powered by Plotly:
- **Driver Impact Ranking:** Horizontal bar charts showing exact % upside/downside impact on Net Income.
- **Waterfall "What-If" Builder:** Interactive sliders to manually tweak margins, growth, and taxes to see step-by-step cumulative impacts.
- **Sensitivity Heatmap:** 2D matrix evaluating combinations of key drivers (e.g., Growth vs. Margin).

### 🏥 Comprehensive Risk Dashboard (`risk_analysis.py`)
- **Piotroski F-Score (9-Point):** Evaluates profitability, leverage, and efficiency with visual ✅/❌ signal cards.
- **DuPont Decomposition:** Breaks down Return on Equity (ROE) into Net Margin × Asset Turnover × Equity Multiplier.
- **5-Pillar Radar Chart & Gauge Dials:** Visualizes financial health (Altman Z-Score) across critical domains.
- **Contextual Red Flags:** Categorizes financial warnings by severity (HIGH/MEDIUM) with detailed context.

### 📰 Live Market Context (`news_fetcher.py`)
- **Strict 7-Day Feed:** Aggregates and filters corporate and sector-level macro news from the last 7 days to track live market catalysts.
- **Draggable Live Ticker:** A floating, draggable UI component displaying live stock prices and market capitalization.

---

## 🛠️ Tech Stack

- **Frontend/UI:** Streamlit, HTML/CSS/JS (for custom draggable components)
- **Data Manipulation:** Pandas, NumPy
- **Machine Learning:** Scikit-Learn
- **Visualizations:** Plotly
- **Financial Data:** `yfinance`, Google News RSS (via BeautifulSoup)

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/FinancialForecast.git
   cd FinancialForecast
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

---

## 🎯 How to Use (Workflow)

The application is designed as a guided, sequential 6-stage pipeline. Here is how you pull data and generate forecasts:

1. **Stage 1: Select Company**
   - Enter the name or ticker of an Indian public company (NSE/BSE).
   - The engine searches the live equity list, fetching the company's metadata, sector, live price, and market cap.
2. **Stage 2: Financials (Historical Data)**
   - Click to automatically pull the last 5 years of historical financial statements (Income Statement, Balance Sheet, Cash Flow).
   - The data is cleaned, standardized, and saved into the local `storage/` database for ultra-fast retrieval in the future.
3. **Stage 3: Forecast Model**
   - The engine calculates historical margins and growth drivers.
   - It generates a fully balanced 3-statement financial roll-forward based on momentum-weighted percentiles (Good, Base, and Bad scenarios).
4. **Stage 4: ML & Hybrid**
   - Run the machine learning ensemble on the pulled historical data to project future metrics (Revenue, EBITDA, FCF).
   - Compare the traditional accounting-based forecast with the AI-driven predictions.
5. **Stage 5: Sensitivity**
   - Stress-test the business model. Use the interactive sliders to manually adjust assumptions like revenue growth, margins, or tax rates.
   - Instantly see the impact rendered on the Waterfall What-If chart and 2D Heatmaps.
6. **Stage 6: Risk Score**
   - Review the automated financial health scorecard.
   - Check the Altman Z-Score, Piotroski F-Score, and review any automatically generated "Red Flag" warnings for liquidity or leverage issues.

---

## 📂 Project Structure

```text
FinancialForecast/
├── app.py                     # Main Streamlit application entry point
├── core/                      # Core backend logic
│   ├── driver_analyzer.py     # Extracts historical margins, ratios, and trends
│   ├── forecast_engine.py     # 3-statement financial roll-forward math
│   ├── ml_forecaster.py       # Advanced machine learning ensemble pipeline
│   ├── news_fetcher.py        # Yahoo/Google news aggregator & sentiment
│   ├── risk_engine.py         # Z-Score, F-Score, and DuPont calculations
│   └── scenario_engine.py     # Percentile-based scenario generation
├── pages/                     # Streamlit frontend views (UI)
│   ├── company_search.py      # Phase 1: Ticker lookup
│   ├── historical_data.py     # Phase 2: Statement extraction
│   ├── forecast.py            # Phase 3: Base scenario modeling
│   ├── ml_forecast.py         # Phase 4: ML dashboard
│   ├── sensitivity.py         # Phase 5: What-If & heatmaps
│   └── risk_analysis.py       # Phase 6: Financial health scorecard
├── utils/                     # Helpers
│   ├── constants.py           # Financial thresholds and UI colors
│   ├── formatting.py          # Currency and metric formatters
│   └── stepper.py             # Global UI navigation state
└── storage/                   # Local SQLite DB / JSON caching
```

---

## 🔮 Future Roadmap

- **Deep Learning Integration:** Explore LSTMs and Transformers for highly complex, multi-variate time-series predictions.
- **TradingView Integration:** Pull in advanced charting and technical indicators to overlay fundamental analysis with market sentiment.
- **Alternative Data Feeds:** Incorporate broader macroeconomic indicators, interest rate curves, and global sector data to refine contextual ML weights.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/yourusername/FinancialForecast/issues).

## 📄 License
This project is [MIT](LICENSE) licensed.
