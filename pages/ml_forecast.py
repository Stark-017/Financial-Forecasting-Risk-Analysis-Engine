# pages/ml_forecast.py
"""
Phase 6 & 7 UI — Machine Learning Forecasting & Hybrid Model Comparison
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from core.ml_forecaster import run_ml_forecast
from core.forecast_comparator import compare_and_blend_forecasts
from utils.formatting import crore, pct, ratio
from utils.constants import COLOUR

CHART_LAYOUT = dict(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#0f172a', size=12, family='Plus Jakarta Sans'),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor='rgba(0,0,0,0)'),
    xaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
    yaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
)


def page_ml_forecast():
    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data'):
        st.warning('⚠️ Please fetch historical data first in the **Historical Data** tab.')
        return

    clean_data = st.session_state['clean_data']
    company_info = st.session_state.get('company_info', {})
    company_name = company_info.get('company_name', 'Company')
    drivers_data = st.session_state.get('drivers_data', {})

    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 4: Machine Learning & Hybrid Forecast — {company_name}
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            Statistical time-series ML models (Ridge, Random Forest, Gradient Boosting) and hybrid model weighting against traditional financial drivers.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Run ML Forecast button
    if st.button('🚀 Run ML Models & Hybrid Blend', type='primary', use_container_width=True):
        with st.spinner('Training ML models (Ridge, Random Forest, Gradient Boosting)...'):
            ml_results = run_ml_forecast(clean_data, n_years=1)
            st.session_state['ml_results'] = ml_results
            st.session_state['max_unlocked_stage'] = max(st.session_state.get('max_unlocked_stage', 1), 5)
            st.rerun()

    if 'ml_results' not in st.session_state or not st.session_state.get('ml_results'):
        st.info('Click **Run ML Models & Hybrid Blend** to train ML algorithms.')
        return

    ml_results = st.session_state['ml_results']
    targets = ml_results.get('targets', {})
    forecast_years = ml_results.get('forecast_years', ['FY25'])

    # ── Section 1: ML Model Predictions ────────────────────────────────────────
    st.markdown('---')
    st.markdown('### 📊 ML Target Predictions')

    cols = st.columns(3)
    target_names = [('revenue', 'Revenue (Cr)', cols[0]),
                    ('ebitda', 'EBITDA (Cr)', cols[1]),
                    ('net_income', 'Net Income (Cr)', cols[2])]

    for key, label, col in target_names:
        with col:
            res = targets.get(key, {})
            preds = res.get('predictions', [0.0])
            best_model = res.get('best_model', 'N/A')
            metrics = res.get('metrics', {})
            val = preds[0] if preds else 0.0

            st.markdown(f"""
            <div style="background:{COLOUR['card_bg']}; border:1px solid {COLOUR['border']};
                        border-radius:12px; padding:18px;">
                <p style="color:#64748b; font-size:0.8rem; margin:0;">{label} ({forecast_years[0]})</p>
                <h2 style="color:{COLOUR['accent']}; margin:4px 0;">{crore(val)}</h2>
                <p style="color:#e2e8f0; font-size:0.85rem; margin:0;">Model: <b>{best_model}</b></p>
                <p style="color:#94a3b8; font-size:0.75rem; margin:4px 0 0 0;">MAE: ₹{metrics.get('mae',0):.1f} Cr | R²: {metrics.get('r2',0):.2f}</p>
            </div>
            """, unsafe_allow_html=True)

    # ── Section 2: Hybrid Model Comparison (Phase 7) ───────────────────────────
    st.markdown('---')
    st.markdown('### ⚖️ Phase 7: Hybrid Model Comparison')

    scenario_results = st.session_state.get('scenario_results', {})
    base_fo = scenario_results.get('base', {})

    if not base_fo:
        st.info('💡 Tip: Run the **Forecast** tab first to enable side-by-side Driver vs ML vs Hybrid comparison.')
    else:
        ml_weight_pct = st.slider('ML Blend Weight (%)', 0, 100, 40, 5,
                                  help="Set weight for ML forecast vs Driver-Based forecast")
        ml_weight = ml_weight_pct / 100.0

        hybrid_out = compare_and_blend_forecasts(base_fo, ml_results, ml_weight=ml_weight)
        comp_df = hybrid_out.get('comparison_df', pd.DataFrame())

        st.dataframe(comp_df, use_container_width=True)

        # Comparison Bar Chart
        fig = go.Figure()
        for idx, row in comp_df.iterrows():
            fig.add_trace(go.Bar(
                name=row['Metric'],
                x=['Driver Model', 'ML Model', 'Hybrid Blend'],
                y=[row['Driver Forecast'], row['ML Forecast'], row['Hybrid Blend']],
            ))
        fig.update_layout(barmode='group', title=dict(text='Driver vs ML vs Hybrid Forecast (Cr)', font=dict(color='#e2e8f0', size=14)),
                          **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')
    from utils.stepper import proceed_to_stage
    proceed_to_stage(5, "Proceed to Stage 5: Sensitivity & Stress Testing ➔")


if __name__ == '__main__':
    page_ml_forecast()
