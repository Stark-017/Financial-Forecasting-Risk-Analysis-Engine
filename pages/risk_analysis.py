# pages/risk_analysis.py
"""
Stage 6 UI — Risk & Financial Health Dashboard
Gauge chart, Piotroski F-Score, DuPont Decomposition, Radar Chart, Red Flags.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from core.risk_engine import (compute_altman_z_score, compute_piotroski_f_score,
                               compute_dupont, compute_health_score, flag_red_flags)
from utils.formatting import crore, pct, ratio
from utils.constants import COLOUR

CHART_LAYOUT = dict(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#0f172a', size=12, family='Plus Jakarta Sans'),
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(bgcolor='rgba(0,0,0,0)'),
)


def _gauge(value, title, min_v=0, max_v=10, thresholds=None, suffix=''):
    """Build a Plotly gauge indicator."""
    if thresholds is None:
        thresholds = [
            {'range': [min_v, max_v * 0.33], 'color': '#ef4444'},
            {'range': [max_v * 0.33, max_v * 0.67], 'color': '#f59e0b'},
            {'range': [max_v * 0.67, max_v], 'color': '#10b981'},
        ]
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=value,
        title={'text': title, 'font': {'size': 14, 'color': '#0f172a', 'family': 'Plus Jakarta Sans'}},
        number={'suffix': suffix, 'font': {'size': 28, 'color': '#0f172a'}},
        gauge={
            'axis': {'range': [min_v, max_v], 'tickwidth': 1,
                     'tickcolor': '#cbd5e1', 'tickfont': {'size': 10}},
            'bar': {'color': '#3b82f6', 'thickness': 0.25},
            'bgcolor': 'white',
            'borderwidth': 0,
            'steps': thresholds,
            'threshold': {
                'line': {'color': '#0f172a', 'width': 3},
                'thickness': 0.75,
                'value': value,
            },
        },
    ))
    fig.update_layout(**CHART_LAYOUT, height=250, margin=dict(l=20, r=20, t=60, b=10))
    return fig


def page_risk_analysis():
    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data'):
        st.warning('⚠️ Please fetch historical data first in the **Historical Data** tab.')
        return

    clean_data   = st.session_state['clean_data']
    company_info = st.session_state.get('company_info', {})
    company_name = company_info.get('company_name', 'Company')
    ratios_data  = st.session_state.get('ratios_data', {})

    is_df     = clean_data.get('income_stmt',   pd.DataFrame())
    bs_df     = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df     = clean_data.get('cash_flow',     pd.DataFrame())
    ratios_df = ratios_data.get('ratios_df',    pd.DataFrame())

    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 6: Risk &amp; Financial Health — {company_name}
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            Altman Z-Score, Piotroski F-Score, DuPont ROE Decomposition, Health Scorecard & Red Flags.
        </p>
    </div>
    """, unsafe_allow_html=True)

    mcap    = company_info.get('market_cap_cr')
    z_res   = compute_altman_z_score(is_df, bs_df, market_cap_cr=mcap)
    p_res   = compute_piotroski_f_score(is_df, bs_df, cf_df)
    h_res   = compute_health_score(is_df, bs_df, cf_df, ratios_df)
    du_res  = compute_dupont(is_df, bs_df)
    flags   = flag_red_flags(is_df, bs_df, cf_df, ratios_df)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 1: Top Score Row
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### 📊 Financial Health Overview')
    c1, c2, c3 = st.columns(3)

    # Altman Z-Score gauge
    with c1:
        z = z_res.get('z_score')
        if z is not None:
            fig_z = _gauge(
                value=min(max(z, 0), 5),
                title='Altman Z-Score',
                min_v=0, max_v=5,
                thresholds=[
                    {'range': [0,   1.81], 'color': '#fecaca'},
                    {'range': [1.81, 2.99], 'color': '#fef3c7'},
                    {'range': [2.99, 5],   'color': '#d1fae5'},
                ],
            )
            st.plotly_chart(fig_z, use_container_width=True)
            zone  = z_res.get('zone', 'Unknown')
            color = z_res.get('color', '#94a3b8')
            st.markdown(f"<div style='text-align:center; font-weight:800; color:{color}; font-size:1rem;'>{zone}</div>", unsafe_allow_html=True)
            st.caption(z_res.get('description', ''))
        else:
            st.info('Altman Z-Score: insufficient data.')

    # Piotroski F-Score gauge
    with c2:
        fs = p_res.get('f_score')
        if fs is not None:
            fig_p = _gauge(
                value=fs,
                title='Piotroski F-Score',
                min_v=0, max_v=9,
                thresholds=[
                    {'range': [0, 4],  'color': '#fecaca'},
                    {'range': [4, 7],  'color': '#fef3c7'},
                    {'range': [7, 9],  'color': '#d1fae5'},
                ],
            )
            st.plotly_chart(fig_p, use_container_width=True)
            strength = p_res.get('strength', '')
            color_p  = p_res.get('color', '#94a3b8')
            st.markdown(f"<div style='text-align:center; font-weight:800; color:{color_p}; font-size:1rem;'>{strength} ({fs}/9)</div>", unsafe_allow_html=True)
        else:
            st.info(p_res.get('strength', 'F-Score: insufficient data.'))

    # Health Score gauge
    with c3:
        hs = h_res.get('score', 50)
        fig_h = _gauge(
            value=hs,
            title='Overall Health Score',
            min_v=0, max_v=100,
            thresholds=[
                {'range': [0,  40], 'color': '#fecaca'},
                {'range': [40, 65], 'color': '#fef3c7'},
                {'range': [65, 100], 'color': '#d1fae5'},
            ],
            suffix='/100',
        )
        st.plotly_chart(fig_h, use_container_width=True)
        grade = h_res.get('grade', 'B')
        color_h = h_res.get('color', '#f59e0b')
        st.markdown(f"<div style='text-align:center; font-weight:800; color:{color_h}; font-size:1.2rem;'>Grade: {grade}</div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 2: Health Score Radar Chart
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### 🕸️ 5-Pillar Financial Health Radar')

    breakdown = h_res.get('breakdown', {})
    if breakdown:
        categories = list(breakdown.keys())
        values     = [breakdown[k] for k in categories]
        # Close the polygon
        cats_closed = categories + [categories[0]]
        vals_closed = values + [values[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=vals_closed,
            theta=cats_closed,
            fill='toself',
            fillcolor='rgba(59,130,246,0.15)',
            line=dict(color='#3b82f6', width=2.5),
            name='Health Score',
            hovertemplate='<b>%{theta}</b>: %{r:.0f}/100<extra></extra>',
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                gridcolor='#e2e8f0', tickfont=dict(size=9)),
                angularaxis=dict(gridcolor='#e2e8f0'),
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            font=dict(family='Plus Jakarta Sans', color='#0f172a'),
            height=340,
            margin=dict(l=40, r=40, t=20, b=20),
        )
        col_r, col_s = st.columns([2, 1])
        with col_r:
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_s:
            st.markdown("**Pillar Scores**")
            for pillar, score in breakdown.items():
                if score >= 70:   bar_color = '#10b981'
                elif score >= 45: bar_color = '#f59e0b'
                else:             bar_color = '#ef4444'
                st.markdown(f"""
<div style="margin:6px 0;">
    <div style="display:flex; justify-content:space-between;">
        <span style="font-size:0.82rem; font-weight:700; color:#0f172a;">{pillar}</span>
        <span style="font-size:0.82rem; font-weight:800; color:{bar_color};">{score:.0f}/100</span>
    </div>
    <div style="background:#f1f5f9; border-radius:4px; height:6px; margin-top:2px;">
        <div style="background:{bar_color}; width:{score}%; height:100%; border-radius:4px;"></div>
    </div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 3: Piotroski Signal Breakdown
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### 🏦 Piotroski F-Score — Signal Breakdown')

    signals = p_res.get('signals', {})
    if signals:
        dims = {}
        for label, (dim, val) in signals.items():
            dims.setdefault(dim, []).append((label, val))

        for dim, items in dims.items():
            st.markdown(f"**{dim}**")
            cols = st.columns(len(items))
            for col, (label, passed) in zip(cols, items):
                with col:
                    icon  = '✅' if passed else '❌'
                    color = '#10b981' if passed else '#ef4444'
                    clean_label = label.replace('✅ ', '')
                    st.markdown(f"""
<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
            padding:10px; text-align:center; border-top:3px solid {color};">
    <div style="font-size:1.4rem;">{icon}</div>
    <div style="font-size:0.72rem; font-weight:700; color:#0f172a; margin-top:4px; line-height:1.3;">{clean_label}</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 4: DuPont Decomposition
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### 🔬 DuPont ROE Decomposition')
    st.caption('ROE = Net Margin × Asset Turnover × Equity Multiplier (Financial Leverage)')

    if du_res and isinstance(du_res, dict) and 'error' not in du_res:
        du_df = pd.DataFrame(du_res).T
        du_df.index.name = 'FY'

        fig_du = go.Figure()
        colors_du = ['#3b82f6', '#10b981', '#f59e0b']
        components = [('net_margin', 'Net Margin (%)', '%'),
                      ('asset_turnover', 'Asset Turnover (×)', '×'),
                      ('equity_multiplier', 'Equity Multiplier (×)', '×')]
        for (col, lbl, unit), color in zip(components, colors_du):
            if col in du_df.columns:
                fig_du.add_trace(go.Bar(
                    x=du_df.index.tolist(),
                    y=du_df[col].tolist(),
                    name=lbl,
                    marker_color=color,
                    opacity=0.85,
                    hovertemplate=f'<b>{lbl}</b>: %{{y:.2f}}{unit}<extra></extra>',
                ))
        # ROE line
        if 'roe' in du_df.columns:
            fig_du.add_trace(go.Scatter(
                x=du_df.index.tolist(),
                y=du_df['roe'].tolist(),
                name='ROE (%)',
                mode='lines+markers',
                line=dict(color='#ef4444', width=2.5, dash='dot'),
                marker=dict(size=8),
                yaxis='y2',
                hovertemplate='<b>ROE</b>: %{y:.1f}%<extra></extra>',
            ))
        fig_du.update_layout(
            **CHART_LAYOUT,
            title='DuPont Decomposition — ROE Drivers',
            barmode='group',
            xaxis_title='Financial Year',
            yaxis=dict(title='Component Value', gridcolor='#e2e8f0'),
            yaxis2=dict(title='ROE (%)', overlaying='y', side='right',
                        showgrid=False, tickfont=dict(color='#ef4444')),
            height=380,
        )
        st.plotly_chart(fig_du, use_container_width=True)

        # DuPont table
        display_cols = {
            'net_margin': 'Net Margin (%)',
            'asset_turnover': 'Asset Turnover (×)',
            'equity_multiplier': 'Equity Multiplier (×)',
            'roe': 'ROE (%) [Decomposed]',
            'roe_check': 'ROE (%) [Actual]',
        }
        du_display = du_df[[c for c in display_cols if c in du_df.columns]].rename(columns=display_cols)
        st.dataframe(du_display.style.format('{:.2f}').background_gradient(cmap='RdYlGn', axis=None),
                     use_container_width=True)
    else:
        st.info('DuPont: Insufficient historical data (need ≥2 fiscal years).')

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 5: Altman Z-Score Component Breakdown
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### 🛡️ Altman Z-Score — Component Breakdown')

    z_comps = z_res.get('components', {})
    if z_comps:
        comp_cols = st.columns(len(z_comps))
        for col, (lbl, val) in zip(comp_cols, z_comps.items()):
            with col:
                st.metric(lbl, f'{val:.3f}')

        weights = {'X1 Working Capital / Assets': 1.2,
                   'X2 Retained Earnings / Assets': 1.4,
                   'X3 EBIT / Assets': 3.3,
                   'X4 MktCap / Total Liabilities': 0.6,
                   'X5 Revenue / Assets': 0.999}
        fig_comp = go.Figure(go.Bar(
            x=list(z_comps.keys()),
            y=[z_comps[k] * weights.get(k, 1) for k in z_comps],
            marker_color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
            text=[f'{z_comps[k] * weights.get(k, 1):+.3f}' for k in z_comps],
            textposition='outside',
        ))
        fig_comp.update_layout(
            **CHART_LAYOUT,
            title='Weighted Z-Score Components',
            xaxis_title='', yaxis_title='Weighted Contribution',
            height=320,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Section 6: Red Flags
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown('---')
    st.markdown('### ⚠️ Financial Red Flags & Warning Indicators')

    if not flags:
        st.success('✅ No critical financial red flags detected in historical statements.')
    else:
        high_flags = [f for f in flags if f['severity'] == 'HIGH']
        med_flags  = [f for f in flags if f['severity'] == 'MEDIUM']

        if high_flags:
            st.error(f"🚨 {len(high_flags)} HIGH severity flag(s) detected")
            for f in high_flags:
                with st.expander(f"🚨 {f['title']}", expanded=True):
                    st.markdown(f"**{f['message']}**")

        if med_flags:
            st.warning(f"⚠️ {len(med_flags)} MEDIUM severity flag(s) detected")
            for f in med_flags:
                with st.expander(f"⚠️ {f['title']}", expanded=False):
                    st.markdown(f['message'])
