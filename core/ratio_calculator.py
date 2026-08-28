# core/ratio_calculator.py
"""
Phase 2 — Historical financial ratio computation.

Computes from standardised DataFrames:
  - Growth rates (YoY, CAGR)
  - Profitability ratios (margins, ROE, ROA)
  - Liquidity ratios
  - Leverage ratios
  - Cash flow metrics

Returns:
  ratios_df: pd.DataFrame  (index=FY, cols=ratio names)
  summary:   dict          (key metrics summarised)
"""

import logging
import pandas as pd
import numpy as np
from utils.formatting import safe_div, cagr

logger = logging.getLogger(__name__)


def _yoy(series: pd.Series) -> pd.Series:
    """Year-over-year % growth."""
    pct = series.pct_change() * 100
    return pct.replace([np.inf, -np.inf], np.nan)


def compute_ratios(clean_data: dict) -> dict:
    """
    Compute all historical financial ratios.

    Args:
        clean_data: output of data_cleaner.clean_financial_data()

    Returns:
        dict:
          'ratios_df':  pd.DataFrame  (index=FY, cols=ratio names)
          'summary':    dict           (CAGR, avg margins, etc.)
          'errors':     list[str]
    """
    is_df = clean_data.get('income_stmt', pd.DataFrame())
    bs_df = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df = clean_data.get('cash_flow', pd.DataFrame())
    errors = []

    # Align all on common FY index
    all_fys = sorted(set(
        list(is_df.index) + list(bs_df.index) + list(cf_df.index)
    ))
    all_fys = [fy for fy in all_fys if fy.startswith('FY')]

    ratios = pd.DataFrame(index=all_fys)

    def get(df, col, fy):
        """Safely get value from a DataFrame."""
        if df.empty or col not in df.columns or fy not in df.index:
            return np.nan
        val = df.loc[fy, col]
        return float(val) if not pd.isna(val) else np.nan

    def gets(df, col):
        """Get full series for a column, reindexed to all_fys."""
        if df.empty or col not in df.columns:
            return pd.Series(np.nan, index=all_fys)
        return df[col].reindex(all_fys).astype(float)

    # ── Revenue metrics ───────────────────────────────────────────────────────
    rev    = gets(is_df, 'revenue')
    ebitda = gets(is_df, 'ebitda')
    ebit   = gets(is_df, 'ebit')
    ni     = gets(is_df, 'net_income')
    cogs   = gets(is_df, 'cost_of_goods_sold')
    gp     = gets(is_df, 'gross_profit')
    da     = gets(is_df, 'depreciation_amortization')
    interest = gets(is_df, 'interest_expense')
    pbt    = gets(is_df, 'profit_before_tax')
    tax    = gets(is_df, 'tax_expense')

    # BS
    total_assets = gets(bs_df, 'total_assets')
    total_equity = gets(bs_df, 'total_equity')
    total_liab   = gets(bs_df, 'total_liabilities')
    total_debt   = gets(bs_df, 'total_debt') if 'total_debt' in bs_df.columns else \
                   gets(bs_df, 'short_term_debt').fillna(0) + gets(bs_df, 'long_term_debt').fillna(0)
    cash         = gets(bs_df, 'cash')
    curr_assets  = gets(bs_df, 'total_current_assets')
    curr_liab    = gets(bs_df, 'total_current_liabilities')
    inventory    = gets(bs_df, 'inventory')
    receivables  = gets(bs_df, 'trade_receivables')
    payables     = gets(bs_df, 'trade_payables')
    ppe          = gets(bs_df, 'net_ppe')
    retained     = gets(bs_df, 'retained_earnings')

    # CF
    cfo   = gets(cf_df, 'cash_from_operations')
    capex = gets(cf_df, 'capex')
    fcf   = gets(cf_df, 'free_cash_flow')
    if fcf.isna().all() and not cfo.isna().all():
        fcf = cfo.fillna(0) + capex.fillna(0)  # capex negative

    # ── Growth rates ──────────────────────────────────────────────────────────
    ratios['revenue_growth']  = _yoy(rev)
    ratios['ebitda_growth']   = _yoy(ebitda)
    ratios['ebit_growth']     = _yoy(ebit)
    ratios['ni_growth']       = _yoy(ni)
    ratios['asset_growth']    = _yoy(total_assets)
    ratios['equity_growth']   = _yoy(total_equity)
    ratios['debt_growth']     = _yoy(total_debt)
    ratios['cfo_growth']      = _yoy(cfo)

    # ── Profitability margins ─────────────────────────────────────────────────
    ratios['gross_margin']    = safe_div(gp,     rev) * 100 if not gp.isna().all()  else np.nan
    ratios['ebitda_margin']   = safe_div(ebitda, rev) * 100 if not ebitda.isna().all() else np.nan
    ratios['ebit_margin']     = safe_div(ebit,   rev) * 100
    ratios['net_margin']      = safe_div(ni,     rev) * 100

    # ── Returns ───────────────────────────────────────────────────────────────
    avg_assets = (total_assets + total_assets.shift(1)) / 2
    avg_equity = (total_equity + total_equity.shift(1)) / 2
    ratios['roa'] = safe_div(ni, avg_assets) * 100
    ratios['roe'] = safe_div(ni, avg_equity) * 100

    # ── Liquidity ─────────────────────────────────────────────────────────────
    ratios['current_ratio'] = safe_div(curr_assets, curr_liab)
    ratios['quick_ratio']   = safe_div(curr_assets.fillna(0) - inventory.fillna(0), curr_liab)

    # ── Leverage ──────────────────────────────────────────────────────────────
    ratios['debt_to_equity']    = safe_div(total_debt, total_equity)
    ratios['debt_to_assets']    = safe_div(total_debt, total_assets)
    net_debt = total_debt.fillna(0) - cash.fillna(0)
    ratios['net_debt']          = net_debt
    ratios['net_debt_ebitda']   = safe_div(net_debt, ebitda)
    ratios['interest_coverage'] = safe_div(ebit, interest.abs())

    # ── Working capital ratios ────────────────────────────────────────────────
    avg_rec = (receivables + receivables.shift(1)) / 2
    avg_inv = (inventory   + inventory.shift(1))   / 2
    avg_pay = (payables    + payables.shift(1))    / 2
    cogs_for_wc = cogs.fillna(rev * 0.6)  # fallback estimate

    ratios['receivable_days'] = safe_div(avg_rec, rev)   * 365
    ratios['inventory_days']  = safe_div(avg_inv, cogs_for_wc) * 365
    ratios['payable_days']    = safe_div(avg_pay, cogs_for_wc) * 365
    ratios['cash_conversion'] = ratios['receivable_days'].fillna(0) + \
                                ratios['inventory_days'].fillna(0)  - \
                                ratios['payable_days'].fillna(0)

    # ── Capex & D&A ───────────────────────────────────────────────────────────
    ratios['capex_to_revenue']  = safe_div(capex.abs(), rev) * 100
    ratios['da_to_revenue']     = safe_div(da, rev) * 100
    ratios['capex_to_da']       = safe_div(capex.abs(), da)

    # ── Cash flow quality ─────────────────────────────────────────────────────
    ratios['cfo_to_ni']         = safe_div(cfo, ni)
    ratios['fcf']               = fcf
    ratios['fcf_margin']        = safe_div(fcf, rev) * 100
    ratios['cfo_margin']        = safe_div(cfo, rev) * 100

    # ── Tax rate ──────────────────────────────────────────────────────────────
    ratios['effective_tax_rate'] = safe_div(tax.abs(), pbt.abs()) * 100

    # ── Dividend payout (if available) ───────────────────────────────────────
    div = gets(cf_df, 'dividends_paid')
    if not div.isna().all():
        ratios['dividend_payout'] = safe_div(div.abs(), ni.abs()) * 100

    # ── CAGR summary ─────────────────────────────────────────────────────────
    fys_valid = [fy for fy in all_fys if not pd.isna(rev.get(fy, np.nan))]
    summary = {}

    if len(fys_valid) >= 2:
        fy_start, fy_end = fys_valid[0], fys_valid[-1]
        n = len(fys_valid) - 1
        metrics_for_cagr = {
            'revenue':     rev,
            'ebitda':      ebitda,
            'net_income':  ni,
            'total_assets': total_assets,
            'total_debt':  total_debt,
            'cfo':         cfo,
            'fcf':         fcf,
        }
        for name, series in metrics_for_cagr.items():
            s = series.get(fy_start, np.nan)
            e = series.get(fy_end,   np.nan)
            summary[f'{name}_cagr'] = cagr(s, e, n)

    # Average margins
    for col in ['gross_margin', 'ebitda_margin', 'ebit_margin', 'net_margin', 'effective_tax_rate']:
        if col in ratios.columns:
            summary[f'avg_{col}'] = ratios[col].mean(skipna=True)
            summary[f'recent_{col}'] = ratios[col].dropna().iloc[-1] if ratios[col].notna().any() else None

    # Average ratios
    for col in ['roe', 'roa', 'current_ratio', 'debt_to_equity', 'interest_coverage']:
        if col in ratios.columns:
            summary[f'avg_{col}'] = ratios[col].mean(skipna=True)

    return {
        'ratios_df': ratios,
        'summary':   summary,
        'errors':    errors,
    }
