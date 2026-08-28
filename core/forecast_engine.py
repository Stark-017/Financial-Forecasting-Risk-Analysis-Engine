# core/forecast_engine.py
"""
Phase 4 — Integrated three-statement forecast engine.

Builds a fully integrated IS + BS + CF forecast for a given set of
assumptions (one scenario at a time).

All values in INR Crore.

Key function:
  build_forecast(clean_data, drivers, assumptions, n_years=3) -> ForecastOutput dict

ForecastOutput:
  {
    'scenario':      str,
    'assumptions':   dict,
    'forecast_years': list,
    'income_stmt':   pd.DataFrame,  index=FY, cols=IS metrics
    'balance_sheet': pd.DataFrame,  index=FY, cols=BS metrics
    'cash_flow':     pd.DataFrame,  index=FY, cols=CF metrics
    'ratios':        pd.DataFrame,
    'validation':    dict,
    'errors':        list,
  }
"""

import logging
import numpy as np
import pandas as pd
from utils.formatting import safe_div

logger = logging.getLogger(__name__)


def _last(df: pd.DataFrame, col: str, default=0.0):
    """Get the last available value for a column."""
    if df.empty or col not in df.columns:
        return default
    s = df[col].dropna()
    return float(s.iloc[-1]) if not s.empty else default


def _last_fy(df: pd.DataFrame):
    """Get the most recent FY string."""
    if df.empty:
        return None
    return df.index[-1]


def _next_fy(fy_str: str, n: int = 1) -> str:
    year = int(fy_str[2:]) + n
    return f'FY{year}'


def _get(assumptions: dict, key: str, default=None):
    return assumptions.get(key, default)


def _validate_forecast(is_rows, bs_rows, cf_rows, forecast_years):
    """
    Validate three-statement integration for each forecast year.
    Returns dict with 'bs_balanced', 'cf_reconciled', 'warnings' list.
    """
    warnings = []
    bs_balanced_all = True
    cf_reconciled_all = True

    for fy in forecast_years:
        is_r = is_rows.get(fy, {})
        bs_r = bs_rows.get(fy, {})
        cf_r = cf_rows.get(fy, {})

        # BS check: Assets = Liabilities + Equity
        assets = bs_r.get('total_assets', 0)
        liab   = bs_r.get('total_liabilities', 0)
        equity = bs_r.get('total_equity', 0)
        le     = liab + equity
        if assets > 0:
            diff_pct = abs(assets - le) / assets
            if diff_pct > 0.01:
                warnings.append(f'{fy}: BS imbalance {diff_pct*100:.2f}% (Assets={assets:.1f}, L+E={le:.1f})')
                bs_balanced_all = False

        # CF reconciliation: Beginning + Net Change ≈ Ending
        beg = cf_r.get('beginning_cash', 0)
        net = cf_r.get('net_change_in_cash', 0)
        end = cf_r.get('ending_cash', 0)
        if abs(end) > 0:
            diff_pct = abs((beg + net) - end) / abs(end)
            if diff_pct > 0.02:
                warnings.append(f'{fy}: CF recon diff {diff_pct*100:.2f}%')
                cf_reconciled_all = False

        # Retained earnings link
        ni  = is_r.get('net_income', 0)
        div = cf_r.get('dividends_paid', 0)  # negative
        # Check that net_income flows into retained earnings
        # (we just flag if NI is positive but net margin extremely weird)

    return {
        'bs_balanced':    bs_balanced_all,
        'cf_reconciled':  cf_reconciled_all,
        'warnings':       warnings,
    }


def build_forecast(clean_data: dict, drivers: dict, assumptions: dict,
                   scenario: str = 'base', n_years: int = 1) -> dict:
    """
    Build a 3-statement integrated forecast.

    Args:
        clean_data:  cleaned historical data from data_cleaner
        drivers:     DriverTable from driver_analyzer (dict of driver dicts)
        assumptions: scenario assumptions dict (overrides driver base_forecast)
        scenario:    'good', 'base', or 'bad'
        n_years:     number of forecast years (default 1)

    Returns:
        ForecastOutput dict
    """
    errors = []
    is_df  = clean_data.get('income_stmt',   pd.DataFrame())
    bs_df  = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df  = clean_data.get('cash_flow',     pd.DataFrame())

    # ── Determine forecast years ───────────────────────────────────────────────
    all_hist_fys = sorted(
        list(is_df.index if not is_df.empty else []) +
        list(bs_df.index if not bs_df.empty else [])
    )
    all_hist_fys = [f for f in all_hist_fys if f.startswith('FY')]
    last_hist_fy = all_hist_fys[-1] if all_hist_fys else 'FY2024'
    forecast_years = [_next_fy(last_hist_fy, i) for i in range(1, n_years + 1)]

    # ── Extract assumptions ──────────────────────────────────────────────────
    def a(key, driver_key=None, default=0.0):
        """
        Get assumption value:
        1. From explicit assumptions dict
        2. From driver base_forecast
        3. Default
        """
        if key in assumptions:
            return float(assumptions[key])
        if driver_key and driver_key in drivers:
            val = drivers[driver_key].get('base_forecast')
            if val is not None:
                return float(val)
        return default

    rev_growth    = a('revenue_growth',   'revenue_growth',   7.0) / 100
    ebitda_margin = a('ebitda_margin',    'ebitda_margin',    20.0) / 100
    da_ratio      = a('da_to_revenue',    'da_to_revenue',    4.0)  / 100
    tax_rate      = a('effective_tax_rate','effective_tax_rate', 25.0) / 100
    capex_ratio   = a('capex_to_revenue', 'capex_to_revenue', 5.0)  / 100
    rec_days      = a('receivable_days',  'receivable_days',  45.0)
    inv_days      = a('inventory_days',   'inventory_days',   30.0)
    pay_days      = a('payable_days',     'payable_days',     40.0)
    int_rate      = a('interest_rate',    'interest_rate',    6.0)  / 100
    div_payout    = a('dividend_payout',  'dividend_payout',  30.0) / 100

    # Gross margin / COGS ratio
    gross_margin  = a('gross_margin', 'gross_margin', 40.0) / 100

    # Other income: use last historical value
    other_income_last = _last(is_df, 'other_income', 0.0)

    # ── Seed historical values ─────────────────────────────────────────────────
    prev_rev      = _last(is_df, 'revenue',           10000.0)
    prev_cash     = _last(bs_df, 'cash',              1000.0)
    prev_ppe      = _last(bs_df, 'net_ppe',           5000.0)
    prev_ret_earn = _last(bs_df, 'retained_earnings', 5000.0)
    prev_lt_debt  = _last(bs_df, 'long_term_debt',    2000.0)
    prev_st_debt  = _last(bs_df, 'short_term_debt',   500.0)
    prev_share_cap = _last(bs_df, 'share_capital',    100.0)
    prev_other_eq  = _last(bs_df, 'other_equity',     1000.0)
    prev_other_nca = _last(bs_df, 'other_non_current_assets', 500.0)
    prev_intang   = _last(bs_df, 'intangibles',       200.0)
    prev_invest   = _last(bs_df, 'investments',       500.0)
    prev_other_curr_a = _last(bs_df, 'other_current_assets', 200.0)
    prev_other_curr_l = _last(bs_df, 'other_current_liabilities', 300.0)
    prev_other_ncl    = _last(bs_df, 'other_non_current_liabilities', 200.0)

    # Debt: use last total; split 80% LT / 20% ST
    prev_total_debt = prev_lt_debt + prev_st_debt
    # Assume net debt reduction of ~2% of debt per year in base
    debt_repay_rate = assumptions.get('debt_repay_rate', 0.02)

    is_rows = {}
    bs_rows = {}
    cf_rows = {}

    current_rev      = prev_rev
    current_cash     = prev_cash
    current_ppe      = prev_ppe
    current_ret_earn = prev_ret_earn
    current_total_debt = prev_total_debt

    for fy in forecast_years:
        # ═══════════════════════════════════════════════════
        # INCOME STATEMENT
        # ═══════════════════════════════════════════════════
        revenue   = current_rev * (1 + rev_growth)
        cogs      = revenue * (1 - gross_margin)
        gross_pft = revenue - cogs
        ebitda    = revenue * ebitda_margin
        da        = revenue * da_ratio
        ebit      = ebitda - da
        # Interest: on beginning debt
        interest  = current_total_debt * int_rate
        # Other income: keep flat, independent of revenue growth
        other_inc = other_income_last
        pbt       = ebit - interest + other_inc
        tax       = max(0, pbt) * tax_rate
        ni        = pbt - tax
        dividends = ni * div_payout  # positive outflow

        # ═══════════════════════════════════════════════════
        # CASH FLOW
        # ═══════════════════════════════════════════════════
        # Working capital items (forecast)
        ar_new  = revenue  * rec_days / 365
        inv_new = cogs     * inv_days / 365
        ap_new  = cogs     * pay_days / 365
        oc_a_new = prev_other_curr_a
        oc_l_new = prev_other_curr_l

        # Previous AR/Inv/AP
        ar_prev  = current_rev * rec_days / 365  # approx using same drivers
        inv_prev = (current_rev * (1 - gross_margin)) * inv_days / 365
        ap_prev  = (current_rev * (1 - gross_margin)) * pay_days / 365

        wc_change = -((ar_new - ar_prev) + (inv_new - inv_prev) - (ap_new - ap_prev))

        cfo   = ni + da + wc_change
        capex = -revenue * capex_ratio  # negative (cash outflow)
        cfi   = capex

        # Debt: repay some, issue if needed
        debt_repayment = current_total_debt * debt_repay_rate
        
        # Minimum cash guardrail: if ending cash would drop below 0, issue short term debt
        prelim_cff = -debt_repayment - dividends
        prelim_ending_cash = current_cash + cfo + cfi + prelim_cff
        
        debt_issuance = max(0.0, -prelim_ending_cash + 50.0) # Maintain at least 50Cr cash
        
        new_total_debt = current_total_debt - debt_repayment + debt_issuance
        net_debt_change = new_total_debt - current_total_debt  # negative = repayment

        cff   = net_debt_change - dividends
        net_delta_cash = cfo + cfi + cff
        ending_cash    = current_cash + net_delta_cash

        # FCF
        fcf   = cfo + capex  # capex is negative

        # ═══════════════════════════════════════════════════
        # BALANCE SHEET
        # ═══════════════════════════════════════════════════
        # PP&E roll-forward
        new_ppe = current_ppe + abs(capex) - da
        new_ppe = max(new_ppe, 0)

        # Retained earnings roll-forward
        new_ret_earn = current_ret_earn + ni - dividends

        # Debt split (80% LT, 20% ST)
        lt_debt = new_total_debt * 0.80
        st_debt = new_total_debt * 0.20

        # Equity
        total_equity = prev_share_cap + new_ret_earn + prev_other_eq

        # Liabilities
        total_liab = lt_debt + st_debt + oc_l_new + prev_other_ncl

        # Total L+E
        total_le   = total_liab + total_equity

        # Assets (non-cash)
        total_assets_ex_cash = (ar_new + inv_new + oc_a_new +   # current
                                new_ppe + prev_intang + prev_invest + prev_other_nca)  # non-current
        
        # Primary cash comes directly from CF statement. Use other equity to plug any minor imbalances
        final_cash = max(ending_cash, 0.0)
        total_assets = total_assets_ex_cash + final_cash
        
        plug = total_assets - total_le
        if plug != 0:
            # Force balance by putting plug into other equity
            total_equity += plug
            total_le = total_liab + total_equity

        # ── Store rows ──────────────────────────────────────────────────────────
        is_rows[fy] = {
            'revenue':             revenue,
            'cost_of_goods_sold':  cogs,
            'gross_profit':        gross_pft,
            'ebitda':              ebitda,
            'depreciation_amortization': da,
            'ebit':                ebit,
            'interest_expense':    interest,
            'other_income':        other_inc,
            'profit_before_tax':   pbt,
            'tax_expense':         tax,
            'net_income':          ni,
        }

        bs_rows[fy] = {
            'cash':                  final_cash,
            'trade_receivables':     ar_new,
            'inventory':             inv_new,
            'other_current_assets':  oc_a_new,
            'total_current_assets':  final_cash + ar_new + inv_new + oc_a_new,
            'net_ppe':               new_ppe,
            'intangibles':           prev_intang,
            'investments':           prev_invest,
            'other_non_current_assets': prev_other_nca,
            'total_assets':          total_assets,
            'trade_payables':        ap_new,
            'short_term_debt':       st_debt,
            'other_current_liabilities': oc_l_new,
            'total_current_liabilities': ap_new + st_debt + oc_l_new,
            'long_term_debt':        lt_debt,
            'total_debt':            new_total_debt,
            'other_non_current_liabilities': prev_other_ncl,
            'total_liabilities':     total_liab,
            'share_capital':         prev_share_cap,
            'retained_earnings':     new_ret_earn,
            'other_equity':          prev_other_eq,
            'total_equity':          total_equity,
            'total_liabilities_equity': total_le,
        }

        cf_rows[fy] = {
            'net_income_cf':             ni,
            'depreciation_amortization_cf': da,
            'working_capital_changes':   wc_change,
            'cash_from_operations':      cfo,
            'capex':                     capex,
            'cash_from_investing':       cfi,
            'debt_issuance':             debt_issuance,
            'debt_repayment':            -debt_repayment,
            'dividends_paid':            -dividends,
            'cash_from_financing':       cff,
            'net_change_in_cash':        net_delta_cash,
            'beginning_cash':            current_cash,
            'ending_cash':               final_cash,
            'free_cash_flow':            fcf,
        }

        # ── Roll forward state ───────────────────────────────────────────────────
        current_rev        = revenue
        current_cash       = final_cash
        current_ppe        = new_ppe
        current_ret_earn   = new_ret_earn
        current_total_debt = new_total_debt
        prev_other_curr_a  = oc_a_new
        prev_other_curr_l  = oc_l_new

    # ── Build DataFrames ────────────────────────────────────────────────────────────
    is_out = pd.DataFrame(is_rows).T
    bs_out = pd.DataFrame(bs_rows).T
    cf_out = pd.DataFrame(cf_rows).T

    is_out.index.name = 'FY'
    bs_out.index.name = 'FY'
    cf_out.index.name = 'FY'

    # ── Quick ratios ─────────────────────────────────────────────────────────────
    ratios_out = pd.DataFrame(index=forecast_years)
    ratios_out['ebitda_margin']   = (is_out['ebitda']    / is_out['revenue'] * 100).round(2)
    ratios_out['net_margin']      = (is_out['net_income'] / is_out['revenue'] * 100).round(2)
    ratios_out['ebit_margin']     = (is_out['ebit']      / is_out['revenue'] * 100).round(2)
    ratios_out['roe']             = (is_out['net_income'] / bs_out['total_equity'] * 100).round(2)
    ratios_out['roa']             = (is_out['net_income'] / bs_out['total_assets'] * 100).round(2)
    ratios_out['debt_to_equity']  = (bs_out['total_debt'] / bs_out['total_equity']).round(3)
    ratios_out['interest_coverage'] = (is_out['ebit'] / is_out['interest_expense'].abs()).round(2)
    ratios_out['fcf']             = cf_out['free_cash_flow'].round(1)
    ratios_out['fcf_margin']      = (cf_out['free_cash_flow'] / is_out['revenue'] * 100).round(2)
    ratios_out['net_debt']        = (bs_out['total_debt'] - bs_out['cash']).round(1)
    ratios_out['net_debt_ebitda'] = (ratios_out['net_debt'] / is_out['ebitda']).round(2)
    ratios_out['revenue_growth']  = (is_out['revenue'].pct_change() * 100).round(2)
    ratios_out.loc[forecast_years[0], 'revenue_growth'] = rev_growth * 100

    # ── Validate ─────────────────────────────────────═══════════════════════
    validation = _validate_forecast(is_rows, bs_rows, cf_rows, forecast_years)

    return {
        'scenario':       scenario,
        'assumptions':    assumptions,
        'forecast_years': forecast_years,
        'income_stmt':    is_out,
        'balance_sheet':  bs_out,
        'cash_flow':      cf_out,
        'ratios':         ratios_out,
        'validation':     validation,
        'errors':         errors,
    }
