# utils/formatting.py
# Number formatting helpers for the dashboard

def crore(val, decimals=1):
    """Format a number as ₹ X Cr with appropriate suffix."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "N/A"
    if abs(val) >= 1_00_000:
        return f"₹{val / 1_00_000:.{decimals}f}L Cr"
    if abs(val) >= 1_000:
        return f"₹{val / 1_000:.{decimals}f}K Cr"
    return f"₹{val:,.{decimals}f} Cr"

def pct(val, decimals=1, sign=False):
    """Format a number as a percentage string."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "N/A"
    prefix = "+" if sign and val > 0 else ""
    return f"{prefix}{val:.{decimals}f}%"

def ratio(val, decimals=2, suffix="x"):
    """Format a ratio."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"

def delta_color(val):
    """Return 'normal', 'inverse' or 'off' for st.metric delta_color."""
    if val is None:
        return "off"
    try:
        return "normal" if float(val) >= 0 else "inverse"
    except (TypeError, ValueError):
        return "off"

def trend_arrow(trend: str) -> str:
    arrows = {
        "increasing": "↑",
        "stable":     "→",
        "declining":  "↓",
        "volatile":   "⇅",
    }
    return arrows.get(trend, "—")

def trend_color(trend: str) -> str:
    """Return hex colour for a trend direction."""
    colors = {
        "increasing": "#10b981",
        "stable":     "#f59e0b",
        "declining":  "#ef4444",
        "volatile":   "#8b5cf6",
    }
    return colors.get(trend, "#94a3b8")

def fy_label(fy: str) -> str:
    """'FY2024' → 'FY2024'  (identity; kept for future locale changes)."""
    return str(fy)

def safe_div(numerator, denominator):
    """Safe division supporting both scalar values and pandas Series/DataFrames. Returns np.nan on zero or invalid division."""
    import pandas as pd
    import numpy as np

    if isinstance(numerator, (pd.Series, pd.DataFrame)) or isinstance(denominator, (pd.Series, pd.DataFrame)):
        try:
            n = numerator.astype(float) if hasattr(numerator, 'astype') else numerator
            d = denominator.astype(float) if hasattr(denominator, 'astype') else denominator
            if hasattr(d, 'replace'):
                d = d.replace(0, np.nan)
            return n / d
        except Exception:
            return pd.Series(np.nan, index=getattr(numerator, 'index', None))

    try:
        n = float(numerator)
        d = float(denominator)
        if d == 0:
            return np.nan
        return n / d
    except (TypeError, ValueError):
        return np.nan

def cagr(start, end, years):
    """Compound Annual Growth Rate."""
    try:
        s, e, n = float(start), float(end), int(years)
        if s <= 0 or n <= 0:
            return None
        return ((e / s) ** (1 / n) - 1) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return None
