# pages/company_search.py
"""
Phase 1 UI — Company Search and Selection
Schematiq Design: Clean, Direct, Single-Click Company Lookup & Reliable Session State Navigation.
"""

import streamlit as st
from core.company_lookup import search_company, get_company_info, BUILTIN_EQUITIES
from utils.formatting import crore, pct, ratio
from utils.constants import COLOUR


def render_company_card(info: dict):
    """Render native Streamlit company summary card with bold P/E & PAT metrics."""
    mcap = crore(info.get('market_cap_cr'))
    price = info.get('current_price', 'N/A')
    if isinstance(price, (int, float)):
        price_str = f"{float(price):.2f}"
    else:
        price_str = price
    pe = info.get('pe_ratio')
    pb = info.get('pb_ratio')
    dy = info.get('dividend_yield')
    pat = info.get('net_income') or info.get('net_profit')

    company_name = info.get('company_name', 'Company')
    exchange = info.get('exchange', 'NSE')
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    symbol = info.get('nse_symbol') or info.get('bse_code') or '—'
    isin = info.get('isin', 'N/A')

    st.markdown("---")
    st.subheader(f"🏢 {company_name}")
    st.caption(f"**Exchange:** {exchange} | **Symbol:** {symbol} | **ISIN:** {isin}")
    st.write(f"**Sector:** {sector} &nbsp;|&nbsp; **Industry:** {industry}")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric('CURRENT STOCK ...', f'₹{price_str}', help="Market price per share")
    with c2:
        pe_val = f"{pe:.2f}x" if pe else 'N/A'
        st.metric('🔥 P/E RATIO', pe_val, help="Price-to-Earnings Valuation Multiple")
    with c3:
        pat_val = crore(pat) if pat is not None else 'N/A'
        st.metric('💰 PAT (Net Profit)', pat_val, help="Profit After Tax (Annual Net Income)")
    with c4:
        pb_val = f"{pb:.2f}x" if pb else 'N/A'
        st.metric('📊 P/B Ratio', pb_val, help="Price-to-Book Value Multiple")
    with c5:
        dy_val = pct(dy * 100) if dy else 'N/A'
        st.metric('💸 Div. Yield', dy_val, help="Annual Dividend Yield %")

    if info.get('description'):
        with st.expander('🏭 Business Overview & Description'):
            st.write(info['description'])

    if info.get('website'):
        st.markdown(f"[🌐 {info.get('website')}]({info.get('website')})")

    # Render live corporate news & contract wins section
    from core.news_fetcher import render_news_section
    render_news_section(info)


def page_company_search():
    st.markdown("""
    <div style="margin-bottom:20px;">
        <h1 style='color:#0f172a; font-size:2.2rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px;'>
            Stage 1: Select Corporate Entity
        </h1>
        <p style='color:#64748b; font-size:1rem; margin:0;'>
            Search for any Indian listed company on NSE or BSE by typing its name or ticker below.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Search Bar + Action Button ────────────────────────────────────────────
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            'Search Company',
            placeholder='Type company name or ticker (e.g. Pidilite, Tata Motors, Cupid, Shriram, Reliance, TCS)',
            label_visibility='collapsed',
            key='company_search_input',
        )
    with col2:
        search_btn = st.button('🔍 Search', type='primary', use_container_width=True)

    # ── Quick Dropdown Fallback ────────────────────────────────────────────────
    dropdown_options = ['-- Or Select From Popular Listed Companies --'] + [f"{sym} — {name}" for sym, name, exch, isin in BUILTIN_EQUITIES]
    quick_choice = st.selectbox(
        'Quick Dropdown Select',
        dropdown_options,
        index=0,
        label_visibility='collapsed',
        key='quick_company_selectbox'
    )

    selected_symbol = None
    selected_exchange = 'NSE'

    if quick_choice and '--' not in quick_choice:
        selected_symbol = quick_choice.split(' — ')[0].strip()

    # Trigger search when query entered or search button clicked
    if not selected_symbol and (query and len(query.strip()) >= 2):
        matches = search_company(query)
        if not matches:
            st.warning(f'No companies matching "{query}" were found. Try another symbol or company name.')
        else:
            st.markdown(f"<p style='color:#64748b; font-size:0.85rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin:16px 0 8px 0;'>Found {len(matches)} Match(es):</p>",
                        unsafe_allow_html=True)

            for match in matches:
                score_color = '#059669' if match['score'] >= 80 else ('#d97706' if match['score'] >= 60 else '#64748b')
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"""
                    <div style="background:#ffffff; border:1px solid #e2e8f0;
                                border-radius:12px; padding:12px 18px; margin:3px 0; box-shadow:0 2px 8px rgba(0,0,0,0.02);">
                        <span style="color:#0f172a; font-weight:800; font-size:1.02rem;">
                            {match.get('company_name', '')}
                        </span>
                        <span style="color:#64748b; font-size:0.85rem; font-weight:600; margin-left:12px;">
                            {match.get('symbol', '')} &bull; {match.get('exchange', '')}
                        </span>
                        <span style="float:right; color:{score_color}; font-weight:700; font-size:0.82rem;">
                            {match['score']}% match
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    if st.button('SELECT', key=f"select_{match['symbol']}", use_container_width=True):
                        selected_symbol   = match['symbol']
                        selected_exchange = match['exchange']

    # ── If a new selection was made, store in session state and rerun ─────────
    if selected_symbol and selected_symbol != st.session_state.get('selected_symbol'):
        from utils.loading_screen import show_loading_screen
        show_loading_screen("Verifying Company Data", duration_ms=2200)
        with st.spinner(f'Loading financial details for {selected_symbol}...'):
            company_info = get_company_info(selected_symbol, selected_exchange)

        if company_info is None:
            st.error(f'Could not verify {selected_symbol} on Yahoo Finance. Try a different ticker.')
            return

        st.session_state['company_info']        = company_info
        st.session_state['selected_symbol']     = selected_symbol
        st.session_state['max_unlocked_stage']  = max(st.session_state.get('max_unlocked_stage', 1), 2)
        st.session_state['clean_data']          = None
        st.session_state['ratios_data']         = None
        st.session_state['drivers_data']        = None
        st.session_state['scenario_results']    = None
        st.rerun()

    # ── Display selected company & proceed button (PERSISTENT ON ALL RERUNS) ────
    if 'company_info' in st.session_state and st.session_state.get('company_info'):
        company_info = st.session_state['company_info']
        render_company_card(company_info)
        st.success(f'✅ {company_info["company_name"]} selected successfully!')
        from utils.stepper import proceed_to_stage
        proceed_to_stage(2, f"PROCEED TO STAGE 2: FETCH FINANCIALS FOR {company_info['company_name'].upper()} →")


if __name__ == '__main__':
    page_company_search()
