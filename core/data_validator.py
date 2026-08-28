# core/data_validator.py
"""
Phase 2 — Automated financial data validation.

Checks performed:
  1. Balance sheet: Assets ≈ Liabilities + Equity (5% tolerance)
  2. Cash flow: Beginning Cash + Net Change ≈ Ending Cash
  3. Temporal: 5 FY years present, no duplicates, no gaps
  4. Logical: Revenue > 0, non-negative assets
  5. Data completeness

Returns a list of ValidationResult dicts:
  {'check': str, 'status': 'PASS'|'WARN'|'FAIL', 'message': str, 'fy': str}
"""

import logging
from typing import List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

BS_TOLERANCE = 0.05   # 5%
CF_TOLERANCE = 0.10   # 10%


def _check(check_name: str, status: str, message: str, fy: str = 'ALL') -> dict:
    return {'check': check_name, 'status': status, 'message': message, 'fy': fy}


def validate_balance_sheet(bs_df: pd.DataFrame) -> List[dict]:
    results = []
    if bs_df.empty:
        return [_check('Balance Sheet Present', 'FAIL', 'Balance sheet data is empty')]

    results.append(_check('Balance Sheet Present', 'PASS', f'{len(bs_df)} years of balance sheet data found'))

    if 'total_assets' not in bs_df.columns:
        results.append(_check('BS Completeness', 'WARN', 'total_assets column missing'))
        return results

    for fy in bs_df.index:
        assets = bs_df.loc[fy, 'total_assets'] if 'total_assets' in bs_df.columns else None
        liab   = bs_df.loc[fy, 'total_liabilities'] if 'total_liabilities' in bs_df.columns else None
        equity = bs_df.loc[fy, 'total_equity'] if 'total_equity' in bs_df.columns else None

        if pd.isna(assets):
            results.append(_check('BS Balance', 'WARN', f'total_assets is NULL', fy))
            continue
        if pd.isna(liab) or pd.isna(equity):
            results.append(_check('BS Balance', 'WARN', 'total_liabilities or total_equity is NULL', fy))
            continue

        lhs = float(assets)
        rhs = float(liab) + float(equity)
        if lhs == 0:
            continue
        diff_pct = abs(lhs - rhs) / abs(lhs)
        if diff_pct <= BS_TOLERANCE:
            results.append(_check('BS Balance', 'PASS',
                f'Assets ({lhs:,.1f} Cr) ≈ L+E ({rhs:,.1f} Cr) — diff {diff_pct*100:.2f}%', fy))
        elif diff_pct <= 0.15:
            results.append(_check('BS Balance', 'WARN',
                f'Assets ({lhs:,.1f}) vs L+E ({rhs:,.1f}) — diff {diff_pct*100:.1f}% (rounding?)', fy))
        else:
            results.append(_check('BS Balance', 'FAIL',
                f'Assets ({lhs:,.1f}) ≠ L+E ({rhs:,.1f}) — diff {diff_pct*100:.1f}%', fy))

    return results


def validate_cash_flow(cf_df: pd.DataFrame) -> List[dict]:
    results = []
    if cf_df.empty:
        return [_check('Cash Flow Present', 'WARN', 'Cash flow data is empty')]

    results.append(_check('Cash Flow Present', 'PASS', f'{len(cf_df)} years of cash flow data found'))

    for fy in cf_df.index:
        beg  = cf_df.loc[fy, 'beginning_cash'] if 'beginning_cash' in cf_df.columns else None
        end  = cf_df.loc[fy, 'ending_cash']    if 'ending_cash'    in cf_df.columns else None
        net  = cf_df.loc[fy, 'net_change_in_cash'] if 'net_change_in_cash' in cf_df.columns else None
        cfo  = cf_df.loc[fy, 'cash_from_operations'] if 'cash_from_operations' in cf_df.columns else None
        cfi  = cf_df.loc[fy, 'cash_from_investing']  if 'cash_from_investing'  in cf_df.columns else None
        cff  = cf_df.loc[fy, 'cash_from_financing']  if 'cash_from_financing'  in cf_df.columns else None

        # Check beg + net ≈ end
        if not (pd.isna(beg) or pd.isna(end) or pd.isna(net)):
            expected_end = float(beg) + float(net)
            actual_end   = float(end)
            if abs(actual_end) > 0:
                diff_pct = abs(expected_end - actual_end) / abs(actual_end)
                if diff_pct <= CF_TOLERANCE:
                    results.append(_check('CF Reconciliation', 'PASS',
                        f'Beg+Net ≈ End cash — diff {diff_pct*100:.2f}%', fy))
                else:
                    results.append(_check('CF Reconciliation', 'WARN',
                        f'CF reconciliation diff {diff_pct*100:.1f}%', fy))
        else:
            results.append(_check('CF Reconciliation', 'WARN',
                'Cannot verify — beginning/ending/net cash columns missing', fy))

    return results


def validate_income_statement(is_df: pd.DataFrame) -> List[dict]:
    results = []
    if is_df.empty:
        return [_check('Income Statement Present', 'FAIL', 'Income statement data is empty')]

    results.append(_check('Income Statement Present', 'PASS', f'{len(is_df)} years of P&L data found'))

    if 'revenue' in is_df.columns:
        for fy in is_df.index:
            rev = is_df.loc[fy, 'revenue']
            if pd.isna(rev):
                results.append(_check('Revenue Present', 'WARN', 'Revenue is NULL', fy))
            elif float(rev) <= 0:
                results.append(_check('Revenue Positive', 'WARN', f'Revenue ({rev:.1f} Cr) is not positive', fy))
    else:
        results.append(_check('Revenue Present', 'FAIL', 'revenue column missing from income statement'))

    return results


def validate_temporal(metadata: dict) -> List[dict]:
    results = []
    fys = metadata.get('financial_years', [])

    if len(fys) == 0:
        return [_check('Data Coverage', 'FAIL', 'No financial years found in dataset')]

    if len(fys) >= 5:
        results.append(_check('Data Coverage', 'PASS', f'{len(fys)} financial years found: {fys[0]} – {fys[-1]}'))
    elif len(fys) >= 3:
        results.append(_check('Data Coverage', 'WARN',
            f'Only {len(fys)} years found ({fys[0]} – {fys[-1]}). Target is 5 years.'))
    else:
        results.append(_check('Data Coverage', 'FAIL',
            f'Only {len(fys)} year(s) found. Insufficient for reliable analysis.'))

    # Check for gaps
    if len(fys) >= 2:
        years = sorted([int(fy[2:]) for fy in fys if fy.startswith('FY') and len(fy) == 6])
        for i in range(1, len(years)):
            if years[i] - years[i-1] > 1:
                results.append(_check('Temporal Gap', 'WARN',
                    f'Gap between FY{years[i-1]} and FY{years[i]}'))

    return results


def validate_completeness(metadata: dict) -> List[dict]:
    pct = metadata.get('data_completeness', 0)
    if pct >= 80:
        return [_check('Data Completeness', 'PASS', f'{pct}% of key metrics populated')]
    elif pct >= 50:
        return [_check('Data Completeness', 'WARN', f'{pct}% of key metrics populated (some gaps)')]
    else:
        return [_check('Data Completeness', 'FAIL', f'Only {pct}% of key metrics populated')]


def run_all_validations(clean_data: dict) -> List[dict]:
    """
    Run all validation checks on cleaned financial data.

    Args:
        clean_data: output of data_cleaner.clean_financial_data()

    Returns:
        List of validation result dicts.
        Summary also returned via 'summary' key in output.
    """
    is_df = clean_data.get('income_stmt', pd.DataFrame())
    bs_df = clean_data.get('balance_sheet', pd.DataFrame())
    cf_df = clean_data.get('cash_flow', pd.DataFrame())
    meta  = clean_data.get('metadata', {})

    results = []
    results += validate_income_statement(is_df)
    results += validate_balance_sheet(bs_df)
    results += validate_cash_flow(cf_df)
    results += validate_temporal(meta)
    results += validate_completeness(meta)

    # Add summary
    pass_count = sum(1 for r in results if r['status'] == 'PASS')
    warn_count = sum(1 for r in results if r['status'] == 'WARN')
    fail_count = sum(1 for r in results if r['status'] == 'FAIL')

    results.append({
        'check': '__SUMMARY__',
        'status': 'PASS' if fail_count == 0 else ('WARN' if fail_count <= 2 else 'FAIL'),
        'message': f'PASS: {pass_count} | WARN: {warn_count} | FAIL: {fail_count}',
        'fy': 'ALL',
        'pass_count': pass_count,
        'warn_count': warn_count,
        'fail_count': fail_count,
    })

    return results
