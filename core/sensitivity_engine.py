# core/sensitivity_engine.py
"""
Phase 8 — Sensitivity Analysis & Stress Testing Engine.

Provides:
  1. 1D Sensitivity Analysis (OVAT — One Variable At a Time)
  2. 2D Sensitivity Matrix (Two Drivers vs Target Metric, e.g., Growth vs Margin -> Net Income)
  3. Tornado Analysis (Ranks all drivers by impact magnitude on Net Income & FCF)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from core.forecast_engine import build_forecast

logger = logging.getLogger(__name__)


def run_1d_sensitivity(clean_data: dict, drivers: dict, base_assumptions: dict,
                       driver_key: str, step_pcts: List[float] = None) -> pd.DataFrame:
    """
    Run 1D sensitivity on a single driver across relative percentage variations.
    e.g., driver_key='revenue_growth', step_pcts=[-5, -2.5, 0, 2.5, 5]
    """
    if step_pcts is None:
        step_pcts = [-5.0, -2.5, -1.0, 0.0, 1.0, 2.5, 5.0]

    base_val = float(base_assumptions.get(driver_key, 7.0))
    rows = []

    for step in step_pcts:
        test_val = base_val + step
        test_assump = base_assumptions.copy()
        test_assump[driver_key] = test_val

        fo = build_forecast(clean_data, drivers, test_assump, scenario='sensitivity', n_years=1)
        is_df = fo.get('income_stmt', pd.DataFrame())
        cf_df = fo.get('cash_flow', pd.DataFrame())
        fy = fo.get('forecast_years', ['FY25'])[0]

        rev = float(is_df.loc[fy, 'revenue']) if not is_df.empty and 'revenue' in is_df.columns else 0.0
        ebitda = float(is_df.loc[fy, 'ebitda']) if not is_df.empty and 'ebitda' in is_df.columns else 0.0
        ni = float(is_df.loc[fy, 'net_income']) if not is_df.empty and 'net_income' in is_df.columns else 0.0
        fcf = float(cf_df.loc[fy, 'free_cash_flow']) if not cf_df.empty and 'free_cash_flow' in cf_df.columns else 0.0

        rows.append({
            'Change (pp)': step,
            'Driver Value': round(test_val, 2),
            'Revenue (Cr)': round(rev, 1),
            'EBITDA (Cr)': round(ebitda, 1),
            'Net Income (Cr)': round(ni, 1),
            'FCF (Cr)': round(fcf, 1),
        })

    return pd.DataFrame(rows)


def run_2d_sensitivity(clean_data: dict, drivers: dict, base_assumptions: dict,
                       driver_x: str = 'revenue_growth', steps_x: List[float] = None,
                       driver_y: str = 'ebitda_margin', steps_y: List[float] = None,
                       target_metric: str = 'net_income') -> pd.DataFrame:
    """
    Run 2D Sensitivity Matrix: driver_x on columns, driver_y on rows.
    Target metric: 'net_income', 'ebitda', 'revenue', or 'free_cash_flow'
    """
    if steps_x is None:
        steps_x = [-4.0, -2.0, 0.0, 2.0, 4.0]
    if steps_y is None:
        steps_y = [-3.0, -1.5, 0.0, 1.5, 3.0]

    base_x = float(base_assumptions.get(driver_x, 7.0))
    base_y = float(base_assumptions.get(driver_y, 20.0))

    matrix = {}

    for sy in steps_y:
        val_y = base_y + sy
        row_dict = {}
        for sx in steps_x:
            val_x = base_x + sx
            test_assump = base_assumptions.copy()
            test_assump[driver_x] = val_x
            test_assump[driver_y] = val_y

            fo = build_forecast(clean_data, drivers, test_assump, scenario='sensitivity', n_years=1)
            fy = fo.get('forecast_years', ['FY25'])[0]
            stmt = 'cash_flow' if target_metric == 'free_cash_flow' else 'income_stmt'
            df = fo.get(stmt, pd.DataFrame())

            val = float(df.loc[fy, target_metric]) if (not df.empty and target_metric in df.columns) else 0.0
            col_label = f"{driver_x.replace('_',' ').title()} {val_x:+.1f}%"
            row_dict[col_label] = round(val, 1)

        row_label = f"{driver_y.replace('_',' ').title()} {val_y:+.1f}%"
        matrix[row_label] = row_dict

    df_2d = pd.DataFrame(matrix).T
    return df_2d


def run_tornado_analysis(clean_data: dict, drivers: dict, base_assumptions: dict,
                         target_metric: str = 'net_income', delta_pct: float = 10.0) -> pd.DataFrame:
    """
    Run Tornado Analysis: Varies each driver by ±delta_pct relative to base,
    ranks drivers by impact magnitude on the target metric.
    """
    target_drivers = [
        ('revenue_growth',    'Revenue Growth (%)'),
        ('ebitda_margin',     'EBITDA Margin (%)'),
        ('effective_tax_rate','Effective Tax Rate (%)'),
        ('capex_to_revenue',  'Capex / Revenue (%)'),
        ('interest_rate',     'Interest Rate (%)'),
        ('receivable_days',   'Receivable Days'),
    ]

    # Compute base forecast target metric
    base_fo = build_forecast(clean_data, drivers, base_assumptions, scenario='base', n_years=1)
    fy = base_fo.get('forecast_years', ['FY25'])[0]
    stmt = 'cash_flow' if target_metric == 'free_cash_flow' else 'income_stmt'
    base_df = base_fo.get(stmt, pd.DataFrame())
    base_target = float(base_df.loc[fy, target_metric]) if (not base_df.empty and target_metric in base_df.columns) else 100.0

    rows = []

    for key, label in target_drivers:
        base_val = float(base_assumptions.get(key, 10.0))
        delta = abs(base_val * (delta_pct / 100.0)) if base_val != 0 else 1.0

        # High variation
        assump_high = base_assumptions.copy()
        assump_high[key] = base_val + delta
        fo_high = build_forecast(clean_data, drivers, assump_high, scenario='high', n_years=1)
        val_high = float(fo_high[stmt].loc[fy, target_metric]) if not fo_high[stmt].empty else base_target

        # Low variation
        assump_low = base_assumptions.copy()
        assump_low[key] = base_val - delta
        fo_low = build_forecast(clean_data, drivers, assump_low, scenario='low', n_years=1)
        val_low = float(fo_low[stmt].loc[fy, target_metric]) if not fo_low[stmt].empty else base_target

        impact_high = val_high - base_target
        impact_low = val_low - base_target
        total_swing = abs(val_high - val_low)

        rows.append({
            'Driver': label,
            'Base Value': round(base_val, 2),
            'Low Value': round(base_val - delta, 2),
            'High Value': round(base_val + delta, 2),
            'Low Target (Cr)': round(val_low, 1),
            'High Target (Cr)': round(val_high, 1),
            'Impact Low (Cr)': round(impact_low, 1),
            'Impact High (Cr)': round(impact_high, 1),
            'Total Swing (Cr)': round(total_swing, 1),
        })

    df_tornado = pd.DataFrame(rows).sort_values(by='Total Swing (Cr)', ascending=False)
    return df_tornado
