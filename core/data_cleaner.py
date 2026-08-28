# core/data_cleaner.py
"""
Phase 2 — Data cleaning, standardization, and FY mapping.

Transforms raw yfinance DataFrames into:
  - Standardised column names (snake_case)
  - INR Crore units
  - FY strings as index (FY2022, FY2023, ...)
  - Screener.in data merged where yfinance is missing
"""

import logging
from typing import Optional
from datetime import datetime

import pandas as pd
import numpy as np

from utils.constants import (
    INCOME_STMT_MAP, BALANCE_SHEET_MAP, CASH_FLOW_MAP,
    YFINANCE_UNIT, IS_COLUMNS, BS_COLUMNS, CF_COLUMNS,
)

logger = logging.getLogger(__name__)


def _date_to_fy(dt) -> str:
    """
    Convert a date to Indian Financial Year string.
    Indian FY ends March 31.
    e.g. 2024-03-31 -> 'FY2024'
         2024-12-31 -> 'FY2025'  (for Dec year-end companies)
    """
    try:
        d = pd.Timestamp(dt)
        # If month <= 3 (Jan, Feb, Mar): year is the FY year
        # If month > 3: FY year = year + 1
        if d.month <= 3:
            return f"FY{d.year}"
        else:
            return f"FY{d.year + 1}"
    except Exception:
        return str(dt)


def _standardize_df(raw_df: pd.DataFrame, field_map: dict, unit_divisor: float = 1.0) -> pd.DataFrame:
    """
    Transform a raw yfinance DataFrame:
      - Transpose: dates become index, metrics become columns
      - Map column names via field_map
      - Convert values to target unit (Crore)
      - Return with FY strings as index
    """
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    try:
        # yfinance: index=metric names, columns=dates  ->  transpose
        df = raw_df.T.copy()

        # Convert index (dates) to FY strings
        df.index = [_date_to_fy(d) for d in df.index]
        df.index.name = 'FY'

        # Sort ascending
        df = df.sort_index()

        # Rename columns using field_map
        rename = {col: field_map[col] for col in df.columns if col in field_map}
        df = df.rename(columns=rename)

        # For duplicate target names, keep first occurrence
        df = df.loc[:, ~df.columns.duplicated(keep='first')]

        # Convert to numeric and apply unit conversion
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if unit_divisor != 1.0:
                df[col] = df[col] * unit_divisor

        # Remove columns that are all NaN
        df = df.dropna(axis=1, how='all')

        return df

    except Exception as e:
        logger.error(f"Standardization error: {e}")
        return pd.DataFrame()


def _derive_missing(is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame):
    """Derive common metrics that may be missing from yfinance."""

    # ── Income Statement derivations ─────────────────────────────────────────
    if 'gross_profit' not in is_df.columns and 'revenue' in is_df.columns and 'cost_of_goods_sold' in is_df.columns:
        is_df['gross_profit'] = is_df['revenue'] - is_df['cost_of_goods_sold']

    if 'ebitda' not in is_df.columns and 'ebit' in is_df.columns and 'depreciation_amortization' in is_df.columns:
        is_df['ebitda'] = is_df['ebit'] + is_df['depreciation_amortization']

    if 'ebit' not in is_df.columns and 'ebitda' in is_df.columns and 'depreciation_amortization' in is_df.columns:
        is_df['ebit'] = is_df['ebitda'] - is_df['depreciation_amortization']

    if 'profit_before_tax' not in is_df.columns and 'ebit' in is_df.columns:
        interest = is_df.get('interest_expense', pd.Series(0, index=is_df.index))
        other    = is_df.get('other_income',     pd.Series(0, index=is_df.index))
        is_df['profit_before_tax'] = is_df['ebit'] - interest.fillna(0) + other.fillna(0)

    if 'net_income' not in is_df.columns and 'profit_before_tax' in is_df.columns and 'tax_expense' in is_df.columns:
        is_df['net_income'] = is_df['profit_before_tax'] - is_df['tax_expense'].fillna(0)

    # ── Balance Sheet derivations ─────────────────────────────────────────────
    if 'total_liabilities_equity' not in bs_df.columns:
        if 'total_liabilities' in bs_df.columns and 'total_equity' in bs_df.columns:
            bs_df['total_liabilities_equity'] = (
                bs_df['total_liabilities'].fillna(0) + bs_df['total_equity'].fillna(0)
            )
        elif 'total_assets' in bs_df.columns:
            bs_df['total_liabilities_equity'] = bs_df['total_assets']

    if 'total_debt' not in bs_df.columns:
        st = bs_df.get('short_term_debt', pd.Series(0, index=bs_df.index)).fillna(0)
        lt = bs_df.get('long_term_debt',  pd.Series(0, index=bs_df.index)).fillna(0)
        bs_df['total_debt'] = st + lt

    # ── Cash Flow derivations ─────────────────────────────────────────────────
    if 'free_cash_flow' not in cf_df.columns:
        if 'cash_from_operations' in cf_df.columns and 'capex' in cf_df.columns:
            cf_df['free_cash_flow'] = (
                cf_df['cash_from_operations'].fillna(0) + cf_df['capex'].fillna(0)
            )  # capex is negative in yfinance

    if 'net_change_in_cash' not in cf_df.columns:
        cols = ['cash_from_operations', 'cash_from_investing', 'cash_from_financing']
        available = [c for c in cols if c in cf_df.columns]
        if available:
            cf_df['net_change_in_cash'] = cf_df[available].fillna(0).sum(axis=1)

    return is_df, bs_df, cf_df


def _merge_screener(is_df: pd.DataFrame, screener_data: dict) -> pd.DataFrame:
    """
    Attempt to merge Screener.in P&L data to fill missing years.
    Screener.in columns are year strings like 'Mar 2020'.
    """
    if screener_data is None or screener_data.get('profit_loss') is None:
        return is_df

    try:
        sc = screener_data['profit_loss'].copy()
        # Map Screener year strings like 'Mar 2020' -> 'FY2020'
        new_index = []
        for col in sc.columns:
            col_str = str(col)
            if 'Mar' in col_str or 'mar' in col_str:
                year_part = ''.join(filter(str.isdigit, col_str))
                if len(year_part) == 4:
                    new_index.append(f"FY{year_part}")
                else:
                    new_index.append(col_str)
            else:
                new_index.append(col_str)
        sc.columns = new_index

        # Only add FY years not already in is_df
        missing_fys = [fy for fy in sc.columns if fy not in is_df.index and fy.startswith('FY')]
        if not missing_fys:
            return is_df

        # Build a row for each missing year with Screener revenue
        for fy in missing_fys:
            if fy in sc.columns:
                row = {}
                col_data = sc[fy]
                # Screener.in rows: look for 'Sales', 'Revenue', 'Net Profit'
                for idx, val in col_data.items():
                    idx_lower = str(idx).lower()
                    if any(k in idx_lower for k in ['sales', 'revenue', 'net revenue']):
                        try:
                            row['revenue'] = float(str(val).replace(',', ''))
                        except Exception:
                            pass
                    elif 'net profit' in idx_lower or 'pat' in idx_lower:
                        try:
                            row['net_income'] = float(str(val).replace(',', ''))
                        except Exception:
                            pass
                if row:
                    is_df.loc[fy] = row

        is_df = is_df.sort_index()
    except Exception as e:
        logger.warning(f"Screener merge error: {e}")

    return is_df


def _compute_completeness(is_df, bs_df, cf_df) -> float:
    """Compute data completeness as % of key metrics present."""
    key_metrics = [
        ('is', 'revenue'), ('is', 'ebitda'), ('is', 'net_income'),
        ('bs', 'total_assets'), ('bs', 'total_equity'), ('bs', 'total_debt'),
        ('cf', 'cash_from_operations'), ('cf', 'capex'),
    ]
    present = 0
    for stmt, metric in key_metrics:
        df = {'is': is_df, 'bs': bs_df, 'cf': cf_df}.get(stmt, pd.DataFrame())
        if not df.empty and metric in df.columns and df[metric].notna().any():
            present += 1
    return round(present / len(key_metrics) * 100, 1)


def clean_financial_data(raw_data: dict, company_info: dict) -> dict:
    """
    Master cleaning function.

    Args:
        raw_data:     output of data_fetcher.fetch_all_financials()
        company_info: output of company_lookup.get_company_info()

    Returns:
        dict with 'income_stmt', 'balance_sheet', 'cash_flow' DataFrames + metadata
    """
    errors = list(raw_data.get('errors', []))

    # ── Standardise each statement ────────────────────────────────────────────
    is_df = _standardize_df(raw_data.get('income_stmt'),  INCOME_STMT_MAP,  YFINANCE_UNIT)
    bs_df = _standardize_df(raw_data.get('balance_sheet'), BALANCE_SHEET_MAP, YFINANCE_UNIT)
    cf_df = _standardize_df(raw_data.get('cash_flow'),    CASH_FLOW_MAP,    YFINANCE_UNIT)

    # ── Merge Screener supplementary data ────────────────────────────────────
    screener = raw_data.get('screener_data')
    if screener and not is_df.empty:
        is_df = _merge_screener(is_df, screener)

    # ── Derive missing metrics ────────────────────────────────────────────────
    if not is_df.empty and not bs_df.empty and not cf_df.empty:
        is_df, bs_df, cf_df = _derive_missing(is_df, bs_df, cf_df)
    elif not is_df.empty:
        is_df, _, _ = _derive_missing(is_df, pd.DataFrame(), pd.DataFrame())

    # ── Get financial years ───────────────────────────────────────────────────
    all_fys = sorted(set(
        list(is_df.index if not is_df.empty else []) +
        list(bs_df.index if not bs_df.empty else []) +
        list(cf_df.index if not cf_df.empty else [])
    ))
    # Keep only valid FY strings
    all_fys = [fy for fy in all_fys if fy.startswith('FY') and len(fy) == 6]

    if len(all_fys) == 0:
        errors.append("No valid financial years found in data")

    completeness = _compute_completeness(is_df, bs_df, cf_df)

    metadata = {
        'company':           company_info.get('company_name', 'Unknown'),
        'nse_symbol':        company_info.get('nse_symbol', ''),
        'ticker_symbol':     raw_data.get('ticker_symbol', ''),
        'source':            raw_data.get('source', 'yfinance'),
        'source_url':        raw_data.get('source_url', ''),
        'statement_type':    'consolidated',  # yfinance default
        'financial_years':   all_fys,
        'n_years':           len(all_fys),
        'unit':              'Crore',
        'currency':          'INR',
        'retrieval_date':    raw_data.get('retrieval_date', ''),
        'data_completeness': completeness,
    }

    return {
        'income_stmt':   is_df,
        'balance_sheet': bs_df,
        'cash_flow':     cf_df,
        'metadata':      metadata,
        'errors':        errors,
    }
