# core/scenario_engine.py
"""
Phase 5 — Economic Scenario Engine.

Generates Good, Base, and Bad economic scenarios by modifying financial
drivers based on historical volatility (sigma-based adjustments).

Key functions:
  build_scenario_assumptions(drivers)  -> {'good': dict, 'base': dict, 'bad': dict}
  run_scenarios(clean_data, drivers, custom_assumptions=None, n_years=3)
    -> {'good': ForecastOutput, 'base': ForecastOutput, 'bad': ForecastOutput,
        'comparison': pd.DataFrame, 'resilience': dict}
"""

import logging
import numpy as np
import pandas as pd
from utils.constants import SCENARIO_DEFAULTS, COLOUR, RISK_THRESHOLDS
from core.forecast_engine import build_forecast

logger = logging.getLogger(__name__)


def _get_driver_val(drivers: dict, key: str, field: str = 'base_forecast', default=None):
    d = drivers.get(key, {})
    return d.get(field, default)


def _sigma(drivers: dict, key: str) -> float:
    """Return historical std deviation for a driver (used to scale scenario spreads)."""
    d = drivers.get(key, {})
    std = d.get('std', None)
    if std is None or std == 0:
        # Fall back to 20% of average
        avg = abs(d.get('avg', 1.0) or 1.0)
        return avg * 0.20
    return float(std)


def build_scenario_assumptions(drivers: dict) -> dict:
    """
    Build Good, Base, and Bad scenario assumption dicts using percentile-based distributions.

    Methodology:
      - Extracts yearly historical values for each key driver
      - Good  = 75th percentile (favourable tail)
      - Base  = 55th percentile (slightly above median — survivorship bias adjustment)
      - Bad   = 25th percentile (adverse tail)
      - All values clipped to financially sensible bounds

    This approach is strictly data-driven and avoids the arbitrary sigma-multiplier
    problem that caused 70% bad-scenario misses in the previous version.
    """

    def _pct_val(key: str, fallback: float, pct: float) -> float:
        """Extract yearly historical values and return given percentile."""
        d = drivers.get(key, {})
        yearly = d.get('yearly', {})
        if yearly:
            vals = [v for v in yearly.values() if v is not None and not np.isnan(float(v))]
            if vals:
                return float(np.percentile(vals, pct))
        # Fallback to base_forecast ± adjustment
        base = d.get('base_forecast', fallback) or fallback
        spread = abs(base) * 0.15  # ±15% if no history
        if pct >= 70:
            return base + spread
        elif pct <= 30:
            return base - spread
        return base

    # ── Revenue Growth ────────────────────────────────────────────────────────
    rev_good  = float(np.clip(_pct_val('revenue_growth', 7.0, 75), -5.0,  40.0))
    rev_base  = float(np.clip(_pct_val('revenue_growth', 7.0, 55), -10.0, 35.0))
    rev_bad   = float(np.clip(_pct_val('revenue_growth', 7.0, 25), -20.0, 25.0))
    # Enforce ordering: bad < base < good
    rev_bad   = min(rev_bad,  rev_base - 1.0)
    rev_good  = max(rev_good, rev_base + 1.0)

    # ── EBITDA Margin ─────────────────────────────────────────────────────────
    em_good = float(np.clip(_pct_val('ebitda_margin', 20.0, 75), 2.0,  60.0))
    em_base = float(np.clip(_pct_val('ebitda_margin', 20.0, 55), 1.0,  55.0))
    em_bad  = float(np.clip(_pct_val('ebitda_margin', 20.0, 25), 0.5,  50.0))
    em_bad  = min(em_bad,  em_base - 0.5)
    em_good = max(em_good, em_base + 0.5)

    # ── Gross Margin ──────────────────────────────────────────────────────────
    gm_base = float(np.clip(_pct_val('gross_margin', 40.0, 55), 5.0, 95.0))
    gm_good = float(np.clip(_pct_val('gross_margin', 40.0, 70), 5.0, 95.0))
    gm_bad  = float(np.clip(_pct_val('gross_margin', 40.0, 30), 5.0, 95.0))

    # ── Fixed/stable drivers (use base_forecast for base; modest tweaks for scenarios) ──
    def _base(key: str, fallback: float) -> float:
        d = drivers.get(key, {})
        return float(d.get('base_forecast', fallback) or fallback)

    tax_base = float(np.clip(_base('effective_tax_rate', 25.0), 10.0, 45.0))
    da_base  = float(np.clip(_base('da_to_revenue',      4.0),  0.5,  20.0))
    rec_base = float(np.clip(_base('receivable_days',    45.0), 10.0, 180.0))
    inv_base = float(np.clip(_base('inventory_days',     30.0),  5.0, 180.0))
    pay_base = float(np.clip(_base('payable_days',       40.0), 10.0, 150.0))
    cap_base = float(np.clip(_base('capex_to_revenue',   5.0),  0.5,  25.0))
    int_base = float(np.clip(_base('interest_rate',      6.0),  2.0,  20.0))
    div_base = float(np.clip(_base('dividend_payout',    30.0), 0.0,  90.0))

    base = {
        'revenue_growth':     rev_base,
        'ebitda_margin':      em_base,
        'gross_margin':       gm_base,
        'da_to_revenue':      da_base,
        'effective_tax_rate': tax_base,
        'receivable_days':    rec_base,
        'inventory_days':     inv_base,
        'payable_days':       pay_base,
        'capex_to_revenue':   cap_base,
        'interest_rate':      int_base,
        'dividend_payout':    div_base,
        'debt_repay_rate':    0.03,
    }

    good = base.copy()
    good.update({
        'revenue_growth':    rev_good,
        'ebitda_margin':     em_good,
        'gross_margin':      gm_good,
        'receivable_days':   max(rec_base * 0.88, 10.0),
        'inventory_days':    max(inv_base * 0.92, 5.0),
        'capex_to_revenue':  cap_base * 1.10,      # invest more when things are good
        'interest_rate':     max(int_base - 0.30, 2.0),
        'effective_tax_rate': max(tax_base - 0.50, 10.0),
        'debt_repay_rate':   0.05,
    })

    bad = base.copy()
    bad.update({
        'revenue_growth':    rev_bad,
        'ebitda_margin':     em_bad,
        'gross_margin':      gm_bad,
        'receivable_days':   min(rec_base * 1.18, 180.0),
        'inventory_days':    min(inv_base * 1.12, 180.0),
        'payable_days':      min(pay_base * 1.08, 150.0),
        'capex_to_revenue':  cap_base * 0.72,      # cut capex in downturns
        'interest_rate':     min(int_base + 0.60, 20.0),
        'effective_tax_rate': min(tax_base + 1.00, 45.0),
        'debt_repay_rate':   0.01,
    })

    return {'good': good, 'base': base, 'bad': bad}


def _score_resilience(ratios_df: pd.DataFrame) -> dict:
    """
    Score financial resilience from 0 (best) to 100 (worst).
    Uses RISK_THRESHOLDS from constants.
    """
    if ratios_df is None or ratios_df.empty:
        return {'score': 50, 'classification': 'Unknown', 'breakdown': {}}

    # Use last forecast year
    r = ratios_df.iloc[-1]

    def score_metric(val, metric_key, higher_is_better=True):
        """Score 0-100 for a metric; 0=best."""
        if val is None or (hasattr(val, '__float__') and np.isnan(float(val))):
            return 50  # unknown
        t = RISK_THRESHOLDS.get(metric_key, {})
        good_t = t.get('good', None)
        bad_t  = t.get('bad',  None)
        if good_t is None or bad_t is None:
            return 50
        try:
            v = float(val)
        except (TypeError, ValueError):
            return 50

        if higher_is_better:
            if v >= good_t:   return 5
            if v <= bad_t:    return 95
            # Linear interpolation
            return int(5 + 90 * (good_t - v) / (good_t - bad_t + 1e-9))
        else:  # lower is better (e.g., D/E)
            if v <= good_t:   return 5
            if v >= bad_t:    return 95
            return int(5 + 90 * (v - good_t) / (bad_t - good_t + 1e-9))

    breakdown = {
        'liquidity':      score_metric(r.get('current_ratio'), 'current_ratio', True),
        'leverage':       score_metric(r.get('debt_to_equity'), 'debt_to_equity', False),
        'profitability':  score_metric(r.get('ebitda_margin'), 'ebitda_margin_pct', True),
        'cash_flow':      score_metric(r.get('fcf_margin'), 'fcf_margin_pct', True),
        'debt_service':   score_metric(r.get('interest_coverage'), 'interest_coverage', True),
    }

    weights = {
        'liquidity': 0.20,
        'leverage':  0.25,
        'profitability': 0.25,
        'cash_flow': 0.20,
        'debt_service': 0.10,
    }

    overall = sum(breakdown[k] * weights[k] for k in breakdown)
    overall = round(overall, 1)

    if overall <= 20:    classification = 'Low Risk'
    elif overall <= 40:  classification = 'Moderate Risk'
    elif overall <= 60:  classification = 'Elevated Risk'
    elif overall <= 80:  classification = 'High Risk'
    else:                classification = 'Very High Risk'

    return {
        'score':          overall,
        'classification': classification,
        'breakdown':      breakdown,
    }


def build_comparison_table(scenarios: dict) -> pd.DataFrame:
    """
    Build a side-by-side comparison DataFrame for all three scenarios.
    """
    rows = []
    metrics = [
        ('Revenue (Cr)',        'income_stmt',  'revenue'),
        ('EBITDA (Cr)',         'income_stmt',  'ebitda'),
        ('Net Income (Cr)',     'income_stmt',  'net_income'),
        ('EBITDA Margin (%)',   'ratios',       'ebitda_margin'),
        ('Net Margin (%)',      'ratios',       'net_margin'),
        ('FCF (Cr)',            'ratios',       'fcf'),
        ('Cash (Cr)',           'balance_sheet','cash'),
        ('Total Debt (Cr)',     'balance_sheet','total_debt'),
        ('Debt / Equity',       'ratios',       'debt_to_equity'),
        ('Interest Coverage',   'ratios',       'interest_coverage'),
        ('ROE (%)',             'ratios',       'roe'),
        ('ROA (%)',             'ratios',       'roa'),
    ]

    for scen_name, fo in scenarios.items():
        for fy in fo.get('forecast_years', []):
            for display_name, stmt, col in metrics:
                df = fo.get(stmt, pd.DataFrame())
                val = None
                if not df.empty and col in df.columns and fy in df.index:
                    val = df.loc[fy, col]
                rows.append({
                    'Scenario': scen_name.capitalize(),
                    'FY':       fy,
                    'Metric':   display_name,
                    'Value':    val,
                })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Pivot: Scenario x FY vs Metric
    pivot = df.pivot_table(index='Metric', columns=['Scenario', 'FY'],
                            values='Value', aggfunc='first')
    return pivot


def run_scenarios(clean_data: dict, drivers: dict,
                  custom_assumptions: dict = None,
                  n_years: int = 1) -> dict:
    """
    Run all three economic scenarios.

    Args:
        clean_data:          cleaned historical data
        drivers:             DriverTable from driver_analyzer
        custom_assumptions:  optional dict of {'good': {...}, 'base': {...}, 'bad': {...}}
                             Partial overrides are merged with auto-generated assumptions.
        n_years:             forecast horizon

    Returns:
        dict:
          'good':       ForecastOutput
          'base':       ForecastOutput
          'bad':        ForecastOutput
          'assumptions': {'good': dict, 'base': dict, 'bad': dict}
          'comparison': pd.DataFrame
          'resilience': {'good': dict, 'base': dict, 'bad': dict}
    """
    # Build auto assumptions
    auto_assumptions = build_scenario_assumptions(drivers)

    # Merge with custom overrides
    final_assumptions = {}
    for scenario in ['good', 'base', 'bad']:
        final_assumptions[scenario] = auto_assumptions[scenario].copy()
        if custom_assumptions and scenario in custom_assumptions:
            final_assumptions[scenario].update(custom_assumptions[scenario])

    # Run forecasts
    scenarios = {}
    resilience = {}
    for scenario in ['good', 'base', 'bad']:
        try:
            fo = build_forecast(
                clean_data=clean_data,
                drivers=drivers,
                assumptions=final_assumptions[scenario],
                scenario=scenario,
                n_years=n_years,
            )
            scenarios[scenario] = fo
            resilience[scenario] = _score_resilience(fo.get('ratios', pd.DataFrame()))
        except Exception as e:
            logger.error(f"Scenario {scenario} failed: {e}")
            scenarios[scenario] = {'scenario': scenario, 'error': str(e)}
            resilience[scenario] = {'score': 50, 'classification': 'Unknown', 'breakdown': {}}

    # Build comparison table
    try:
        comparison = build_comparison_table(scenarios)
    except Exception as e:
        logger.warning(f"Comparison table failed: {e}")
        comparison = pd.DataFrame()

    return {
        'good':        scenarios.get('good', {}),
        'base':        scenarios.get('base', {}),
        'bad':         scenarios.get('bad',  {}),
        'assumptions': final_assumptions,
        'comparison':  comparison,
        'resilience':  resilience,
    }
