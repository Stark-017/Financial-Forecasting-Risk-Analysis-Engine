# utils/stepper.py
"""
Top-level Stage Progress Stepper Component.
Inspired by Schematiq design language: ultra-clean, bold typography, warm gradients, and high contrast.
"""

import streamlit as st
import streamlit.components.v1 as components
from utils.constants import COLOUR

STAGES = [
    (1, "1. Select Company", "Company Search & Verification"),
    (2, "2. Financials", "5-Year Statements & Ratios"),
    (3, "3. Forecast Model", "3-Statement Scenario Engine"),
    (4, "4. ML & Hybrid", "ML Forecasting & Blend"),
    (5, "5. Sensitivity", "Matrix & Stress Testing"),
    (6, "6. Risk Score", "Altman Z-Score & Red Flags"),
]


def render_stage_stepper():
    if 'current_stage' not in st.session_state:
        st.session_state['current_stage'] = 1
    if 'max_unlocked_stage' not in st.session_state:
        st.session_state['max_unlocked_stage'] = 1

    # Auto unlock check based on session state
    if st.session_state.get('company_info'):
        st.session_state['max_unlocked_stage'] = max(st.session_state['max_unlocked_stage'], 2)
    if st.session_state.get('clean_data'):
        st.session_state['max_unlocked_stage'] = max(st.session_state['max_unlocked_stage'], 3)
    if st.session_state.get('scenario_results'):
        st.session_state['max_unlocked_stage'] = max(st.session_state['max_unlocked_stage'], 4)
    if st.session_state.get('ml_results'):
        st.session_state['max_unlocked_stage'] = max(st.session_state['max_unlocked_stage'], 5)

    curr = st.session_state['current_stage']
    max_unlocked = st.session_state['max_unlocked_stage']

    progress_pct = int((curr / len(STAGES)) * 100)

    # Schematiq top header & gradient progress bar
    st.markdown(f"""
    <div style="margin-bottom: 20px; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="color:#64748b; font-size:0.8rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">
                STAGE {curr} OF {len(STAGES)} &nbsp;&bull;&nbsp; <span style="color:#0f172a;">{STAGES[curr-1][1]}</span>
            </span>
            <span style="color:#0f172a; font-size:0.85rem; font-weight:800;">{progress_pct}%</span>
        </div>
        <div style="background:#e2e8f0; height:6px; border-radius:100px; overflow:hidden; position:relative;">
            <div style="background: linear-gradient(90deg, #ff7e5f 0%, #feb47b 50%, #ff6b8b 100%); height:100%; width:{progress_pct}%; border-radius:100px; transition: width 0.4s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Render horizontal stage buttons
    cols = st.columns(len(STAGES))
    for idx, (stage_num, label, subtitle) in enumerate(STAGES):
        is_active = (stage_num == curr)
        is_unlocked = (stage_num <= max_unlocked)
        is_completed = (stage_num < max_unlocked)

        prefix = "✓ " if is_completed else ""
        btn_label = f"{prefix}{label}"

        with cols[idx]:
            if is_unlocked:
                btn_type = "primary" if is_active else "secondary"
                if st.button(btn_label, key=f"stage_nav_{stage_num}", type=btn_type, use_container_width=True):
                    st.session_state['current_stage'] = stage_num
                    st.session_state['_scroll_top'] = True
                    st.rerun()
            else:
                st.button(f"🔒 Stage {stage_num}", key=f"stage_nav_{stage_num}", disabled=True, use_container_width=True)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def scroll_to_top():
    """Inject JS to scroll the Streamlit page to the top immediately."""
    components.html(
        """<script>
        (function() {
            var pd = window.parent.document;
            var targets = [
                pd.querySelector('section.main'),
                pd.querySelector('[data-testid="stAppViewContainer"]'),
                pd.querySelector('.main'),
                pd.documentElement
            ];
            for (var i = 0; i < targets.length; i++) {
                if (targets[i]) {
                    targets[i].scrollTo({top: 0, behavior: 'instant'});
                }
            }
            window.parent.scrollTo({top: 0, behavior: 'instant'});
        })();
        </script>""",
        height=0,
    )


def proceed_to_stage(next_stage: int, button_label: str = None):
    """Render a high-contrast Schematiq-style proceed button."""
    if button_label is None:
        next_name = STAGES[next_stage - 1][1] if 1 <= next_stage <= len(STAGES) else "Next Stage"
        button_label = f"PROCEED TO {next_name.upper()} →"

    if st.button(button_label, type="primary", use_container_width=True, key=f"proceed_btn_stage_{next_stage}"):
        st.session_state['max_unlocked_stage'] = max(st.session_state.get('max_unlocked_stage', 1), next_stage)
        st.session_state['current_stage'] = next_stage
        st.session_state['_scroll_top'] = True
        st.rerun()
