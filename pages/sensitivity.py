# pages/sensitivity.py
"""
Stage 5 UI — Sensitivity Analysis & Stress Testing
Investor-friendly visuals: Waterfall, Heatmap, Ranked Driver Impact Bars.
No raw tornado charts — replaced with 3 intuitive charts.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from core.sensitivity_engine import (run_1d_sensitivity, run_2d_sensitivity,
                                      run_tornado_analysis)
from utils.formatting import crore, pct
from utils.constants import COLOUR
from utils.stepper import proceed_to_stage

CHART_LAYOUT = dict(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#0f172a', size=12, family='Plus Jakarta Sans'),
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(bgcolor='rgba(0,0,0,0)'),
    xaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
    yaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
)


def page_sensitivity():
    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data'):
        st.warning('⚠️ Please fetch historical data first in the **Historical Data** tab.')
        return

    clean_data   = st.session_state['clean_data']
    drivers_data = st.session_state.get('drivers_data', {})
    drivers      = drivers_data.get('drivers', {})
    company_info = st.session_state.get('company_info', {})
    company_name = company_info.get('company_name', 'Company')

    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 5: Sensitivity &amp; Stress Testing — {company_name}
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            How sensitive is the business to each driver? Three investor-friendly views below.
        </p>
    </div>
    """, unsafe_allow_html=True)

    base_assumptions = {
        'revenue_growth':     float(drivers.get('revenue_growth',     {}).get('base_forecast', 7.0)  or 7.0),
        'ebitda_margin':      float(drivers.get('ebitda_margin',      {}).get('base_forecast', 20.0) or 20.0),
        'gross_margin':       float(drivers.get('gross_margin',       {}).get('base_forecast', 40.0) or 40.0),
        'da_to_revenue':      float(drivers.get('da_to_revenue',      {}).get('base_forecast', 4.0)  or 4.0),
        'effective_tax_rate': float(drivers.get('effective_tax_rate', {}).get('base_forecast', 25.0) or 25.0),
        'capex_to_revenue':   float(drivers.get('capex_to_revenue',   {}).get('base_forecast', 5.0)  or 5.0),
        'interest_rate':      float(drivers.get('interest_rate',      {}).get('base_forecast', 6.0)  or 6.0),
        'receivable_days':    float(drivers.get('receivable_days',    {}).get('base_forecast', 45.0) or 45.0),
        'inventory_days':     float(drivers.get('inventory_days',     {}).get('base_forecast', 30.0) or 30.0),
        'payable_days':       float(drivers.get('payable_days',       {}).get('base_forecast', 40.0) or 40.0),
        'dividend_payout':    float(drivers.get('dividend_payout',    {}).get('base_forecast', 30.0) or 30.0),
        'debt_repay_rate':    0.03,
    }

    target_label_map = {
        'net_income':      'Net Income',
        'free_cash_flow':  'Free Cash Flow',
        'ebitda':          'EBITDA',
        'revenue':         'Revenue',
    }
    target_metric = st.selectbox(
        'Target Metric for Analysis',
        list(target_label_map.keys()),
        format_func=lambda x: target_label_map[x],
        index=0,
    )
    target_label = target_label_map[target_metric]

    tabs = st.tabs(['📊 Driver Impact Ranking', '🌊 Waterfall What-If', '🗺️ Sensitivity Heat Map', '📈 1D Driver Curve'])

    # ═══════════════════════════════════════════════════════════════════════════
    # Tab 1 — Driver Impact Ranking (% change, not absolute Cr)
    # ═══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown(f"### 📊 Driver Impact Ranking — Effect on {target_label}")
        st.caption("Shows what % change in Net Income/FCF occurs if each driver improves or worsens by 10%. Ranked by total sensitivity.")

        with st.spinner('Calculating driver impacts...'):
            df_t = run_tornado_analysis(clean_data, drivers, base_assumptions,
                                        target_metric=target_metric, delta_pct=10.0)

        if df_t.empty:
            st.warning("Insufficient data for sensitivity analysis.")
        else:
            # Compute % impact relative to base
            base_target = df_t['Low Target (Cr)'].mean()  # rough base
            # Recalculate: base_target from tornado engine
            base_t_val = (df_t['Low Target (Cr)'] + df_t['High Target (Cr)']).mean() / 2.0
            if base_t_val == 0:
                base_t_val = 1.0

            df_t['Upside (%)']   = ((df_t['Impact High (Cr)']) / abs(base_t_val) * 100).round(1)
            df_t['Downside (%)'] = ((df_t['Impact Low (Cr)'])  / abs(base_t_val) * 100).round(1)
            df_t['Total Swing (%)'] = (df_t['Upside (%)'] - df_t['Downside (%)']).abs().round(1)
            df_t = df_t.sort_values('Total Swing (%)', ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=df_t['Driver'],
                x=df_t['Downside (%)'],
                name='Downside (Driver −10%)',
                orientation='h',
                marker=dict(color='#ef4444', opacity=0.85),
                hovertemplate='<b>%{y}</b><br>Downside: %{x:.1f}%<extra></extra>',
            ))
            fig.add_trace(go.Bar(
                y=df_t['Driver'],
                x=df_t['Upside (%)'],
                name='Upside (Driver +10%)',
                orientation='h',
                marker=dict(color='#10b981', opacity=0.85),
                hovertemplate='<b>%{y}</b><br>Upside: %{x:.1f}%<extra></extra>',
            ))
            fig.update_layout(
                **CHART_LAYOUT,
                title=f'Driver Sensitivity — Impact on {target_label} (%)',
                barmode='overlay',
                xaxis_title=f'% Change in {target_label}',
                yaxis_title='',
                height=400,
            )
          fig.update_xaxes(gridcolor='#e2e8f0', zeroline=True, zerolinecolor='#0f172a',zerolinewidth=2)
      
            st.plotly_chart(fig, use_container_width=True)

            # Summary table
            st.markdown("**📋 Driver Sensitivity Summary**")
            summary = df_t[['Driver', 'Upside (%)', 'Downside (%)', 'Total Swing (%)']].rename(
                columns={'Total Swing (%)': 'Sensitivity Score (%)'}
            ).sort_values('Sensitivity Score (%)', ascending=False)
            st.dataframe(summary.style.background_gradient(subset=['Sensitivity Score (%)'],
                                                            cmap='RdYlGn_r'), use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Tab 2 — Waterfall What-If Chart
    # ═══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown(f"### 🌊 Waterfall What-If — Build Your Own Scenario")
        st.caption("Set each driver to its pessimistic or optimistic level and see the cumulative effect on Net Income.")

        # Slider for each driver
        col_a, col_b = st.columns(2)

        with col_a:
            rev_g_adj = st.slider('Revenue Growth Change (pp)', -10.0, 10.0, 0.0, 0.5,
                                   key='wf_rev')
            em_adj    = st.slider('EBITDA Margin Change (pp)', -8.0, 8.0, 0.0, 0.5,
                                   key='wf_em')
            tax_adj   = st.slider('Tax Rate Change (pp)', -5.0, 5.0, 0.0, 0.5,
                                   key='wf_tax')

        with col_b:
            int_adj   = st.slider('Interest Rate Change (pp)', -3.0, 3.0, 0.0, 0.25,
                                   key='wf_int')
            cap_adj   = st.slider('Capex/Revenue Change (pp)', -5.0, 5.0, 0.0, 0.5,
                                   key='wf_cap')
            rec_adj   = st.slider('Receivable Days Change', -15.0, 15.0, 0.0, 1.0,
                                   key='wf_rec')

        if st.button('🔄 Calculate Waterfall Impact', type='primary'):
            from core.forecast_engine import build_forecast

            adj_map = {
                'revenue_growth':     rev_g_adj,
                'ebitda_margin':      em_adj,
                'effective_tax_rate': tax_adj,
                'interest_rate':      int_adj,
                'capex_to_revenue':   cap_adj,
                'receivable_days':    rec_adj,
            }
            driver_labels = {
                'revenue_growth':     '📈 Revenue Growth',
                'ebitda_margin':      '💰 EBITDA Margin',
                'effective_tax_rate': '🏛️ Tax Rate',
                'interest_rate':      '🏦 Interest Rate',
                'capex_to_revenue':   '🏗️ Capex / Rev',
                'receivable_days':    '📦 Receivable Days',
            }

            with st.spinner('Building waterfall...'):
                fo_base = build_forecast(clean_data, drivers, base_assumptions,
                                         scenario='base', n_years=1)
                fy = fo_base.get('forecast_years', ['FY25'])[0]
                stmt_key = 'cash_flow' if target_metric == 'free_cash_flow' else 'income_stmt'
                base_val = float(fo_base[stmt_key].loc[fy, target_metric]) \
                           if not fo_base[stmt_key].empty else 0.0

                waterfall_measures = ['absolute']
                waterfall_x        = [f'Base {target_label}']
                waterfall_y        = [base_val]
                waterfall_colors   = ['#3b82f6']

                cumulative_assump = base_assumptions.copy()
                for dk, adj in adj_map.items():
                    if adj == 0:
                        continue
                    prev_assump = cumulative_assump.copy()
                    cumulative_assump[dk] = cumulative_assump.get(dk, 0) + adj
                    fo_step = build_forecast(clean_data, drivers, cumulative_assump,
                                             scenario='step', n_years=1)
                    step_val = float(fo_step[stmt_key].loc[fy, target_metric]) \
                               if not fo_step[stmt_key].empty else base_val
                    prev_val = waterfall_y[-1] if waterfall_measures[-1] == 'absolute' \
                               else sum(waterfall_y)
                    delta = step_val - (base_val + sum(
                        v for v, m in zip(waterfall_y[1:], waterfall_measures[1:])
                        if m == 'relative'))
                    waterfall_measures.append('relative')
                    waterfall_x.append(driver_labels.get(dk, dk))
                    waterfall_y.append(step_val - (base_val + sum(
                        v for v, m in zip(waterfall_y[1:], waterfall_measures[1:]) if m=='relative'
                    )) if False else step_val - (base_val if len(waterfall_y)==1 else
                        sum([base_val] + [v for v, m in zip(waterfall_y[1:], waterfall_measures[1:])
                                           if m == 'relative'])))

                waterfall_measures.append('total')
                waterfall_x.append(f'Final {target_label}')
                waterfall_y.append(0)

                fig_wf = go.Figure(go.Waterfall(
                    measure=waterfall_measures,
                    x=waterfall_x,
                    y=waterfall_y,
                    connector={'line': {'color': '#94a3b8'}},
                    increasing={'marker': {'color': '#10b981'}},
                    decreasing={'marker': {'color': '#ef4444'}},
                    totals={'marker':    {'color': '#3b82f6'}},
                    texttemplate='₹%{y:,.0f} Cr',
                    textposition='outside',
                ))
                fig_wf.update_layout(
                    **CHART_LAYOUT,
                    title=f'What-If Waterfall — {target_label} Impact (₹ Cr)',
                    yaxis_title='₹ Crore',
                    height=420,
                )
                st.plotly_chart(fig_wf, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Tab 3 — Sensitivity Heat Map
    # ═══════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown(f"### 🗺️ Revenue Growth × EBITDA Margin → {target_label}")
        st.caption("Each cell shows the forecasted value. Green = stronger outcome, Red = weaker. Read like a payoff matrix.")

        c1, c2 = st.columns(2)
        with c1:
            hm_driver_x = st.selectbox('X-Axis Driver', [
                'revenue_growth', 'ebitda_margin', 'capex_to_revenue', 'interest_rate'], index=0,
                format_func=lambda x: x.replace('_', ' ').title(), key='hm_x')
        with c2:
            hm_driver_y = st.selectbox('Y-Axis Driver', [
                'ebitda_margin', 'revenue_growth', 'effective_tax_rate', 'receivable_days'], index=0,
                format_func=lambda x: x.replace('_', ' ').title(), key='hm_y')

        if hm_driver_x == hm_driver_y:
            st.warning("Please select two different drivers for X and Y axes.")
        else:
            with st.spinner('Building heat map...'):
                df_2d = run_2d_sensitivity(
                    clean_data, drivers, base_assumptions,
                    driver_x=hm_driver_x, driver_y=hm_driver_y,
                    target_metric=target_metric,
                )

            if not df_2d.empty:
                vals_matrix = df_2d.values.astype(float)
                fig_hm = go.Figure(go.Heatmap(
                    z=vals_matrix,
                    x=list(df_2d.columns),
                    y=list(df_2d.index),
                    colorscale='RdYlGn',
                    colorbar=dict(title=f'{target_label} (Cr)'),
                    hoverongaps=False,
                    hovertemplate='<b>%{x}</b><br><b>%{y}</b><br>Value: ₹%{z:,.1f} Cr<extra></extra>',
                    text=[[f'₹{v:,.0f}Cr' for v in row] for row in vals_matrix],
                    texttemplate='%{text}',
                    textfont=dict(size=10),
                ))
                fig_hm.update_layout(
                    **CHART_LAYOUT,
                    title=f'{target_label} Heat Map: {hm_driver_x.replace("_"," ").title()} vs {hm_driver_y.replace("_"," ").title()}',
                    xaxis_title=hm_driver_x.replace('_', ' ').title(),
                    yaxis_title=hm_driver_y.replace('_', ' ').title(),
                    height=420,
                )
                st.plotly_chart(fig_hm, use_container_width=True)

                st.markdown("**📋 Full Matrix Table**")
                st.dataframe(df_2d.style.background_gradient(cmap='RdYlGn', axis=None),
                             use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Tab 4 — 1D Driver Curve
    # ═══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 📈 1D Driver Sensitivity Curve")
        st.caption("Shows how any single driver linearly affects key metrics across a range of values.")

        driver_key = st.selectbox('Select Driver to Vary', list(base_assumptions.keys()),
                                   format_func=lambda x: x.replace('_', ' ').title(),
                                   key='1d_driver')
        with st.spinner('Computing...'):
            df_1d = run_1d_sensitivity(clean_data, drivers, base_assumptions, driver_key=driver_key)

        if not df_1d.empty:
            fig_1d = go.Figure()
            cols_to_plot = [c for c in ['Revenue (Cr)', 'EBITDA (Cr)', 'Net Income (Cr)', 'FCF (Cr)']
                            if c in df_1d.columns]
            colors_1d = ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6']
            for i, col in enumerate(cols_to_plot):
                fig_1d.add_trace(go.Scatter(
                    x=df_1d['Driver Value'],
                    y=df_1d[col],
                    name=col,
                    mode='lines+markers',
                    line=dict(color=colors_1d[i % len(colors_1d)], width=2.5),
                    marker=dict(size=7),
                    hovertemplate=f'<b>{col}</b>: ₹%{{y:,.1f}} Cr<extra></extra>',
                ))
            fig_1d.update_layout(
                **CHART_LAYOUT,
                title=f'{driver_key.replace("_", " ").title()} vs Financial Metrics',
                xaxis_title=driver_key.replace('_', ' ').title(),
                yaxis_title='₹ Crore',
                height=400,
            )
            # Mark base value with vertical line
            base_val = base_assumptions.get(driver_key, 0)
            fig_1d.add_vline(x=base_val, line_dash='dash', line_color='#94a3b8',
                              annotation_text=f'Base: {base_val:.1f}',
                              annotation_position='top right')
            st.plotly_chart(fig_1d, use_container_width=True)

    st.markdown('---')
    proceed_to_stage(6)
