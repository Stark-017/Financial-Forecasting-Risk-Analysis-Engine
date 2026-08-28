# pages/about.py
"""
About page — project information
"""

import streamlit as st


def page_about():
    st.markdown("""
    <h1 style='color:#e2e8f0; font-size:2rem; font-weight:800;'>About This System</h1>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#141c2e,#0b0f1e); border:1px solid #1e2d45;
                border-radius:16px; padding:28px; margin-bottom:20px;">
        <h2 style="color:#3b82f6; font-weight:700;">Corporate Financial Forecasting System</h2>
        <p style="color:#94a3b8;">A driver-based, three-statement integrated financial model for Indian listed companies.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 🎯 What This System Does

    This system takes any NSE or BSE listed company and:

    1. **Phase 1** — Searches and verifies the company on NSE/BSE
    2. **Phase 2** — Retrieves 4–5 years of historical Income Statement, Balance Sheet, and Cash Flow data
    3. **Phase 3** — Analyses historical financial drivers (growth rates, margins, working capital ratios, leverage)
    4. **Phase 4** — Builds a fully integrated 3-statement financial model using those drivers
    5. **Phase 5** — Runs Good, Base, and Bad economic scenarios using sigma-based driver adjustments

    ### 📊 Data Sources

    | Source | Usage |
    |--------|-------|
    | Yahoo Finance (yfinance) | Primary source: 4 years of annual financials |
    | Screener.in | Supplementary: older years, gap filling |
    | NSE EQUITY_L.csv | Company verification & fuzzy search |

    ### ⚙️ Technical Stack

    - **Frontend**: Streamlit + Plotly
    - **Data**: yfinance, pandas, numpy
    - **Search**: rapidfuzz (fuzzy matching)
    - **Storage**: SQLite
    - **Language**: Python 3.10+

    ### ⚠️ Disclaimer
    This system is for educational and research purposes only. It does not constitute financial advice.
    All forecasts are model-generated and involve significant uncertainty.
    """)


if __name__ == '__main__':
    page_about()
