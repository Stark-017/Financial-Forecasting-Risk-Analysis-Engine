# core/risk_engine.py
"""
Phase 9 — Financial Risk & Health Scoring Engine.

Calculates:
  1. Altman Z-Score (Bankruptcy / Distress Risk) — with NaN guards
  2. Piotroski F-Score (9-point financial health indicator)
  3. DuPont Decomposition (ROE = Net Margin × Asset Turnover × Equity Multiplier)
  4. Financial Health Score (0–100) across 5 pillars
  5. Automated Red Flags & Financial Warning Indicators
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from utils.constants import RISK_THRESHOLDS

logger = logging.getLogger(__name__)


def _safe(df: pd.DataFrame, col: str, fy, default: float = 0.0) -> float:
    """Safe NaN-guarded value fetch from a DataFrame."""
    try:
        v = float(df.loc[fy, col])
        return default if (v != v) else v   # NaN check via self-inequality
    except Exception:
        return default


def _last(df: pd.DataFrame, col: str, default: float = 0.0) -> float:
    """Get the last non-NaN value for a column across all rows."""
    if df.empty or col not in df.columns:
        return default
    s = df[col].dropna()
    return float(s.iloc[-1]) if not s.empty else default


# ─── 1. ALTMAN Z-SCORE ───────────────────────────────────────────────────────

def compute_altman_z_score(is_df: pd.DataFrame, bs_df: pd.DataFrame,
                            market_cap_cr: float = None) -> dict:
    """
    Altman Z-Score for corporate distress risk:
      Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 0.999×X5
    """
    if is_df.empty or bs_df.empty:
        return {'z_score': None, 'zone': 'Unknown',
                'description': 'Insufficient data', 'components': {}, 'color': '#94a3b8'}

    fy = bs_df.index[-1]

    rev      = _safe(is_df, 'revenue',             fy, 0.0)
    ebit     = _safe(is_df, 'ebit',                fy, 0.0)
    assets   = _safe(bs_df, 'total_assets',        fy, 1.0) or 1.0
    liab     = _safe(bs_df, 'total_liabilities',   fy, 1.0) or 1.0
    equity   = _safe(bs_df, 'total_equity',        fy, 1.0)
    ret_earn = _safe(bs_df, 'retained_earnings',   fy, 0.0)
    curr_a   = _safe(bs_df, 'total_current_assets',    fy, 0.0)
    curr_l   = _safe(bs_df, 'total_current_liabilities', fy, 0.0)

    working_cap = curr_a - curr_l

    x1 = working_cap / assets
    x2 = ret_earn    / assets
    x3 = ebit        / assets
    x4 = (market_cap_cr if market_cap_cr else equity) / max(liab, 1.0)
    x5 = rev         / assets

    z_score = round(1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 0.999*x5, 2)

    if z_score != z_score:   # still NaN
        return {'z_score': None, 'zone': 'Unknown',
                'description': 'Could not compute — missing balance sheet data',
                'components': {}, 'color': '#94a3b8'}

    if z_score >= 2.99:
        zone = 'Safe Zone';     color = '#10b981'
        desc = 'Low probability of financial distress. Company appears financially healthy.'
    elif z_score >= 1.81:
        zone = 'Grey Zone';     color = '#f59e0b'
        desc = 'Moderate distress risk. Monitor financial ratios closely.'
    else:
        zone = 'Distress Zone'; color = '#ef4444'
        desc = 'High risk of financial distress. Company may face solvency challenges.'

    return {
        'z_score':     z_score,
        'zone':        zone,
        'color':       color,
        'description': desc,
        'components':  {
            'X1 Working Capital / Assets':   round(x1, 3),
            'X2 Retained Earnings / Assets': round(x2, 3),
            'X3 EBIT / Assets':              round(x3, 3),
            'X4 MktCap / Total Liabilities': round(x4, 3),
            'X5 Revenue / Assets':           round(x5, 3),
        },
    }


# ─── 2. PIOTROSKI F-SCORE ────────────────────────────────────────────────────

def compute_piotroski_f_score(is_df: pd.DataFrame, bs_df: pd.DataFrame,
                               cf_df: pd.DataFrame) -> dict:
    """
    Piotroski F-Score (0–9): 9 binary signals across 3 dimensions.
      Profitability (4): ROA, CFO, Δ ROA, Accruals
      Leverage (3): Δ D/E, Δ Current Ratio, No New Equity
      Efficiency (2): Δ Gross Margin, Δ Asset Turnover
    Score 8-9 = Strong, 5-7 = Moderate, 0-4 = Weak
    """
    if is_df.empty or bs_df.empty:
        return {'f_score': None, 'strength': 'Unknown', 'signals': {}, 'color': '#94a3b8'}

    fys = list(is_df.index)
    if len(fys) < 2:
        return {'f_score': None, 'strength': 'Insufficient history (need ≥2 years)',
                'signals': {}, 'color': '#94a3b8'}

    fy_now  = fys[-1]
    fy_prev = fys[-2]

    def _is(col, fy):  return _safe(is_df, col, fy, np.nan)
    def _bs(col, fy):  return _safe(bs_df, col, fy, np.nan)
    def _cf(col, fy):  return _safe(cf_df, col, fy, np.nan) if not cf_df.empty else np.nan

    # ── Profitability signals ─────────────────────────────────────────────────
    roa_now  = _is('net_income', fy_now)  / max(abs(_bs('total_assets', fy_now)), 1)
    roa_prev = _is('net_income', fy_prev) / max(abs(_bs('total_assets', fy_prev)), 1)
    cfo      = _cf('cash_from_operations', fy_now)
    assets_n = _bs('total_assets', fy_now)

    p1_roa_pos   = int(roa_now > 0)                   # ROA > 0
    p2_cfo_pos   = int(cfo > 0)                       # CFO > 0
    p3_droa_pos  = int(roa_now > roa_prev)            # ROA improving
    p4_accruals  = int(cfo / max(abs(assets_n), 1) > roa_now)  # CFO/Assets > ROA (quality)

    # ── Leverage / Liquidity signals ─────────────────────────────────────────
    de_now  = (_bs('total_debt', fy_now)  or 0) / max(abs(_bs('total_equity', fy_now)), 1)
    de_prev = (_bs('total_debt', fy_prev) or 0) / max(abs(_bs('total_equity', fy_prev)), 1)

    curr_r_now  = _bs('total_current_assets', fy_now)  / max(abs(_bs('total_current_liabilities', fy_now)), 1)
    curr_r_prev = _bs('total_current_assets', fy_prev) / max(abs(_bs('total_current_liabilities', fy_prev)), 1)

    sc_now  = _bs('share_capital', fy_now)
    sc_prev = _bs('share_capital', fy_prev)

    l1_lever_lower = int(de_now < de_prev)         # D/E improved
    l2_liq_higher  = int(curr_r_now > curr_r_prev) # Current ratio improved
    l3_no_dilution = int(sc_now <= sc_prev * 1.01)  # No significant new equity

    # ── Efficiency signals ────────────────────────────────────────────────────
    gm_now  = (_is('gross_profit', fy_now)  / max(_is('revenue', fy_now),  1))
    gm_prev = (_is('gross_profit', fy_prev) / max(_is('revenue', fy_prev), 1))
    at_now  = _is('revenue', fy_now)  / max(abs(_bs('total_assets', fy_now)),  1)
    at_prev = _is('revenue', fy_prev) / max(abs(_bs('total_assets', fy_prev)), 1)

    e1_gm_higher = int(gm_now > gm_prev)  # Gross margin improved
    e2_at_higher = int(at_now > at_prev)  # Asset turnover improved

    signals = {
        '✅ ROA Positive':              ('Profitability', p1_roa_pos),
        '✅ Cash Flow from Ops Positive': ('Profitability', p2_cfo_pos),
        '✅ ROA Improving YoY':          ('Profitability', p3_droa_pos),
        '✅ Earnings Quality (CFO>ROA)': ('Profitability', p4_accruals),
        '✅ D/E Ratio Declining':        ('Leverage',      l1_lever_lower),
        '✅ Current Ratio Improving':    ('Leverage',      l2_liq_higher),
        '✅ No Equity Dilution':         ('Leverage',      l3_no_dilution),
        '✅ Gross Margin Expanding':     ('Efficiency',    e1_gm_higher),
        '✅ Asset Turnover Improving':   ('Efficiency',    e2_at_higher),
    }

    f_score = sum(v for _, (_, v) in signals.items())

    if f_score >= 8:   strength = 'Strong';   color = '#10b981'
    elif f_score >= 5: strength = 'Moderate'; color = '#f59e0b'
    else:              strength = 'Weak';     color = '#ef4444'

    return {
        'f_score':  f_score,
        'strength': strength,
        'color':    color,
        'signals':  signals,
        'max':      9,
    }


# ─── 3. DUPONT DECOMPOSITION ─────────────────────────────────────────────────

def compute_dupont(is_df: pd.DataFrame, bs_df: pd.DataFrame) -> dict:
    """
    3-factor DuPont Decomposition:
      ROE = Net Margin × Asset Turnover × Financial Leverage (Equity Multiplier)
    """
    if is_df.empty or bs_df.empty:
        return {'error': 'Insufficient data'}

    results = {}
    for fy in is_df.index:
        if fy not in bs_df.index:
            continue
        ni  = _safe(is_df, 'net_income', fy, 0.0)
        rev = _safe(is_df, 'revenue',    fy, 1.0) or 1.0
        ta  = _safe(bs_df, 'total_assets', fy, 1.0) or 1.0
        eq  = _safe(bs_df, 'total_equity', fy, 1.0) or 1.0

        net_margin  = ni  / rev
        asset_turn  = rev / ta
        eq_mult     = ta  / eq
        roe         = net_margin * asset_turn * eq_mult

        results[fy] = {
            'net_margin':          round(net_margin * 100, 2),
            'asset_turnover':      round(asset_turn, 3),
            'equity_multiplier':   round(eq_mult, 3),
            'roe':                 round(roe * 100, 2),
            'roe_check':           round(ni / eq * 100, 2),
        }

    return results


# ─── 4. FINANCIAL HEALTH SCORE ───────────────────────────────────────────────

def compute_health_score(is_df: pd.DataFrame, bs_df: pd.DataFrame,
                          cf_df: pd.DataFrame, ratios_df: pd.DataFrame) -> dict:
    """
    5-pillar financial health scorecard (0–100, higher = healthier).
    Pillars: Profitability, Liquidity, Leverage, Efficiency, Growth
    """
    if ratios_df is None or ratios_df.empty:
        return {'score': 50, 'grade': 'B', 'breakdown': {}, 'color': '#f59e0b'}

    r = ratios_df.iloc[-1]

    def _score_hi(val, good_v, bad_v) -> float:
        """Higher-is-better metric. Returns 0–100."""
        if val is None or (isinstance(val, float) and val != val):
            return 50.0
        try:
            v = float(val)
        except Exception:
            return 50.0
        if v >= good_v: return 90.0
        if v <= bad_v:  return 10.0
        return round(10 + 80 * (v - bad_v) / max(good_v - bad_v, 1e-9), 1)

    def _score_lo(val, good_v, bad_v) -> float:
        """Lower-is-better metric. Returns 0–100."""
        if val is None or (isinstance(val, float) and val != val):
            return 50.0
        try:
            v = float(val)
        except Exception:
            return 50.0
        if v <= good_v: return 90.0
        if v >= bad_v:  return 10.0
        return round(10 + 80 * (bad_v - v) / max(bad_v - good_v, 1e-9), 1)

    breakdown = {
        'Profitability': round(np.mean([
            _score_hi(r.get('ebitda_margin'),      20,  5),
            _score_hi(r.get('net_margin'),         10,  0),
            _score_hi(r.get('roe'),                15,  2),
            _score_hi(r.get('roa'),                 8,  1),
        ]), 1),
        'Liquidity': round(np.mean([
            _score_hi(r.get('current_ratio'),       2.0, 1.0),
            _score_hi(r.get('quick_ratio'),         1.5, 0.8),
        ]), 1),
        'Leverage': round(np.mean([
            _score_lo(r.get('debt_to_equity'),      0.5, 2.0),
            _score_hi(r.get('interest_coverage'),   5.0, 1.5),
        ]), 1),
        'Efficiency': round(np.mean([
            _score_hi(r.get('asset_turnover'),      1.0, 0.3),
            _score_lo(r.get('receivable_days'),     30,  90),
            _score_lo(r.get('inventory_days'),      30,  120),
        ]), 1),
        'Growth': round(np.mean([
            _score_hi(r.get('revenue_growth'),      15,  0),
            _score_hi(r.get('fcf_margin'),          10,  0),
        ]), 1),
    }

    weights = {'Profitability': 0.30, 'Liquidity': 0.20,
               'Leverage': 0.20, 'Efficiency': 0.15, 'Growth': 0.15}
    score = round(sum(breakdown[k] * weights[k] for k in breakdown), 1)

    if score >= 80:   grade = 'A+'; color = '#10b981'
    elif score >= 70: grade = 'A';  color = '#34d399'
    elif score >= 60: grade = 'B+'; color = '#f59e0b'
    elif score >= 50: grade = 'B';  color = '#fbbf24'
    elif score >= 40: grade = 'C';  color = '#f97316'
    else:             grade = 'D';  color = '#ef4444'

    return {'score': score, 'grade': grade, 'color': color, 'breakdown': breakdown}


# ─── 5. RED FLAGS ────────────────────────────────────────────────────────────

def flag_red_flags(is_df: pd.DataFrame, bs_df: pd.DataFrame,
                   cf_df: pd.DataFrame, ratios_df: pd.DataFrame) -> List[dict]:
    """
    Detect financial red flags and warning indicators.
    Returns list of {'title', 'message', 'severity': 'HIGH'|'MEDIUM'|'LOW'}.
    """
    flags = []

    if is_df.empty or bs_df.empty:
        return flags

    def _flag(title, msg, severity='HIGH'):
        flags.append({'title': title, 'message': msg, 'severity': severity})

    r = ratios_df.iloc[-1] if (ratios_df is not None and not ratios_df.empty) else pd.Series()

    def _rv(key, default=None):
        try:
            v = r.get(key, default)
            return float(v) if v is not None else default
        except Exception:
            return default

    # Profitability flags
    nm = _rv('net_margin')
    if nm is not None and nm < 0:
        _flag('Negative Net Profit Margin',
              f'Net Margin is {nm:.1f}%. Company is losing money on its operations.', 'HIGH')
    elif nm is not None and nm < 2:
        _flag('Very Thin Profit Margin',
              f'Net Margin at {nm:.1f}% — very little cushion against adverse events.', 'MEDIUM')

    # Debt flags
    de = _rv('debt_to_equity')
    if de is not None and de > 3.0:
        _flag('Very High Debt-to-Equity',
              f'D/E ratio is {de:.2f}×. Highly leveraged — interest burden risk.', 'HIGH')
    elif de is not None and de > 1.5:
        _flag('Elevated Leverage',
              f'D/E ratio is {de:.2f}×. Monitor debt service capacity.', 'MEDIUM')

    # Interest coverage
    ic = _rv('interest_coverage')
    if ic is not None and ic < 1.0:
        _flag('Interest Coverage Below 1× (Distress Signal)',
              f'EBIT ({ic:.2f}×) does not cover interest expense. Potential default risk.', 'HIGH')
    elif ic is not None and ic < 2.5:
        _flag('Low Interest Coverage',
              f'Interest coverage is {ic:.2f}× — limited buffer for earnings shocks.', 'MEDIUM')

    # Liquidity
    cr = _rv('current_ratio')
    if cr is not None and cr < 1.0:
        _flag('Current Ratio Below 1 (Liquidity Crisis Risk)',
              f'Current ratio is {cr:.2f}× — current liabilities exceed current assets.', 'HIGH')

    # Cash flow quality
    if not cf_df.empty:
        fy = cf_df.index[-1]
        cfo = _safe(cf_df, 'cash_from_operations', fy, None)
        ni  = _safe(is_df, 'net_income', fy, None) if not is_df.empty and fy in is_df.index else None
        if cfo is not None and cfo < 0:
            _flag('Negative Operating Cash Flow',
                  f'CFO is ₹{cfo:,.0f} Cr — the company is consuming cash from operations.', 'HIGH')
        if cfo is not None and ni is not None and ni > 0 and cfo < ni * 0.3:
            _flag('Low Cash Flow Quality (Earnings not backed by cash)',
                  f'Net Income ₹{ni:,.0f} Cr but CFO only ₹{cfo:,.0f} Cr. Possible aggressive accruals.', 'MEDIUM')

    # Revenue growth
    rg = _rv('revenue_growth')
    if rg is not None and rg < -10:
        _flag('Significant Revenue Contraction',
              f'Revenue declined {rg:.1f}% YoY — demand or competitive concern.', 'HIGH')

    # Working capital deterioration
    rec = _rv('receivable_days')
    if rec is not None and rec > 90:
        _flag('High Receivable Days (Collection Risk)',
              f'Receivable Days = {rec:.0f} — slow customer payments, cash flow pressure.', 'MEDIUM')

    inv = _rv('inventory_days')
    if inv is not None and inv > 120:
        _flag('High Inventory Days (Demand / Obsolescence Risk)',
              f'Inventory Days = {inv:.0f} — excess inventory or slow-moving goods.', 'MEDIUM')

    return sorted(flags, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['severity']])
