# pages/historical_data.py
"""
Phase 2 UI — Historical Financial Data Collection, Cleaning, Validation & Executive Summary
Schematiq Design: Clean Typography, Vibrant Plotly Graphics, Color-Coded P&L & Executive Pros/Cons.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from core.data_fetcher import fetch_all_financials
from core.data_cleaner import clean_financial_data
from core.data_validator import run_all_validations
from core.ratio_calculator import compute_ratios
from utils.formatting import crore, pct, ratio
from utils.constants import COLOUR
from utils.stepper import proceed_to_stage


@st.cache_data(ttl=1800, show_spinner=False)   # cache 30 mins per ticker
def _cached_fetch(ticker_symbol: str, company_info_str: str) -> dict:
    """Cache-friendly wrapper around fetch_all_financials."""
    import json
    company_info = json.loads(company_info_str)
    return fetch_all_financials(company_info)

CHART_LAYOUT = dict(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#0f172a', size=12, family='Plus Jakarta Sans'),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor='rgba(0,0,0,0)'),
    xaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
    yaxis=dict(gridcolor='#e2e8f0', linecolor='#cbd5e1'),
)


def status_badge(status):
    colors = {'PASS': '#059669', 'WARN': '#d97706', 'FAIL': '#dc2626'}
    icons  = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}
    c = colors.get(status, '#64748b')
    i = icons.get(status, '—')
    return f"<span style='color:{c}; font-weight:700;'>{i} {status}</span>"


def style_financial_df(df: pd.DataFrame):
    """
    Smart P&L styling:
    - Focuses color highlighting specifically on key metrics (Revenue, EBITDA, Net Income, Gross Profit, FCF).
    - YoY Growth / Higher than prior year -> Soft Green highlight (#059669).
    - YoY Decline / Net Loss -> Soft Red highlight (#dc2626).
    - Non-key line items remain clean to prevent visual clutter.
    """
    if df.empty:
        return df

    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    key_keywords = ['revenue', 'ebitda', 'ebit', 'net_income', 'gross_profit', 'total_revenue', 'net_profit', 'free_cash_flow', 'cash_from_operations']

    for col in df.columns:
        col_clean = str(col).lower().strip()
        is_key = any(km in col_clean for km in key_keywords)
        if not is_key:
            continue

        series = df[col]
        for i in range(len(series)):
            val = series.iloc[i]
            if pd.isna(val):
                continue
            try:
                v = float(val)
                # Compare with previous year if available
                if i > 0 and pd.notna(series.iloc[i - 1]):
                    prev_v = float(series.iloc[i - 1])
                    if v > prev_v and v > 0:
                        style_df.iloc[i, df.columns.get_loc(col)] = 'color: #059669; font-weight: 700; background-color: rgba(16, 185, 129, 0.14);'
                    elif v < prev_v or v < 0:
                        style_df.iloc[i, df.columns.get_loc(col)] = 'color: #dc2626; font-weight: 700; background-color: rgba(239, 68, 68, 0.14);'
                else:
                    if v > 0:
                        style_df.iloc[i, df.columns.get_loc(col)] = 'color: #059669; font-weight: 700; background-color: rgba(16, 185, 129, 0.08);'
                    elif v < 0:
                        style_df.iloc[i, df.columns.get_loc(col)] = 'color: #dc2626; font-weight: 700; background-color: rgba(239, 68, 68, 0.14);'
            except (ValueError, TypeError):
                pass

    styler = df.style
    def _apply_styles(data):
        return style_df

    return styler.apply(_apply_styles, axis=None).format('{:,.1f}', na_rep='N/A')


def bar_chart(df: pd.DataFrame, col: str, title: str, color=None):
    if col not in df.columns:
        st.info(f'{col} not available')
        return
    fig = go.Figure()
    vals = df[col].fillna(0)
    default_colors = ['#ff7e5f' if v >= 0 else '#dc2626' for v in vals]
    fig.add_trace(go.Bar(
        x=df.index, y=vals,
        marker_color=color or default_colors,
        text=[crore(v) for v in vals], textposition='outside',
        textfont=dict(size=11, color='#0f172a', family='Plus Jakarta Sans'),
        marker=dict(line=dict(width=0)),
    ))
    fig.update_layout(title=dict(text=title, font=dict(color='#0f172a', size=14, family='Plus Jakarta Sans')),
                      **CHART_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def line_chart(df: pd.DataFrame, cols: list, title: str, unit='%'):
    colors = ['#0f172a', '#059669', '#d97706', '#8b5cf6', '#ec4899']
    fig = go.Figure()
    for i, col in enumerate(cols):
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=col.replace('_', ' ').title(),
                mode='lines+markers',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=7),
            ))
    fig.update_layout(title=dict(text=title, font=dict(color='#0f172a', size=14, family='Plus Jakarta Sans')),
                      **CHART_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def render_pros_and_cons(clean_data: dict, ratios_data: dict):
    """Render Executive Pros & Cons Summary cards."""
    is_df = clean_data.get('income_stmt', pd.DataFrame())
    bs_df = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df = clean_data.get('cash_flow', pd.DataFrame())
    ratios_df = ratios_data.get('ratios_df', pd.DataFrame())
    summary = ratios_data.get('summary', {})

    pros = []
    cons = []

    # 1. Top-line Revenue Growth
    cagr_val = summary.get('revenue_cagr')
    if cagr_val is not None:
        if cagr_val > 10.0:
            pros.append(f"<b>Strong Revenue Growth:</b> Delivered a 5-year Revenue CAGR of <b>{cagr_val:.1f}%</b>.")
        elif cagr_val > 0.0:
            pros.append(f"<b>Positive Top-Line Growth:</b> 5-year Revenue CAGR stands at <b>{cagr_val:.1f}%</b>.")
        else:
            cons.append(f"<b>Revenue Stagnation / Decline:</b> 5-year Revenue CAGR is negative at <b>{cagr_val:.1f}%</b>.")

    # 2. EBITDA / Operating Profitability
    ebitda_m = summary.get('avg_ebitda_margin')
    if ebitda_m is not None:
        if ebitda_m >= 20.0:
            pros.append(f"<b>Robust Operating Margins:</b> Average EBITDA margin sits at a strong <b>{ebitda_m:.1f}%</b>.")
        elif ebitda_m >= 10.0:
            pros.append(f"<b>Healthy EBITDA Margin:</b> Average EBITDA margin is <b>{ebitda_m:.1f}%</b>.")
        else:
            cons.append(f"<b>Thin Operating Margin:</b> Average EBITDA margin is tight at <b>{ebitda_m:.1f}%</b>.")

    # 3. Return on Equity (ROE)
    roe_val = summary.get('avg_roe')
    if roe_val is not None:
        if roe_val >= 15.0:
            pros.append(f"<b>High Capital Returns:</b> Excellent average Return on Equity (ROE) of <b>{roe_val:.1f}%</b>.")
        elif roe_val >= 8.0:
            pros.append(f"<b>Moderate ROE Profile:</b> Average Return on Equity of <b>{roe_val:.1f}%</b>.")
        else:
            cons.append(f"<b>Subdued Return on Equity:</b> Average ROE is low at <b>{roe_val:.1f}%</b>.")

    # 4. Leverage (Debt to Equity)
    if not ratios_df.empty and 'debt_to_equity' in ratios_df.columns:
        recent_de = ratios_df['debt_to_equity'].dropna()
        if not recent_de.empty:
            de = recent_de.iloc[-1]
            if de < 0.5:
                pros.append(f"<b>Low Debt Risk:</b> Conservative capital structure with D/E ratio at <b>{de:.2f}x</b>.")
            elif de > 1.5:
                cons.append(f"<b>High Financial Leverage:</b> Heavy reliance on debt financing (D/E: <b>{de:.2f}x</b>).")

    # 5. Interest Coverage Ratio
    if not ratios_df.empty and 'interest_coverage' in ratios_df.columns:
        recent_ic = ratios_df['interest_coverage'].dropna()
        if not recent_ic.empty:
            ic = recent_ic.iloc[-1]
            if ic >= 4.0:
                pros.append(f"<b>Solid Debt Serviceability:</b> High Interest Coverage ratio of <b>{ic:.1f}x</b>.")
            elif ic < 2.0:
                cons.append(f"<b>Vulnerable Debt Serviceability:</b> Interest Coverage is low at <b>{ic:.1f}x</b>.")

    # 6. Cash Flow Conversion
    if not cf_df.empty and 'cash_from_operations' in cf_df.columns and not is_df.empty and 'net_income' in is_df.columns:
        cfo_sum = cf_df['cash_from_operations'].fillna(0).sum()
        ni_sum = is_df['net_income'].fillna(0).sum()
        if ni_sum > 0:
            if cfo_sum >= ni_sum:
                pros.append(f"<b>Strong Cash Conversion:</b> Cumulative Operating Cash Flow (₹{cfo_sum:,.1f} Cr) exceeds reported Net Income (₹{ni_sum:,.1f} Cr).")
            elif cfo_sum < ni_sum * 0.7:
                cons.append(f"<b>Earnings Quality Warning:</b> Cumulative Operating Cash Flow (₹{cfo_sum:,.1f} Cr) trails reported Net Income (₹{ni_sum:,.1f} Cr).")

    # Fallbacks if list is brief
    if not pros:
        pros.append("<b>Established Track Record:</b> Multi-year reporting listing on NSE/BSE.")
    if not cons:
        cons.append("<b>Macro Sensitivity:</b> Exposed to sector cycles and input cost inflation.")

    st.markdown("""
    <div style="margin-top:40px; margin-bottom:16px;">
        <h3 style="color:#0f172a; font-size:1.4rem; font-weight:800; letter-spacing:-0.02em; margin-bottom:4px;">
            📋 Executive Financial Summary — Strengths & Weaknesses
        </h3>
        <p style="color:#64748b; font-size:0.9rem; margin:0;">
            Key pros and cons synthesized from 5-year historical statements, ratios, and cash flows.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        pros_items = "".join([f"<li style='margin-bottom:10px; line-height:1.5;'>{p}</li>" for p in pros])
        st.markdown(f"""
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:16px; padding:24px; min-height:220px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
                <span style="font-size:1.3rem;">👍</span>
                <h4 style="color:#166534; margin:0; font-size:1.1rem; font-weight:800;">Key Pros & Strengths</h4>
            </div>
            <ul style="color:#14532d; padding-left:20px; margin:0; font-size:0.92rem;">
                {pros_items}
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        cons_items = "".join([f"<li style='margin-bottom:10px; line-height:1.5;'>{c}</li>" for c in cons])
        st.markdown(f"""
        <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:16px; padding:24px; min-height:220px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
                <span style="font-size:1.3rem;">👎</span>
                <h4 style="color:#991b1b; margin:0; font-size:1.1rem; font-weight:800;">Key Cons & Weaknesses</h4>
            </div>
            <ul style="color:#7f1d1d; padding-left:20px; margin:0; font-size:0.92rem;">
                {cons_items}
            </ul>
        </div>
        """, unsafe_allow_html=True)


def page_historical_data():
    if 'company_info' not in st.session_state or not st.session_state.get('company_info'):
        st.warning('⚠️ Please go to **Company Search** and select a company first.')
        return

    company_info = st.session_state['company_info']
    company_name = company_info['company_name']

    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 2: Historical Financials — {company_name}
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            5-Year Financial Statements, Ratios, Data Validation & Executive Pros/Cons Summary.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-Fetch Financials on Page Load ────────────────────────────────────
    current_symbol = company_info.get('ticker_symbol') or company_info.get('nse_symbol') or company_info.get('company_name')
    stored_symbol = st.session_state.get('loaded_symbol')

    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data') or stored_symbol != current_symbol:
        # Show animated loading screen
        from utils.loading_screen import show_loading_screen
        show_loading_screen(f"Fetching {company_name} Financials", duration_ms=3000)

        with st.spinner(f'Loading 5-year financial statements for {company_name}...'):
            import json
            raw_data   = _cached_fetch(current_symbol, json.dumps(company_info, default=str))
            clean_data = clean_financial_data(raw_data, company_info)
            validation = run_all_validations(clean_data)
            ratios_data = compute_ratios(clean_data)

        st.session_state['raw_data']      = raw_data
        st.session_state['clean_data']    = clean_data
        st.session_state['validation']    = validation
        st.session_state['ratios_data']   = ratios_data
        st.session_state['loaded_symbol'] = current_symbol

        meta = clean_data.get('metadata', {})
        if meta.get('n_years', 0) > 0:
            st.session_state['max_unlocked_stage'] = max(st.session_state.get('max_unlocked_stage', 1), 3)

    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data'):
        st.error('Failed to retrieve financial data. Please return to Stage 1 and select a different company.')
        return

    clean_data  = st.session_state['clean_data']
    ratios_data = st.session_state.get('ratios_data', {})
    validation  = st.session_state.get('validation', [])
    meta        = clean_data.get('metadata', {})
    is_df       = clean_data.get('income_stmt',   pd.DataFrame())
    bs_df       = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df       = clean_data.get('cash_flow',     pd.DataFrame())
    ratios_df   = ratios_data.get('ratios_df',    pd.DataFrame())
    summary     = ratios_data.get('summary',      {})

    # ── Metadata header ─────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Years of Data',  meta.get('n_years', 0))
    c2.metric('FY Range', f"{meta.get('financial_years', ['?'])[0]} – {meta.get('financial_years', ['?'])[-1]}" if meta.get('financial_years') else 'N/A')
    last_pat = is_df['net_income'].iloc[-1] if not is_df.empty and 'net_income' in is_df.columns else None
    c3.metric('💰 Latest PAT (Profit After Tax)', crore(last_pat) if last_pat is not None else 'N/A')
    c4.metric('Data Source',    meta.get('source', 'N/A'))
    c5.metric('Completeness',   f"{meta.get('data_completeness', 0):.0f}%")

    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-top:18px; margin-bottom:8px;">
        <span style="font-size:1.5rem;">👇</span>
        <span style="color:#0f172a; font-weight:800; font-size:1.05rem; letter-spacing:-0.01em;">Click a statement tab below to inspect details:</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tabs = st.tabs(['P&L 📊', 'Balance Sheet 🏦', 'Cash Flows 💰', 'Ratios 📈', 'Validation ✔️', 'Corporate News & Catalysts 📰'])

    # ── P&L Tab ────────────────────────────────────────────────────────────────
    with tabs[0]:
        if not is_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                bar_chart(is_df, 'revenue', 'Revenue Growth (Cr)', '#ff7e5f')
            with c2:
                bar_chart(is_df, 'ebitda', 'EBITDA (Cr)', '#059669')

            c1, c2 = st.columns(2)
            with c1:
                bar_chart(is_df, 'net_income', 'Net Income (Cr)', '#8b5cf6')
            with c2:
                if not ratios_df.empty:
                    line_chart(ratios_df, ['gross_margin', 'ebitda_margin', 'net_margin'],
                               'Margin Trends (%)', '%')

            st.subheader('📊 Income Statement Data (Key Highlights: 🟢 YoY Growth, 🔴 Decline / Loss)')
            st.dataframe(
                style_financial_df(is_df),
                use_container_width=True, height=350
            )
        else:
            st.warning('No income statement data available.')

    # ── Balance Sheet Tab ─────────────────────────────────────────────────────
    with tabs[1]:
        if not bs_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                bar_chart(bs_df, 'total_assets', 'Total Assets (Cr)', '#3b82f6')
            with c2:
                if 'total_debt' in bs_df.columns and 'total_equity' in bs_df.columns:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=bs_df.index, y=bs_df['total_debt'].fillna(0),
                                         name='Total Debt', marker_color='#dc2626'))
                    fig.add_trace(go.Bar(x=bs_df.index, y=bs_df['total_equity'].fillna(0),
                                         name='Total Equity', marker_color='#059669'))
                    fig.update_layout(barmode='group', title='Debt vs Equity (Cr)', **CHART_LAYOUT)
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader('🏦 Balance Sheet Data')
            st.dataframe(
                style_financial_df(bs_df),
                use_container_width=True, height=350
            )
        else:
            st.warning('No balance sheet data available.')

    # ── Cash Flow Tab ─────────────────────────────────────────────────────────
    with tabs[2]:
        if not cf_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                bar_chart(cf_df, 'cash_from_operations', 'Operating Cash Flow (Cr)', '#059669')
            with c2:
                bar_chart(cf_df, 'free_cash_flow', 'Free Cash Flow (Cr)', '#ff7e5f')

            if 'cash_from_operations' in cf_df.columns and \
               'cash_from_investing' in cf_df.columns and \
               'cash_from_financing' in cf_df.columns:
                fig = go.Figure()
                colors_cf = ['#059669', '#dc2626', '#8b5cf6']
                for i, col in enumerate(['cash_from_operations', 'cash_from_investing', 'cash_from_financing']):
                    fig.add_trace(go.Bar(x=cf_df.index, y=cf_df[col].fillna(0),
                                         name=col.replace('_', ' ').title(),
                                         marker_color=colors_cf[i]))
                fig.update_layout(barmode='relative', title='Cash Flow Waterfall (Cr)', **CHART_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader('💰 Cash Flow Statement Data')
            st.dataframe(
                style_financial_df(cf_df),
                use_container_width=True, height=350
            )
        else:
            st.warning('No cash flow data available.')

    # ── Ratios Tab ───────────────────────────────────────────────────────────────
    with tabs[3]:
        if not ratios_df.empty:
            cols = st.columns(4)
            summary_items = [
                ('Revenue CAGR',    summary.get('revenue_cagr'),     '%'),
                ('Avg EBITDA Margin', summary.get('avg_ebitda_margin'), '%'),
                ('Avg Net Margin',  summary.get('avg_net_margin'),   '%'),
                ('Avg ROE',         summary.get('avg_roe'),          '%'),
            ]
            for i, (label, val, unit) in enumerate(summary_items):
                with cols[i % 4]:
                    if val is not None:
                        st.metric(label, f"{val:.1f}{unit}")

            line_chart(ratios_df, ['roe', 'roa'], 'Returns — ROE & ROA (%)', '%')
            line_chart(ratios_df, ['current_ratio', 'quick_ratio'], 'Liquidity Ratios', 'x')
            line_chart(ratios_df, ['debt_to_equity', 'net_debt_ebitda'], 'Leverage Ratios', 'x')

            st.subheader('📈 Full Ratio Table')
            st.dataframe(
                ratios_df.style.format('{:.2f}', na_rep='N/A'),
                use_container_width=True
            )
        else:
            st.warning('No ratio data. Fetch financials first.')

    # ── Validation Tab ──────────────────────────────────────────────────────────
    with tabs[4]:
        if not validation:
            st.info('No validation results yet. Fetch data first.')
        else:
            summary_row = next((item for item in validation if item.get('check') == '__SUMMARY__'), None)
            if summary_row:
                p, w, f = summary_row.get('pass_count', 0), summary_row.get('warn_count', 0), summary_row.get('fail_count', 0)
                c1, c2, c3 = st.columns(3)
                c1.metric('✅ Passed', p)
                c2.metric('⚠️ Warnings', w)
                c3.metric('❌ Failed', f)
                st.markdown('---')

            for val_item in validation:
                if val_item.get('check') == '__SUMMARY__':
                    continue
                fy_str = val_item.get('fy', 'ALL')
                fy_lbl = f" [{fy_str}]" if fy_str and fy_str != 'ALL' else ''
                st.markdown(
                    f"{status_badge(val_item.get('status', 'INFO'))} &nbsp; **{val_item.get('check', '')}**{fy_lbl} &mdash; "
                    f"<span style='color:#64748b;'>{val_item.get('message', '')}</span>",
                    unsafe_allow_html=True
                )

    # ── Corporate News & Catalysts Tab ──────────────────────────────────────
    with tabs[5]:
        from core.news_fetcher import render_news_section
        render_news_section(company_info)

    # ── Executive Summary: Pros & Cons Section ──────────────────────────────
    st.markdown('---')
    render_pros_and_cons(clean_data, ratios_data)

    st.markdown('<br>', unsafe_allow_html=True)
    proceed_to_stage(3, "PROCEED TO STAGE 3: INTEGRATED FORECAST MODEL →")


if __name__ == '__main__':
    page_historical_data()
