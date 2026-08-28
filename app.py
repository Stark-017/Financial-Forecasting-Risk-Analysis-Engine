# app.py
"""
Corporate Financial Forecasting System
Schematiq-Inspired Design: Bold Typography, Warm Sunset Gradients, Obsidian High Contrast & Clean Canvas.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from utils.stepper import render_stage_stepper, scroll_to_top, STAGES

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinCast — Corporate Financial Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)

# ─── Global CSS (Schematiq Aesthetic System) ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,800&family=Outfit:wght@400;500;600;700;800&display=swap');

/* Base canvas */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #f8fafc;
    color: #0f172a;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}

/* Main Container */
.main .block-container {
    padding: 2rem 3rem !important;
    max-width: 1350px !important;
}

/* Headings */
h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    color: #0f172a !important;
}

/* Schematiq Hero Typography */
.hero-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.04em;
    color: #0f172a;
    margin-bottom: 1rem;
}

.hero-subtitle {
    font-size: 1.2rem;
    color: #64748b;
    font-weight: 400;
    max-width: 650px;
    line-height: 1.6;
    margin-bottom: 2rem;
}

/* Schematiq High-Contrast Obsidian Buttons (LIKE THE LEARN MORE BUTTON IN IMAGE) */
.stButton > button {
    border-radius: 8px !important;
    border: none !important;
    background-color: #0f172a !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    padding: 0.75rem 1.75rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 14px rgba(15,23,42,0.12) !important;
}

.stButton > button:hover {
    background-color: #1e293b !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.2) !important;
    color: #ffffff !important;
}

/* Secondary Buttons */
.stButton > button[type="secondary"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: none !important;
}

.stButton > button[type="secondary"]:hover {
    background-color: #f1f5f9 !important;
    border-color: #0f172a !important;
}

/* Cards & Elevated Containers */
div[data-testid="stMetric"], .schematiq-card {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 20px 24px !important;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05) !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stMetric"]:hover, .schematiq-card:hover {
    border-color: #cbd5e1 !important;
    box-shadow: 0 20px 40px -15px rgba(15,23,42,0.08) !important;
}

[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* Text Input */
input[type="text"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    font-size: 1rem !important;
    padding: 12px 18px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
}

input[type="text"]:focus {
    border-color: #0f172a !important;
    box-shadow: 0 0 0 3px rgba(15,23,42,0.1) !important;
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 8px;
    color: #64748b;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 8px 16px;
}

[data-testid="stTabs"] [aria-selected="true"] {
    background: #0f172a !important;
    color: #ffffff !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
}

/* Custom Ribbon Divider */
.gradient-ribbon {
    height: 4px;
    width: 100%;
    background: linear-gradient(90deg, #ff7e5f 0%, #feb47b 50%, #ff6b8b 100%);
    border-radius: 2px;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'current_stage' not in st.session_state:
    st.session_state['current_stage'] = 1
if 'max_unlocked_stage' not in st.session_state:
    st.session_state['max_unlocked_stage'] = 1

# Check if we need to scroll to top after this render completes
_do_scroll_top = st.session_state.pop('_scroll_top', False)

# ─── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 12px 0; text-align: left;">
        <div style="display:flex; align-items:center; gap:10px;">
            <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#ff7e5f,#feb47b); display:flex; align-items:center; justify-content:center; color:white; font-weight:900; font-size:1.1rem;">⚡</div>
            <div>
                <h2 style="color:#0f172a; font-size:1.25rem; font-weight:800; margin:0; letter-spacing:-0.03em;">fincast</h2>
                <p style="color:#64748b; font-size:0.75rem; margin:0; font-weight:500;">Financial Intelligence</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='gradient-ribbon'></div>", unsafe_allow_html=True)

    # Selected Company Context Card
    if 'company_info' in st.session_state and st.session_state.get('company_info'):
        co = st.session_state['company_info']
        st.markdown(f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:14px; margin-bottom:16px;">
            <p style="color:#64748b; font-size:0.7rem; margin:0 0 4px 0; font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">SELECTED COMPANY</p>
            <p style="color:#0f172a; font-size:1rem; font-weight:800; margin:0;">{co.get('company_name','')}</p>
            <p style="color:#64748b; font-size:0.8rem; margin:2px 0 0 0; font-weight:500;">{co.get('nse_symbol','')} &bull; {co.get('exchange','')}</p>
        </div>
        """, unsafe_allow_html=True)

    mode = st.radio(
        "NAVIGATION",
        options=["⚡ Guided Stages Pipeline", "🏠 Overview & Vision", "ℹ️ About Platform"],
        index=0,
        key="view_mode"
    )

    st.markdown("---")
    st.markdown("""
    <div style="padding: 8px 0; text-align:left;">
        <p style="color:#94a3b8; font-size:0.72rem; margin:0; font-weight:600;">DATA SOURCES</p>
        <p style="color:#64748b; font-size:0.8rem; margin:2px 0; font-weight:600;">NSE / BSE Listed Equities</p>
        <p style="color:#94a3b8; font-size:0.72rem; margin:0;">Yahoo Finance + Screener.in</p>
    </div>
    """, unsafe_allow_html=True)

# ─── Page Router ───────────────────────────────────────────────────────────────
if mode == "🏠 Overview & Vision":
    # Schematiq-inspired Hero Section
    st.markdown("""
    <div style="text-align:center; padding: 60px 0 40px 0; position:relative;">
        <div style="display:inline-block; padding: 6px 16px; background:#f1f5f9; border:1px solid #e2e8f0; border-radius:100px; color:#0f172a; font-size:0.8rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:16px;">
            Corporate Financial Intelligence Platform
        </div>
        <h1 class="hero-title">
            Simplifying corporate<br>
            <span style="background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 50%, #ff6b8b 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                financial forecasting.
            </span>
        </h1>
        <p class="hero-subtitle" style="margin: 0 auto;">
            Transform raw NSE/BSE financial statements into driver-based 3-statement forecasts, machine learning predictions, and stress tests in seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Feature Cards Grid
    c1, c2, c3 = st.columns(3)
    cards = [
        ("01", "Company Search & Verify", "Fuzzy matching and instant verification across NSE/BSE listed securities."),
        ("02", "3-Statement Forecast", "Integrated Income Statement, Balance Sheet, and Cash Flow financial engine."),
        ("03", "ML & Sensitivity", "Statistical machine learning projections and multi-variate stress testing."),
    ]
    for col, (num, title, desc) in zip([c1, c2, c3], cards):
        with col:
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:28px; height:190px; box-shadow:0 10px 30px -10px rgba(0,0,0,0.05);">
                <span style="font-size:0.8rem; font-weight:800; color:#ff7e5f; letter-spacing:0.08em;">{num}</span>
                <h3 style="color:#0f172a; margin:10px 0 8px 0; font-size:1.15rem; font-weight:800;">{title}</h3>
                <p style="color:#64748b; margin:0; font-size:0.88rem; line-height:1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("LAUNCH PIPELINE →", type="primary", use_container_width=True):
        st.session_state['view_mode'] = "⚡ Guided Stages Pipeline"
        st.rerun()

elif mode == "ℹ️ About Platform":
    from pages.about import page_about
    page_about()

else:
    # ⚡ Guided Stages Pipeline Mode
    render_stage_stepper()
    curr_stage = st.session_state['current_stage']

    # ── Floating Stock Price Ticker (top-right) ────────────────────────────
    co = st.session_state.get('company_info', {})
    if co:
        _price = co.get('current_price', 'N/A')
        _sym = co.get('nse_symbol') or co.get('bse_code') or ''
        _name = co.get('company_name', '')
        _mcap = co.get('market_cap_cr')
        _mcap_str = f"₹{_mcap:,.0f} Cr" if _mcap else 'N/A'
        import streamlit.components.v1 as _comp
        _comp.html(f"""
<script>
(function() {{
  var pd = window.parent.document;
  // Remove any previous ticker to avoid duplicates on rerun
  var old = pd.getElementById('stock-ticker-float');
  if (old) old.remove();

  var el = pd.createElement('div');
  el.id = 'stock-ticker-float';
  el.innerHTML = `
    <div id="ticker-handle-inner" style="
        display:flex; justify-content:space-between; align-items:center;
        margin-bottom:8px; cursor:grab; padding:2px 0;">
      <span style="font-size:0.62rem; font-weight:900; color:#94a3b8;
                    text-transform:uppercase; letter-spacing:0.1em;">{_sym} &bull; LIVE</span>
      <span style="color:#cbd5e1; font-size:1.2rem; line-height:1; padding-left:10px;
                    cursor:grab;">&#x2630;</span>
    </div>
    <div style="font-size:1.55rem; font-weight:900; color:#ffffff;
                letter-spacing:-0.03em; line-height:1;">&#8377;{_price}</div>
    <div style="font-size:0.72rem; color:#cbd5e1; margin-top:5px;">Mkt Cap: {_mcap_str}</div>
    <div style="font-size:0.62rem; color:#94a3b8; margin-top:3px;
                max-width:170px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{_name}</div>
  `;
  el.style.cssText = `
    position: fixed; top: 72px; right: 28px; z-index: 999999;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px; padding: 14px 18px 12px 18px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.55);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    min-width: 195px; user-select: none;
  `;
  pd.body.appendChild(el);

  // Drag logic on parent document
  var handle = pd.getElementById('ticker-handle-inner');
  var isDragging = false, sX, sY, sL, sT;
  handle.addEventListener('mousedown', function(e) {{
    isDragging = true;
    sX = e.clientX; sY = e.clientY;
    var r = el.getBoundingClientRect();
    sL = r.left; sT = r.top;
    el.style.cursor = 'grabbing';
    handle.style.cursor = 'grabbing';
    e.preventDefault();
    e.stopPropagation();
  }});
  pd.addEventListener('mousemove', function(e) {{
    if (!isDragging) return;
    el.style.left  = (sL + e.clientX - sX) + 'px';
    el.style.top   = (sT + e.clientY - sY) + 'px';
    el.style.right = 'auto';
  }});
  pd.addEventListener('mouseup', function() {{
    if (isDragging) {{
      isDragging = false;
      el.style.cursor = 'default';
      handle.style.cursor = 'grab';
    }}
  }});
}})();
</script>""", height=0, scrolling=False)

    if curr_stage == 1:
        from pages.company_search import page_company_search
        page_company_search()

    elif curr_stage == 2:
        from pages.historical_data import page_historical_data
        page_historical_data()

    elif curr_stage == 3:
        from pages.forecast import page_forecast
        page_forecast()

    elif curr_stage == 4:
        from pages.ml_forecast import page_ml_forecast
        page_ml_forecast()

    elif curr_stage == 5:
        from pages.sensitivity import page_sensitivity
        page_sensitivity()

    elif curr_stage == 6:
        from pages.risk_analysis import page_risk_analysis
        page_risk_analysis()

# ── Scroll to top AFTER all page content has rendered ────────────────────────
if _do_scroll_top:
    import streamlit.components.v1 as _scroll_comp
    _scroll_comp.html("""
    <script>
    (function() {
        function doScroll() {
            try {
                var pd = window.parent.document;
                // Streamlit Cloud often uses .stMainBlockContainer or data-testid="stMain"
                var targets = [
                    pd.querySelector('.stMainBlockContainer'),
                    pd.querySelector('[data-testid="stMain"]'),
                    pd.querySelector('[data-testid="stAppViewContainer"]'),
                    pd.querySelector('section.main'),
                    pd.querySelector('.main'),
                    pd.documentElement
                ];
                for (var i = 0; i < targets.length; i++) {
                    if (targets[i]) {
                        targets[i].scrollTop = 0;
                        if (typeof targets[i].scrollTo === 'function') {
                            targets[i].scrollTo({top: 0, behavior: 'instant'});
                        }
                    }
                }
                if (typeof window.parent.scrollTo === 'function') {
                    window.parent.scrollTo(0, 0);
                }
            } catch(e) {
                // Fallback if cross-origin iframe blocks window.parent
                window.scrollTo(0, 0);
            }
        }
        // Fire multiple times with staggered delays to beat Streamlit's render cycle
        doScroll();
        setTimeout(doScroll, 100);
        setTimeout(doScroll, 300);
        setTimeout(doScroll, 600);
    })();
    </script>
    """, height=0)
