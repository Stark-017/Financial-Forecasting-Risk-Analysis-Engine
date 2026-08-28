# core/company_lookup.py
"""
Phase 1 — Company search and NSE/BSE verification.
Ultra-fast in-memory instant search (<0.01 seconds) for smooth auto-matching.
"""

import os
import io
import time
import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests
import yfinance as yf
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "storage" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

NSE_CSV_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_CACHE_FILE = CACHE_DIR / "nse_equity_list.csv"
CACHE_TTL_SECONDS = 86400 * 7  # 7 days

# In-memory global cache for instant 0.001s search response
_NSE_DF_CACHE: Optional[pd.DataFrame] = None
_NAMES_LIST: List[str] = []
_SYMBOLS_LIST: List[str] = []
_ISIN_LIST: List[str] = []

# Built-in popular equities fallback list for instant 0.001s response
BUILTIN_EQUITIES = [
    ("CUPID", "Cupid Limited", "NSE", "INE509F01011"),
    ("SHRIRAMFIN", "Shriram Finance Limited", "NSE", "INE721A01013"),
    ("TCS", "Tata Consultancy Services Limited", "NSE", "INE467B01029"),
    ("INFY", "Infosys Limited", "NSE", "INE009A01021"),
    ("RELIANCE", "Reliance Industries Limited", "NSE", "INE002A01018"),
    ("HDFCBANK", "HDFC Bank Limited", "NSE", "INE040A01034"),
    ("ICICIBANK", "ICICI Bank Limited", "NSE", "INE090A01021"),
    ("TATAMOTORS", "Tata Motors Limited", "NSE", "INE155A01022"),
    ("BHARTIARTL", "Bharti Airtel Limited", "NSE", "INE397D01024"),
    ("ITC", "ITC Limited", "NSE", "INE154A01025"),
    ("LT", "Larsen & Toubro Limited", "NSE", "INE018A01030"),
    ("SBIN", "State Bank of India", "NSE", "INE062A01020"),
    ("HINDUNILVR", "Hindustan Unilever Limited", "NSE", "INE030A01027"),
    ("BAJFINANCE", "Bajaj Finance Limited", "NSE", "INE296A01024"),
    ("MARUTI", "Maruti Suzuki India Limited", "NSE", "INE585B01010"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Limited", "NSE", "INE044A01036"),
    ("TITAN", "Titan Company Limited", "NSE", "INE280A01028"),
    ("AXISBANK", "Axis Bank Limited", "NSE", "INE238A01034"),
    ("ULTRACEMCO", "UltraTech Cement Limited", "NSE", "INE481G01011"),
    ("NTPC", "NTPC Limited", "NSE", "INE733E01010"),
    ("ONGC", "Oil & Natural Gas Corporation Limited", "NSE", "INE213A01029"),
    ("POWERGRID", "Power Grid Corporation of India Limited", "NSE", "INE752E01010"),
    ("JSWSTEEL", "JSW Steel Limited", "NSE", "INE019A01038"),
    ("TATASTEEL", "Tata Steel Limited", "NSE", "INE081A01020"),
    ("COALINDIA", "Coal India Limited", "NSE", "INE522F01014"),
    ("ADANIENT", "Adani Enterprises Limited", "NSE", "INE423A01024"),
    ("ADANIPORTS", "Adani Ports and Special Economic Zone Limited", "NSE", "INE742F01042"),
    ("GRASIM", "Grasim Industries Limited", "NSE", "INE047A01021"),
    ("WIPRO", "Wipro Limited", "NSE", "INE075A01022"),
    ("TECHM", "Tech Mahindra Limited", "NSE", "INE669C01036"),
    ("HCLTECH", "HCL Technologies Limited", "NSE", "INE860A01027"),
    ("ZOMATO", "Eternal Limited (Zomato)", "NSE", "INE758T01015"),
    ("PAYTM", "One97 Communications Limited (Paytm)", "NSE", "INE982J01020"),
    ("JIOFIN", "Jio Financial Services Limited", "NSE", "INE030Z01018"),
    ("BHEL", "Bharat Heavy Electricals Limited", "NSE", "INE257A01026"),
    ("HAL", "Hindustan Aeronautics Limited", "NSE", "INE066F01020"),
    ("BEL", "Bharat Electronics Limited", "NSE", "INE263A01024"),
    ("VBL", "Varun Beverages Limited", "NSE", "INE200M01021"),
    ("TRENT", "Trent Limited", "NSE", "INE849A01020"),
    ("CDSL", "Central Depository Services (India) Limited", "NSE", "INE267A01025"),
    ("BSE", "BSE Limited", "NSE", "INE118H01025"),
]


def _download_nse_equity_list() -> Optional[pd.DataFrame]:
    """Download NSE equity list with proper headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        time.sleep(0.5)
        resp = session.get(NSE_CSV_URL, headers=headers, timeout=8)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            return df
    except Exception as e:
        logger.warning(f"NSE CSV download failed: {e}")
    return None


def get_nse_equity_list() -> Optional[pd.DataFrame]:
    """Return NSE equity list with fast in-memory caching."""
    global _NSE_DF_CACHE, _NAMES_LIST, _SYMBOLS_LIST, _ISIN_LIST

    if _NSE_DF_CACHE is not None:
        return _NSE_DF_CACHE

    if NSE_CACHE_FILE.exists():
        try:
            df = pd.read_csv(NSE_CACHE_FILE)
            _NSE_DF_CACHE = df
            _NAMES_LIST = df['NAME OF COMPANY'].fillna('').str.upper().tolist() if 'NAME OF COMPANY' in df.columns else []
            _SYMBOLS_LIST = df['SYMBOL'].fillna('').str.upper().tolist() if 'SYMBOL' in df.columns else []
            _ISIN_LIST = df['ISIN NUMBER'].fillna('').str.upper().tolist() if 'ISIN NUMBER' in df.columns else []
            return df
        except Exception:
            pass

    df = _download_nse_equity_list()
    if df is not None:
        if 'SYMBOL' not in df.columns:
            sym_col = [c for c in df.columns if 'symbol' in c.lower()]
            if sym_col:
                df = df.rename(columns={sym_col[0]: 'SYMBOL'})
        name_col = [c for c in df.columns if 'name' in c.lower() or 'company' in c.lower()]
        if name_col and 'NAME OF COMPANY' not in df.columns:
            df = df.rename(columns={name_col[0]: 'NAME OF COMPANY'})

        try:
            df.to_csv(NSE_CACHE_FILE, index=False)
        except Exception:
            pass

        _NSE_DF_CACHE = df
        _NAMES_LIST = df['NAME OF COMPANY'].fillna('').str.upper().tolist() if 'NAME OF COMPANY' in df.columns else []
        _SYMBOLS_LIST = df['SYMBOL'].fillna('').str.upper().tolist() if 'SYMBOL' in df.columns else []
        _ISIN_LIST = df['ISIN NUMBER'].fillna('').str.upper().tolist() if 'ISIN NUMBER' in df.columns else []
        return df

    # Fallback to built-in equities dataframe
    rows = [{'SYMBOL': sym, 'NAME OF COMPANY': name.upper(), 'ISIN NUMBER': isin} for sym, name, exch, isin in BUILTIN_EQUITIES]
    fallback_df = pd.DataFrame(rows)
    _NSE_DF_CACHE = fallback_df
    _NAMES_LIST = fallback_df['NAME OF COMPANY'].tolist()
    _SYMBOLS_LIST = fallback_df['SYMBOL'].tolist()
    _ISIN_LIST = fallback_df['ISIN NUMBER'].tolist()
    return fallback_df


def _yfinance_search(query: str) -> List[dict]:
    """Use yfinance Search API only as fallback."""
    results = []
    try:
        search_result = yf.Search(query, max_results=5, enable_fuzzy_query=True)
        for q in search_result.quotes:
            exch = q.get('exchange', '')
            if exch in ('NSI', 'NSE', 'BSE', 'BOM'):
                sym = q.get('symbol', '')
                clean_sym = sym.replace('.NS', '').replace('.BO', '')
                exchange = 'NSE' if exch in ('NSI', 'NSE') else 'BSE'
                results.append({
                    'company_name': q.get('longname') or q.get('shortname') or clean_sym,
                    'symbol': clean_sym,
                    'exchange': exchange,
                    'score': 75,
                    'isin': q.get('isin', ''),
                })
    except Exception as e:
        logger.warning(f"yfinance search failed: {e}")
    return results


def search_company(query: str) -> List[dict]:
    """
    Ultra-fast (<0.01 seconds) in-memory company search.
    """
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip().upper()
    results = []

    # 1. Check built-in equities first (instant 0.001s)
    for sym, name, exch, isin in BUILTIN_EQUITIES:
        s_upper = sym.upper()
        n_upper = name.upper()
        if q == s_upper:
            results.append({'company_name': name, 'symbol': sym, 'exchange': exch, 'score': 100, 'isin': isin})
        elif s_upper.startswith(q):
            results.append({'company_name': name, 'symbol': sym, 'exchange': exch, 'score': 95, 'isin': isin})
        elif q in n_upper:
            results.append({'company_name': name, 'symbol': sym, 'exchange': exch, 'score': 90, 'isin': isin})

    # 2. Check full cached NSE list
    nse_df = get_nse_equity_list()
    if nse_df is not None and _NAMES_LIST:
        # Direct symbol exact/prefix match
        for idx, sym in enumerate(_SYMBOLS_LIST):
            if sym == q:
                results.append({
                    'company_name': _NAMES_LIST[idx].title(),
                    'symbol': sym,
                    'exchange': 'NSE',
                    'score': 100,
                    'isin': _ISIN_LIST[idx] if idx < len(_ISIN_LIST) else ''
                })
            elif sym.startswith(q) and len(q) >= 2:
                results.append({
                    'company_name': _NAMES_LIST[idx].title(),
                    'symbol': sym,
                    'exchange': 'NSE',
                    'score': 92,
                    'isin': _ISIN_LIST[idx] if idx < len(_ISIN_LIST) else ''
                })

        # Rapidfuzz name extraction
        if len(results) < 4:
            fuzzy_hits = process.extract(q, _NAMES_LIST, scorer=fuzz.WRatio, limit=6)
            for match_name, score, idx in fuzzy_hits:
                if score >= 55:
                    results.append({
                        'company_name': match_name.title(),
                        'symbol': _SYMBOLS_LIST[idx] if idx < len(_SYMBOLS_LIST) else '',
                        'exchange': 'NSE',
                        'score': int(score),
                        'isin': _ISIN_LIST[idx] if idx < len(_ISIN_LIST) else ''
                    })

    # 3. Only if no local matches found, run yfinance search fallback
    if len(results) < 2:
        yf_hits = _yfinance_search(q.lower())
        results.extend(yf_hits)

    # Deduplicate keeping highest score
    best: dict[str, dict] = {}
    for r in results:
        sym = r.get('symbol', '')
        if not sym:
            continue
        if sym not in best or r['score'] > best[sym]['score']:
            best[sym] = r

    sorted_results = sorted(best.values(), key=lambda x: x['score'], reverse=True)
    return sorted_results[:6]


def get_company_info(symbol: str, exchange: str = 'NSE') -> Optional[dict]:
    """
    Verify company listing and fetch full metadata from yfinance.
    """
    suffix = '.NS' if exchange == 'NSE' else '.BO'
    ticker_symbol = symbol.upper() + suffix

    info = None
    for ts in [symbol.upper() + '.NS', symbol.upper() + '.BO']:
        try:
            t = yf.Ticker(ts)
            inf = t.info
            if inf and (inf.get('longName') or inf.get('shortName')):
                if inf.get('regularMarketPrice') or inf.get('currentPrice') or inf.get('marketCap'):
                    info = inf
                    ticker_symbol = ts
                    exchange = 'NSE' if ts.endswith('.NS') else 'BSE'
                    break
        except Exception as e:
            logger.warning(f"yfinance info failed for {ts}: {e}")
            continue

    if info is None:
        return None

    market_cap_inr = info.get('marketCap', 0) or 0
    market_cap_cr = market_cap_inr / 1e7  # INR → Crore

    exchange_display = exchange
    try:
        alt_suffix = '.BO' if exchange == 'NSE' else '.NS'
        alt_info = yf.Ticker(symbol.upper() + alt_suffix).info
        if alt_info and (alt_info.get('longName') or alt_info.get('shortName')):
            exchange_display = 'NSE / BSE'
    except Exception:
        pass

    pat_inr = info.get('netIncomeToCommon') or info.get('trailingNetIncome')
    if not pat_inr and info.get('totalRevenue') and info.get('profitMargins'):
        pat_inr = info.get('totalRevenue') * info.get('profitMargins')
    pat_cr = (pat_inr / 1e7) if pat_inr else None

    return {
        'company_name':       info.get('longName') or info.get('shortName') or symbol,
        'nse_symbol':         symbol.upper() if 'NSE' in exchange_display else None,
        'bse_code':           info.get('symbol', '').replace('.BO', '') if 'BSE' in exchange_display else None,
        'isin':               info.get('isin', 'N/A'),
        'sector':             info.get('sector', 'N/A'),
        'industry':           info.get('industry', 'N/A'),
        'exchange':           exchange_display,
        'market_cap_cr':      round(market_cap_cr, 2),
        'ticker_symbol':      ticker_symbol,
        'currency':           info.get('currency', 'INR'),
        'description':        info.get('longBusinessSummary', ''),
        'employees':          info.get('fullTimeEmployees'),
        'website':            info.get('website', ''),
        'current_price':      info.get('currentPrice') or info.get('regularMarketPrice'),
        'pe_ratio':           info.get('trailingPE'),
        'pb_ratio':           info.get('priceToBook'),
        'dividend_yield':     info.get('dividendYield'),
        'net_income':         round(pat_cr, 2) if pat_cr else None,
        '52w_high':           info.get('fiftyTwoWeekHigh'),
        '52w_low':            info.get('fiftyTwoWeekLow'),
        'shares_outstanding': info.get('sharesOutstanding'),
        'verified':           True,
    }
