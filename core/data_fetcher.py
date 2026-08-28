# core/data_fetcher.py
"""
Phase 2 — Raw financial data retrieval.

Sources (fallback chain):
  1. yfinance (.NS ticker)  — primary
  2. yfinance (.BO ticker)  — fallback
  3. Screener.in scraper    — supplementary for older years
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "storage" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_yfinance(ticker_symbol: str) -> dict:
    """Fetch all financial statements from yfinance."""
    result = {
        'income_stmt': None,
        'balance_sheet': None,
        'cash_flow': None,
        'info': {},
        'source': 'yfinance',
        'ticker_symbol': ticker_symbol,
        'error': None,
    }
    try:
        ticker = yf.Ticker(ticker_symbol)

        # Fetch statements
        result['income_stmt']  = ticker.income_stmt
        result['balance_sheet'] = ticker.balance_sheet
        result['cash_flow']    = ticker.cashflow
        result['info']         = ticker.info or {}

        # Check if we actually got data
        if result['income_stmt'] is None or result['income_stmt'].empty:
            result['error'] = f"No income statement data for {ticker_symbol}"

    except Exception as e:
        result['error'] = str(e)
        logger.warning(f"yfinance fetch failed for {ticker_symbol}: {e}")

    return result


def _scrape_screener(symbol: str) -> dict:
    """
    Supplementary: scrape Screener.in for consolidated financial data.
    Returns dict with 'profit_loss', 'balance_sheet', 'cash_flow' DataFrames.
    Each DataFrame: index=year strings, columns=metric labels.
    """
    result = {'profit_loss': None, 'balance_sheet': None, 'cash_flow': None, 'error': None}

    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        time.sleep(1.5)  # polite delay
        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 404:
            # Try standalone
            url = f"https://www.screener.in/company/{symbol}/"
            resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code != 200:
            result['error'] = f"Screener.in returned {resp.status_code}"
            return result

        soup = BeautifulSoup(resp.text, 'lxml')

        def parse_table(section_id: str) -> Optional[pd.DataFrame]:
            section = soup.find('section', id=section_id)
            if not section:
                return None
            table = section.find('table')
            if not table:
                return None
            try:
                # Get year headers
                headers_row = table.find('thead')
                if not headers_row:
                    return None
                years = [th.get_text(strip=True)
                         for th in headers_row.find_all('th')][1:]  # skip first col

                rows = {}
                for tr in table.find('tbody').find_all('tr'):
                    cols = tr.find_all('td')
                    if not cols:
                        continue
                    metric = cols[0].get_text(strip=True)
                    values = []
                    for td in cols[1:]:
                        txt = td.get_text(strip=True).replace(',', '').replace('+', '')
                        try:
                            values.append(float(txt))
                        except ValueError:
                            values.append(None)
                    rows[metric] = values

                df = pd.DataFrame(rows, index=years).T
                return df
            except Exception as e:
                logger.warning(f"Screener.in table parse error ({section_id}): {e}")
                return None

        result['profit_loss']   = parse_table('profit-loss')
        result['balance_sheet'] = parse_table('balance-sheet')
        result['cash_flow']     = parse_table('cash-flow')
        result['source_url']    = url

    except Exception as e:
        result['error'] = str(e)
        logger.warning(f"Screener.in scrape failed for {symbol}: {e}")

    return result


def _save_raw(company_name: str, data: dict, tag: str = ''):
    safe = company_name.replace(' ', '_').replace('/', '_')[:25]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = RAW_DIR / f"{safe}_{tag}_{ts}.json"
    try:
        with open(fname, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not save raw JSON: {e}")


def fetch_all_financials(company_info: dict) -> dict:
    """
    Master fetch function.

    Args:
        company_info: dict from company_lookup.get_company_info()

    Returns:
        dict with keys:
          'income_stmt', 'balance_sheet', 'cash_flow' -> pd.DataFrame
          'info'            -> dict (yfinance metadata)
          'screener_data'   -> dict (screener supplementary, may be None)
          'source'          -> str
          'ticker_symbol'   -> str
          'retrieval_date'  -> str
          'errors'          -> list[str]
    """
    errors = []
    ticker_symbol = company_info.get('ticker_symbol', '')
    company_name  = company_info.get('company_name', 'Unknown')
    symbol        = company_info.get('nse_symbol') or company_info.get('bse_code', '')

    # ── Step 1: yfinance primary ──────────────────────────────────────────────
    yf_data = _fetch_yfinance(ticker_symbol)
    if yf_data['error']:
        errors.append(f"yfinance ({ticker_symbol}): {yf_data['error']}")

        # Try alternate exchange
        alt_sym = ticker_symbol.replace('.NS', '.BO') if '.NS' in ticker_symbol \
                  else ticker_symbol.replace('.BO', '.NS')
        yf_data = _fetch_yfinance(alt_sym)
        if yf_data['error']:
            errors.append(f"yfinance ({alt_sym}): {yf_data['error']}")

    income_stmt   = yf_data.get('income_stmt')
    balance_sheet = yf_data.get('balance_sheet')
    cash_flow     = yf_data.get('cash_flow')

    # ── Step 2: Count years available ────────────────────────────────────────
    n_years = 0
    if income_stmt is not None and not income_stmt.empty:
        n_years = income_stmt.shape[1]  # cols = dates

    # ── Step 3: Screener.in supplementary if < 5 years ───────────────────────
    screener_data = None
    if n_years < 5 and symbol:
        logger.info(f"Only {n_years} years from yfinance — trying Screener.in for {symbol}")
        screener_data = _scrape_screener(symbol)
        if screener_data.get('error'):
            errors.append(f"Screener.in: {screener_data['error']}")

    # ── Save raw data ─────────────────────────────────────────────────────────
    _save_raw(company_name, {
        'ticker': ticker_symbol,
        'yf_info': yf_data.get('info', {}),
        'n_years': n_years,
    }, tag='meta')

    source = 'yfinance'
    if screener_data and not screener_data.get('error'):
        source = 'yfinance + screener.in'

    return {
        'income_stmt':   income_stmt,
        'balance_sheet': balance_sheet,
        'cash_flow':     cash_flow,
        'info':          yf_data.get('info', {}),
        'screener_data': screener_data,
        'source':        source,
        'source_url':    f"https://finance.yahoo.com/quote/{ticker_symbol}",
        'ticker_symbol': yf_data.get('ticker_symbol', ticker_symbol),
        'retrieval_date': datetime.now().isoformat(),
        'errors':        errors,
    }
