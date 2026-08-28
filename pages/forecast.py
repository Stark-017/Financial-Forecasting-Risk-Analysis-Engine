# pages/forecast.py
"""
Phase 4 & 5 UI — Integrated Three-Statement Forecast Engine & Economic Scenario Modeling.
Schematiq Design: Clean typography, 2-Year Average Slider Defaults, Detailed Tooltips with Investopedia Links, & Factual Math Reasoning.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from core.driver_analyzer import analyze_drivers
from core.forecast_engine import build_forecast
from core.scenario_engine import run_scenarios
from utils.formatting import crore, pct
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

SCEN_COLORS = {'good': COLOUR['good'], 'base': COLOUR['base'], 'bad': COLOUR['bad']}


def driver_table(driver_df: pd.DataFrame):
    def color_trend(val):
        colors_map = {'increasing': 'color:#059669; font-weight:700', 'declining': 'color:#dc2626; font-weight:700',
                      'volatile': 'color:#8b5cf6; font-weight:700', 'stable': 'color:#d97706; font-weight:700'}
        return colors_map.get(str(val).lower(), '')

    styler = driver_df.style.format({
        '5-Yr Avg': '{:.2f}',
        '2-Yr Avg': '{:.2f}',
        'Recent': '{:.2f}',
        'Std Dev': '{:.2f}',
        'Base Forecast (2-Yr Avg)': '{:.2f}'
    }, na_rep='N/A')
    if hasattr(styler, 'map'):
        styler = styler.map(color_trend, subset=['Trend'])
    else:
        styler = styler.applymap(color_trend, subset=['Trend'])

    st.dataframe(styler, use_container_width=True)


def scenario_chart(scenarios: dict, metric_stmt: str, metric_col: str, title: str,
                   hist_df=None, hist_col=None):
    fig = go.Figure()

    # Historical
    if hist_df is not None and not hist_df.empty and hist_col and hist_col in hist_df.columns:
        fig.add_trace(go.Bar(
            x=hist_df.index, y=hist_df[hist_col].fillna(0),
            name='Historical', marker_color='#334155',
        ))

    # Scenarios
    for scen in ['good', 'base', 'bad']:
        fo = scenarios.get(scen, {})
        df = fo.get(metric_stmt, pd.DataFrame())
        if not df.empty and metric_col in df.columns:
            fig.add_trace(go.Bar(
                x=df.index, y=df[metric_col].fillna(0),
                name=scen.capitalize(), marker_color=SCEN_COLORS[scen],
            ))

    fig.update_layout(
        title=dict(text=title, font=dict(color='#0f172a', size=14, family='Plus Jakarta Sans')),
        barmode='group',
        **CHART_LAYOUT
    )
    st.plotly_chart(fig, use_container_width=True)


def resilience_gauge(score: float, classification: str, scenario_name: str):
    color = COLOUR['good'] if score >= 65 else (COLOUR['base'] if score >= 45 else COLOUR['bad'])
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=score,
        title={'text': f"{scenario_name.capitalize()} Resilience", 'font': {'color': '#0f172a', 'size': 14, 'family': 'Plus Jakarta Sans'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#64748b'},
            'bar': {'color': color},
            'steps': [
                {'range': [0,  30], 'color': 'rgba(16,185,129,0.15)'},
                {'range': [30, 60], 'color': 'rgba(245,158,11,0.15)'},
                {'range': [60,100], 'color': 'rgba(239,68,68,0.15)'},
            ],
            'threshold': {'value': score, 'line': {'color': color, 'width': 2}},
            'bgcolor': 'rgba(0,0,0,0)',
        },
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#0f172a', height=250,
                      margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<p style='text-align:center;color:{color};font-weight:700;'>{classification}</p>",
                unsafe_allow_html=True)


def render_forecast_reasoning_card(clean_data: dict, drivers: dict, base_results: dict):
    """Render factual mathematical reasoning and justification for the forecast model."""
    is_df = clean_data.get('income_stmt', pd.DataFrame())
    if is_df.empty:
        return

    last_fy = is_df.index[-1]
    last_rev = is_df['revenue'].iloc[-1] if 'revenue' in is_df.columns else 0.0

    rev_g = drivers.get('revenue_growth', {}).get('base_forecast', 0.0) or 0.0
    ebitda_m = drivers.get('ebitda_margin', {}).get('base_forecast', 0.0) or 0.0

    base_is = base_results.get('income_stmt', pd.DataFrame())
    if base_is.empty:
        return

    next_fy = base_is.index[0]
    next_rev = base_is['revenue'].iloc[0] if 'revenue' in base_is.columns else 0.0

    st.markdown("---")
    st.subheader("🧠 Factual Model Reasoning & Math Explanation")
    st.write(f"**Why is {next_fy} Base Revenue projected at ₹{next_rev:,.1f} Cr?** Here is the step-by-step math backing this prediction:")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(f"1. BASELINE ANCHOR ({last_fy})", f"₹{last_rev:,.1f} Cr", help="Audited actual revenue")
    with c2:
        st.metric("2. 2-YEAR HISTORICAL AVG", f"+{rev_g:.2f}%", help="2-Year historical average growth rate")
    with c3:
        st.metric(f"3. {next_fy} PROJECTION", f"₹{next_rev:,.1f} Cr", delta=f"+{rev_g:.1f}% vs {last_fy}", help="Math projection result")

    st.info(f"💡 **Quantitative Rationale:** The model anchors directly to audited **{last_fy}** actual revenue (₹{last_rev:,.1f} Cr) and applies the verified **2-Year Historical Average Revenue Growth (+{rev_g:.1f}%)** and **2-Year Average EBITDA Margin ({ebitda_m:.1f}%)**. This produces a factual baseline projection without arbitrary extrapolation.")


def page_forecast():
    if 'clean_data' not in st.session_state or not st.session_state.get('clean_data'):
        st.warning('⚠️ Please fetch historical data first in the **Historical Data** tab.')
        return

    clean_data  = st.session_state['clean_data']
    ratios_data = st.session_state.get('ratios_data', {})
    company_info = st.session_state.get('company_info', {})
    company_name = company_info.get('company_name', 'Company')
    is_df = clean_data.get('income_stmt', pd.DataFrame())
    bs_df = clean_data.get('balance_sheet', pd.DataFrame())

    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 3: Integrated 3-Statement Forecast — {company_name}
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            Driver-based 3-statement financial engine generating Income Statements, Balance Sheets, Cash Flows, and Resilience Scores across Good, Base, and Bad scenarios.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Section 1: Driver Analysis ────────────────────────────────────────────
    st.markdown('## 📡 Phase 3: Driver Analysis')

    if 'drivers_data' not in st.session_state or not st.session_state.get('drivers_data'):
        with st.spinner('Analysing historical drivers...'):
            drivers_data = analyze_drivers(clean_data, ratios_data)
        st.session_state['drivers_data'] = drivers_data
    else:
        drivers_data = st.session_state['drivers_data']

    drivers = drivers_data.get('drivers', {})
    driver_df = drivers_data.get('driver_df', pd.DataFrame())

    if not driver_df.empty:
        driver_table(driver_df)
    else:
        st.info('No driver data available.')

    # ── Section 2: Scenario Controls ──────────────────────────────────────────
    st.markdown('---')
    st.markdown('## 🎯 Phase 4 & 5: Scenario Forecast')

    n_years = st.selectbox(
        'Forecast Horizon (Years)', [1, 3, 5], index=0,
        help="Predict financial statements for 1 upcoming financial year (FY+1 default)."
    )

    custom_base = {}
    with st.expander('⚙️ Customise Base Scenario Assumptions (Optional — Pre-filled with 2-Year Historical Averages)'):
        st.markdown("<p style='color:#64748b; font-size:0.88rem; margin-bottom:14px;'>Sliders default to the <b>2-Year Historical Average</b>. Hover over the <b>❓ icons</b> for definitions, formulas, examples, and Investopedia links!</p>", unsafe_allow_html=True)

        base_rev_g = float(drivers.get('revenue_growth', {}).get('base_forecast', 8.0) or 8.0)
        base_ebitda = float(drivers.get('ebitda_margin', {}).get('base_forecast', 20.0) or 20.0)
        base_tax = float(drivers.get('effective_tax_rate', {}).get('base_forecast', 25.0) or 25.0)
        base_capex = float(drivers.get('capex_to_revenue', {}).get('base_forecast', 5.0) or 5.0)
        base_div = float(drivers.get('dividend_payout', {}).get('base_forecast', 30.0) or 30.0)

        # Dynamic bounds matching company scale
        rev_min = float(min(-20.0, round(base_rev_g - 25.0, 1)))
        rev_max = float(max(100.0, round(base_rev_g + 30.0, 1)))

        ebitda_min = float(max(0.5, round(min(5.0, base_ebitda - 10.0), 1)))
        ebitda_max = float(max(60.0, round(base_ebitda + 25.0, 1)))

        rev_g = st.slider(
            'Revenue Growth (%)', rev_min, rev_max, base_rev_g, 0.5,
            help="""📈 REVENUE GROWTH (%)

Definition: Percentage change in total company sales year-over-year.

Formula: ((Revenue_FY_t - Revenue_FY_t-1) / Revenue_FY_t-1) * 100

Example: If FY25 Revenue was ₹100 Cr and FY26 Revenue was ₹120 Cr, Growth = +20.0%.

🔗 Learn More: https://www.investopedia.com/terms/r/revenuegrowth.asp"""
        )
        ebitda_m = st.slider(
            'EBITDA Margin (%)', ebitda_min, ebitda_max, base_ebitda, 0.5,
            help="""📊 EBITDA MARGIN (%)

Definition: Core operational cash profit generated per ₹100 of sales before interest, tax, and depreciation.

Formula: (EBITDA / Total Revenue) * 100

Example: If Revenue is ₹200 Cr and EBITDA is ₹40 Cr, Margin = 20.0%.

🔗 Learn More: https://www.investopedia.com/terms/e/ebitdamargin.asp"""
        )
        tax_r = st.slider(
            'Effective Tax Rate (%)', 5.0, 45.0, base_tax, 0.5,
            help="""🏛️ EFFECTIVE TAX RATE (%)

Definition: Share of pre-tax earnings paid as corporate income tax.

Formula: (Income Tax Expense / Profit Before Tax) * 100

Example: If Profit Before Tax is ₹50 Cr and Tax is ₹12.5 Cr, Tax Rate = 25.0%.

🔗 Learn More: https://www.investopedia.com/terms/e/effectivetaxrate.asp"""
        )
        capex_r = st.slider(
            'Capex / Revenue (%)', 0.5, 30.0, base_capex, 0.5,
            help="""🏭 CAPEX TO REVENUE (%)

Definition: Re-investment rate in property, plant, machinery, and technology relative to total sales.

Formula: (Capital Expenditures / Total Revenue) * 100

Example: Re-investing ₹10 Cr in factory equipment on ₹200 Cr Revenue = 5.0%.

🔗 Learn More: https://www.investopedia.com/terms/c/capitalexpenditure.asp"""
        )
        div_p = st.slider(
            'Dividend Payout (%)', 0.0, 100.0, base_div, 1.0,
            help="""💸 DIVIDEND PAYOUT (%)

Definition: Share of annual net profits paid back directly to shareholders as cash dividends.

Formula: (Total Cash Dividends Paid / Net Profit) * 100

Example: Paying ₹15 Cr in cash dividends out of ₹50 Cr Net Income = 30.0% Payout.

🔗 Learn More: https://www.investopedia.com/terms/d/dividendpayoutratio.asp"""
        )

        custom_base = {
            'revenue_growth':    rev_g,
            'ebitda_margin':     ebitda_m,
            'effective_tax_rate': tax_r,
            'capex_to_revenue':  capex_r,
            'dividend_payout':   div_p,
        }

        # Educational Library inside expander
        with st.expander('📚 Comprehensive Financial Terms, Formulas & Articles Library'):
            st.markdown("""
            * **📈 Revenue Growth (%)**: [Investopedia Article](https://www.investopedia.com/terms/r/revenuegrowth.asp)  
              *Formula:* `((Revenue_t - Revenue_t-1) / Revenue_t-1) * 100`
            * **📊 EBITDA Margin (%)**: [Investopedia Article](https://www.investopedia.com/terms/e/ebitdamargin.asp)  
              *Formula:* `(EBITDA / Total Revenue) * 100`
            * **🏛️ Effective Tax Rate (%)**: [Investopedia Article](https://www.investopedia.com/terms/e/effectivetaxrate.asp)  
              *Formula:* `(Income Tax Expense / Profit Before Tax) * 100`
            * **🏭 Capex / Revenue (%)**: [Investopedia Article](https://www.investopedia.com/terms/c/capitalexpenditure.asp)  
              *Formula:* `(Capital Expenditures / Total Revenue) * 100`
            * **💸 Dividend Payout (%)**: [Investopedia Article](https://www.investopedia.com/terms/d/dividendpayoutratio.asp)  
              *Formula:* `(Total Cash Dividends Paid / Net Profit) * 100`
            """)

    run_btn = st.button('🚀 Run All Scenarios', type='primary', use_container_width=True)
    if run_btn or ('scenario_results' in st.session_state and st.session_state.get('scenario_results')):
        if run_btn:
            with st.spinner('Running Good / Base / Bad scenarios...'):
                results = run_scenarios(
                    clean_data=clean_data,
                    drivers=drivers,
                    custom_assumptions={'base': custom_base} if custom_base else None,
                    n_years=n_years,
                )
            st.session_state['scenario_results'] = results
            st.session_state['max_unlocked_stage'] = max(st.session_state.get('max_unlocked_stage', 1), 4)
            st.rerun()
        else:
            results = st.session_state['scenario_results']

        base_fo = results.get('base', {})
        good_fo = results.get('good', {})
        bad_fo  = results.get('bad',  {})

        validation = base_fo.get('validation', {})
        warnings   = validation.get('warnings', [])
        if warnings:
            for w in warnings:
                st.warning(f'⚠️ {w}')
        else:
            st.success('✅ Three-statement integration validated. Balance sheet balanced.')

        # ── Forecast Charts ───────────────────────────────────────────────────
        st.markdown('### 📊 Forecast Comparison')
        tab1, tab2, tab3, tab4 = st.tabs(['Revenue & Income', 'Margins', 'Balance Sheet', 'Cash Flow'])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                scenario_chart(results, 'income_stmt', 'revenue', 'Revenue — 3 Scenarios (Cr)', is_df, 'revenue')
            with c2:
                scenario_chart(results, 'income_stmt', 'net_income', 'Net Income — 3 Scenarios (Cr)', is_df, 'net_income')

        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                scenario_chart(results, 'ratios', 'ebitda_margin', 'EBITDA Margin % — 3 Scenarios')
            with c2:
                scenario_chart(results, 'ratios', 'net_margin', 'Net Margin % — 3 Scenarios')

        with tab3:
            c1, c2 = st.columns(2)
            with c1:
                scenario_chart(results, 'balance_sheet', 'total_assets', 'Total Assets (Cr)', bs_df, 'total_assets')
            with c2:
                scenario_chart(results, 'ratios', 'debt_to_equity', 'Debt/Equity Ratio')

        with tab4:
            c1, c2 = st.columns(2)
            with c1:
                scenario_chart(results, 'cash_flow', 'cash_from_operations', 'Operating Cash Flow (Cr)')
            with c2:
                scenario_chart(results, 'ratios', 'fcf', 'Free Cash Flow (Cr)')

        # ── Factual Math & Model Reasoning Card ──────────────────────────────
        render_forecast_reasoning_card(clean_data, drivers, base_fo)

        # ── Resilience Scores ─────────────────────────────────────────────────
        st.markdown('---')
        st.markdown('### 🛡️ Resilience Analysis')
        resilience = results.get('resilience', {})
        c1, c2, c3 = st.columns(3)
        for col, scen in [(c1, 'good'), (c2, 'base'), (c3, 'bad')]:
            with col:
                r = resilience.get(scen, {})
                resilience_gauge(r.get('score', 50), r.get('classification', 'Unknown'), scen)

        # ── Forecast tables ─────────────────────────────────────────────────
        st.markdown('---')
        st.markdown('### 📜 Forecast Tables')
        scen_tab1, scen_tab2, scen_tab3 = st.tabs(['⬆️ Good', '➖ Base', '⬇️ Bad'])
        for tab, scen in [(scen_tab1, 'good'), (scen_tab2, 'base'), (scen_tab3, 'bad')]:
            with tab:
                fo = results.get(scen, {})
                if fo:
                    stab1, stab2, stab3, stab4 = st.tabs(['P&L', 'Balance Sheet', 'Cash Flow', 'Ratios'])
                    with stab1:
                        df = fo.get('income_stmt', pd.DataFrame())
                        if not df.empty:
                            st.dataframe(df.style.format('{:,.1f}', na_rep='N/A'), use_container_width=True)
                    with stab2:
                        df = fo.get('balance_sheet', pd.DataFrame())
                        if not df.empty:
                            st.dataframe(df.style.format('{:,.1f}', na_rep='N/A'), use_container_width=True)
                    with stab3:
                        df = fo.get('cash_flow', pd.DataFrame())
                        if not df.empty:
                            st.dataframe(df.style.format('{:,.1f}', na_rep='N/A'), use_container_width=True)
                    with stab4:
                        df = fo.get('ratios', pd.DataFrame())
                        if not df.empty:
                            st.dataframe(df.style.format('{:.2f}', na_rep='N/A'), use_container_width=True)

        st.markdown('---')
        from utils.stepper import proceed_to_stage
        proceed_to_stage(4, "Proceed to Stage 4: ML & Hybrid Forecast ➔")


if __name__ == '__main__':
    page_forecast()
