# core/driver_analyzer.py
"""
Phase 3 — Historical driver analysis.

Builds the central DriverTable that drives Phase 4 and Phase 5.

For each driver:
  - Calculates historical yearly values
  - Computes average, median, std deviation, trend direction
  - Sets a 'base_forecast' value (used as Phase 4 base case)

Returns:
  drivers: dict  (the DriverTable)
  driver_df: pd.DataFrame  (tabular view for display)
"""

import logging
import numpy as np
import pandas as pd
from utils.formatting import safe_div, cagr

logger = logging.getLogger(__name__)


def _trend(series: pd.Series) -> str:
    """
    Determine trend direction from a time series.
    Uses linear regression slope relative to mean.
    """
    vals = series.dropna()
    if len(vals) < 2:
        return 'stable'
    x = np.arange(len(vals))
    try:
        slope, _ = np.polyfit(x, vals.values.astype(float), 1)
        mean_val = vals.mean()
        if abs(mean_val) < 1e-10:
            return 'stable'
        rel_slope = slope / abs(mean_val)
        std_rel   = vals.std() / abs(mean_val) if abs(mean_val) > 0 else 0

        if std_rel > 0.25:
            return 'volatile'
        if rel_slope > 0.02:
            return 'increasing'
        if rel_slope < -0.02:
            return 'declining'
        return 'stable'
    except Exception:
        return 'stable'


def _driver(series: pd.Series, label: str) -> dict:
    """
    Build a driver dict from a series of historical yearly values.
    series: index=FY strings, values=metric values (float)
    """
    clean = series.dropna()
    if clean.empty:
        return {
            'label':         label,
            'yearly':        {},
            'avg':           None,
            'median':        None,
            'std':           None,
            'recent':        None,
            'trend':         'stable',
            'base_forecast': None,
        }

    avg    = float(clean.mean())
    median = float(clean.median())
    std    = float(clean.std()) if len(clean) > 1 else 0.0
    recent = float(clean.iloc[-1])
    two_year_avg = float(clean.iloc[-2:].mean()) if len(clean) >= 2 else recent
    trend  = _trend(clean)

    # Momentum-weighted base forecast:
    # 60% most-recent year (captures latest momentum) + 40% 2-year average (stability anchor)
    # This prevents over-reliance on a single outlier year while staying current.
    momentum_base = 0.60 * recent + 0.40 * two_year_avg

    # Clip to ±2 std from historical average to prevent physically impossible forecasts
    if std > 0:
        lo = avg - 2.5 * std
        hi = avg + 2.5 * std
        momentum_base = float(np.clip(momentum_base, lo, hi))

    return {
        'label':         label,
        'yearly':        clean.to_dict(),
        'avg':           avg,
        'median':        median,
        'std':           std,
        'recent':        recent,
        'two_year_avg':  two_year_avg,
        'trend':         trend,
        'base_forecast': round(float(momentum_base), 4),
    }


def analyze_drivers(clean_data: dict, ratios_data: dict) -> dict:
    """
    Build the DriverTable from historical clean data and computed ratios.

    Args:
        clean_data:  output of data_cleaner.clean_financial_data()
        ratios_data: output of ratio_calculator.compute_ratios()

    Returns:
        dict:
          'drivers':   dict of driver dicts
          'driver_df': pd.DataFrame for display
          'errors':    list[str]
    """
    errors = []
    is_df    = clean_data.get('income_stmt',   pd.DataFrame())
    bs_df    = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df    = clean_data.get('cash_flow',     pd.DataFrame())
    ratios   = ratios_data.get('ratios_df',    pd.DataFrame())

    def r(col) -> pd.Series:
        """Get ratio series."""
        if col in ratios.columns:
            return ratios[col].astype(float)
        return pd.Series(dtype=float)

    def g(df, col) -> pd.Series:
        """Get column from a statement DataFrame."""
        if not df.empty and col in df.columns:
            return df[col].astype(float)
        return pd.Series(dtype=float)

    # ── Revenue growth ────────────────────────────────────────────────────────
    rev_growth = r('revenue_growth')
    d_rev_growth = _driver(rev_growth, 'Revenue Growth (%)')

    # ── Margin drivers ───────────────────────────────────────────────────────
    d_gross_margin  = _driver(r('gross_margin'),  'Gross Margin (%)')
    d_ebitda_margin = _driver(r('ebitda_margin'), 'EBITDA Margin (%)')
    d_ebit_margin   = _driver(r('ebit_margin'),   'EBIT Margin (%)')
    d_net_margin    = _driver(r('net_margin'),     'Net Profit Margin (%)')

    # ── Tax rate ────────────────────────────────────────────────────────────
    d_tax_rate = _driver(r('effective_tax_rate'), 'Effective Tax Rate (%)')

    # ── Working capital ────────────────────────────────────────────────────────
    d_rec_days  = _driver(r('receivable_days'), 'Receivable Days')
    d_inv_days  = _driver(r('inventory_days'),  'Inventory Days')
    d_pay_days  = _driver(r('payable_days'),    'Payable Days')

    # ── Capex & D&A ───────────────────────────────────────────────────────────
    d_capex_rev = _driver(r('capex_to_revenue'), 'Capex / Revenue (%)')
    d_da_rev    = _driver(r('da_to_revenue'),    'D&A / Revenue (%)')

    # ── Debt & leverage ────────────────────────────────────────────────────────
    d_de = _driver(r('debt_to_equity'), 'Debt / Equity')
    d_ic = _driver(r('interest_coverage'), 'Interest Coverage')

    # ── Interest rate (interest expense / avg total debt) ─────────────────────
    interest_exp = g(is_df, 'interest_expense').abs()
    total_debt   = g(bs_df, 'total_debt') if 'total_debt' in bs_df.columns else \
                   (g(bs_df, 'short_term_debt').fillna(0) + g(bs_df, 'long_term_debt').fillna(0))
    avg_debt = (total_debt + total_debt.shift(1)) / 2
    int_rate_series = safe_div(interest_exp, avg_debt) * 100
    if hasattr(int_rate_series, 'replace'):
        int_rate_series = int_rate_series.replace([np.inf, -np.inf], np.nan)
    d_interest_rate = _driver(
        int_rate_series if isinstance(int_rate_series, pd.Series) else pd.Series(dtype=float),
        'Avg Cost of Debt (%)'
    )

    # ── Dividend payout ──────────────────────────────────────────────────────
    d_div_payout = _driver(r('dividend_payout'), 'Dividend Payout (%)')

    # ── Assemble DriverTable ───────────────────────────────────────────────────
    drivers = {
        'revenue_growth':  d_rev_growth,
        'gross_margin':    d_gross_margin,
        'ebitda_margin':   d_ebitda_margin,
        'ebit_margin':     d_ebit_margin,
        'net_margin':      d_net_margin,
        'effective_tax_rate': d_tax_rate,
        'receivable_days': d_rec_days,
        'inventory_days':  d_inv_days,
        'payable_days':    d_pay_days,
        'capex_to_revenue': d_capex_rev,
        'da_to_revenue':   d_da_rev,
        'debt_to_equity':  d_de,
        'interest_coverage': d_ic,
        'interest_rate':   d_interest_rate,
        'dividend_payout': d_div_payout,
    }

    # ── Build tabular display DataFrame ────────────────────────────────────────
    rows = []
    for key, d in drivers.items():
        rows.append({
            'Driver':            d.get('label', key),
            '5-Yr Avg':          d.get('avg'),
            '2-Yr Avg':          d.get('two_year_avg'),
            'Recent':            d.get('recent'),
            'Std Dev':           d.get('std'),
            'Trend':             d.get('trend', 'stable'),
            'Base Forecast (2-Yr Avg)': d.get('base_forecast'),
        })
    driver_df = pd.DataFrame(rows)

    return {
        'drivers':   drivers,
        'driver_df': driver_df,
        'errors':    errors,
    }
