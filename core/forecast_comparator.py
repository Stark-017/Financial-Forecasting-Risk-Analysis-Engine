# core/forecast_comparator.py
"""
Phase 7 — Forecast Comparison & Hybrid Blending Engine.

Compares:
  - Traditional Driver-Based Financial Forecast
  - Machine Learning Machine Forecast

Produces:
  - Variance analysis
  - Hybrid Blended Forecast (weighted combination)
  - Tabular comparison
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compare_and_blend_forecasts(driver_forecast: dict, ml_forecast: dict,
                                ml_weight: float = 0.40) -> dict:
    """
    Compare traditional driver-based forecast with ML forecast and generate a hybrid forecast.

    Args:
        driver_forecast: output from build_forecast() or run_scenarios()['base']
        ml_forecast:     output from run_ml_forecast()
        ml_weight:       weight given to ML forecast (0.0 to 1.0), default 0.40 (40% ML, 60% Driver)

    Returns:
        dict:
          'comparison_df': pd.DataFrame comparing Driver, ML, and Hybrid values
          'hybrid_values': dict of hybrid point estimates per metric
          'driver_weight': float
          'ml_weight':     float
    """
    driver_weight = 1.0 - ml_weight
    is_driver = driver_forecast.get('income_stmt', pd.DataFrame())
    ml_targets = ml_forecast.get('targets', {})
    forecast_years = driver_forecast.get('forecast_years', ['FY25'])

    rows = []
    hybrid_dict = {}

    metrics = [
        ('revenue', 'Revenue (Cr)'),
        ('ebitda',  'EBITDA (Cr)'),
        ('net_income', 'Net Income (Cr)'),
    ]

    for col, label in metrics:
        driver_val = float(is_driver.loc[forecast_years[0], col]) if (not is_driver.empty and forecast_years[0] in is_driver.index and col in is_driver.columns) else 0.0
        
        ml_res = ml_targets.get(col, {})
        ml_preds = ml_res.get('predictions', [0.0])
        ml_val = float(ml_preds[0]) if ml_preds else 0.0

        hybrid_val = (driver_weight * driver_val) + (ml_weight * ml_val)
        variance_cr = ml_val - driver_val
        variance_pct = (variance_cr / abs(driver_val) * 100) if abs(driver_val) > 0 else 0.0

        hybrid_dict[col] = hybrid_val

        rows.append({
            'Metric': label,
            'Driver Forecast': round(driver_val, 1),
            'ML Forecast': round(ml_val, 1),
            'Hybrid Blend': round(hybrid_val, 1),
            'Variance (Cr)': round(variance_cr, 1),
            'Variance (%)': round(variance_pct, 2),
            'ML Best Model': ml_res.get('best_model', 'N/A'),
        })

    comparison_df = pd.DataFrame(rows)

    return {
        'comparison_df': comparison_df,
        'hybrid_values': hybrid_dict,
        'driver_weight': driver_weight,
        'ml_weight': ml_weight,
    }
