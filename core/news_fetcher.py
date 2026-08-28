# core/news_fetcher.py
"""
Corporate News, Stock Performance & Sector/Global News Fetcher.
Segment 1: Today's stock performance + company-specific news (last 7 days)
Segment 2: Sector-wide and global macro news
"""

import urllib.parse
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import streamlit as st
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300, show_spinner=False)   # cache 5 mins
def _fetch_yf_news(ticker_symbol: str) -> list:
    """Cached Yahoo Finance news fetch."""
    try:
        t = yf.Ticker(ticker_symbol)
        return t.news or []
    except Exception as e:
        logger.warning(f"yfinance news error: {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_google_news(query: str) -> list:
    """Cached Google News RSS fetch."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.content, 'xml')
        items = []
        for item in soup.find_all('item')[:10]:
            title = item.title.text if item.title else ''
            link  = item.link.text if item.link else '#'
            pub   = item.pubDate.text if item.pubDate else ''
            src   = item.source.text if item.source else 'Google News'
            items.append({'title': title.split(' - ')[0].strip(), 'link': link, 'pub_date': pub, 'source': src})
        return items
    except Exception as e:
        logger.warning(f"Google News RSS error: {e}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_stock_history(ticker_symbol: str) -> dict:
    """Fetch today + 3-month price history for the floating ticker widget."""
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period='3mo')
        if hist.empty:
            return {}
        today_open  = float(hist['Open'].iloc[-1])
        today_close = float(hist['Close'].iloc[-1])
        day_change  = today_close - today_open
        day_pct     = (day_change / today_open * 100) if today_open else 0
        month3_open = float(hist['Open'].iloc[0])
        month3_pct  = ((today_close - month3_open) / month3_open * 100) if month3_open else 0
        week52_high = float(hist['High'].max())
        week52_low  = float(hist['Low'].min())
        return {
            'today_open':  round(today_open, 2),
            'today_close': round(today_close, 2),
            'day_change':  round(day_change, 2),
            'day_pct':     round(day_pct, 2),
            'month3_pct':  round(month3_pct, 2),
            '52w_high':    round(week52_high, 2),
            '52w_low':     round(week52_low, 2),
        }
    except Exception as e:
        logger.warning(f"Stock history error: {e}")
        return {}


def _categorize(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ['contract', 'order', 'deal', 'win', 'bags', 'secures', 'partnership', 'mou', 'tender']):
        return '🚀 CONTRACT / ORDER WIN'
    if any(k in t for k in ['quarter', 'q1', 'q2', 'q3', 'q4', 'earnings', 'profit', 'pat', 'revenue', 'results', 'beat', 'margin', 'ebitda']):
        return '📊 EARNINGS & RESULTS'
    if any(k in t for k in ['expansion', 'plant', 'capacity', 'launch', 'new product', 'acquisition', 'patent', 'ipo']):
        return '📈 GROWTH & EXPANSION'
    return '📰 CORPORATE UPDATE'


def _sentiment(text: str) -> str:
    t = text.lower()
    pos = sum(1 for k in ['beat', 'surges', 'record', 'growth', 'bags', 'win', 'profit', 'jumps', 'rises', 'robust', 'strong', 'expands', 'boost', 'highest'] if k in t)
    neg = sum(1 for k in ['drop', 'fall', 'loss', 'plunge', 'decline', 'penalty', 'slump', 'misses', 'warning', 'risk', 'fraud', 'tax notice'] if k in t)
    return 'POSITIVE' if pos > neg else ('CAUTION' if neg > pos else 'NEUTRAL')


def _is_within_7_days(pub_date_str: str) -> bool:
    """Return True if the publication date is within the last 7 days."""
    if not pub_date_str:
        return False
    try:
        # Try standard RSS format: "Mon, 07 Aug 2026 01:04:25 +0000"
        dt = datetime.strptime(pub_date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
        except Exception:
            return False
    return (datetime.now(timezone.utc) - dt) <= timedelta(days=7)


def fetch_segment1_news(company_info: dict) -> list:
    """
    Segment 1: Company-specific news from last 7 days + today's headlines.
    Sources: Yahoo Finance + Google News (company name query).
    """
    ticker_symbol = company_info.get('ticker_symbol', '')
    company_name  = company_info.get('company_name', '')
    symbol        = company_info.get('nse_symbol') or company_info.get('bse_code', '')
    seen          = set()
    results       = []

    # Yahoo Finance news (already company-specific)
    if ticker_symbol:
        for item in _fetch_yf_news(ticker_symbol):
            content   = item.get('content', {})
            title     = content.get('title') or item.get('title', '')
            if not title or title in seen:
                continue
            seen.add(title)
            summary  = content.get('summary') or ''
            provider = content.get('provider', {}).get('displayName') or 'Yahoo Finance'
            click_url = content.get('clickThroughUrl', {})
            link      = click_url.get('url') if isinstance(click_url, dict) else item.get('link') or '#'
            pub_date  = content.get('displayTime') or content.get('pubDate') or ''
            results.append({
                'title':     title,
                'summary':   summary,
                'link':      link,
                'source':    provider,
                'pub_date':  pub_date,
                'category':  _categorize(title + ' ' + summary),
                'sentiment': _sentiment(title + ' ' + summary),
                'is_recent': _is_within_7_days(pub_date),
            })

    # Google News — company-specific
    search = company_name or symbol
    for item in _fetch_google_news(f"{search} NSE BSE stock earnings contract order"):
        title = item['title']
        if not title or title in seen:
            continue
        seen.add(title)
        results.append({
            'title':     title,
            'summary':   '',
            'link':      item['link'],
            'source':    item['source'],
            'pub_date':  item['pub_date'],
            'category':  _categorize(title),
            'sentiment': _sentiment(title),
            'is_recent': _is_within_7_days(item['pub_date']),
        })

    return results[:8]


def fetch_segment2_news(company_info: dict) -> list:
    """
    Segment 2: Sector-wide and global macro news.
    Sources: Google News (sector + global economy queries).
    """
    sector  = company_info.get('sector', '')
    results = []
    seen    = set()

    queries = []
    if sector and sector != 'N/A':
        queries.append(f"{sector} sector India NSE BSE news")
    queries.append("India economy RBI stock market BSE NSE")
    queries.append("global market economy Fed interest rates")

    for q in queries:
        for item in _fetch_google_news(q):
            title = item['title']
            if not title or title in seen:
                continue
            seen.add(title)
            results.append({
                'title':     title,
                'link':      item['link'],
                'source':    item['source'],
                'pub_date':  item['pub_date'],
                'category':  '🌏 SECTOR / GLOBAL',
                'sentiment': _sentiment(title),
            })
        if len(results) >= 8:
            break

    return results[:8]


def _news_card(item: dict):
    """Render a single news card."""
    cat       = item.get('category', '📰')
    sentiment = item.get('sentiment', 'NEUTRAL')
    sent_color = '#059669' if sentiment == 'POSITIVE' else ('#dc2626' if sentiment == 'CAUTION' else '#64748b')
    title     = item.get('title', '')
    source    = item.get('source', '')
    pub_date  = item.get('pub_date', '')
    link      = item.get('link', '#')
    st.markdown(f"""
<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;
            padding:14px 16px; margin:8px 0; box-shadow:0 1px 4px rgba(0,0,0,0.04);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
        <span style="font-size:0.7rem; font-weight:800; color:#0f172a; text-transform:uppercase; letter-spacing:0.05em;">{cat}</span>
        <span style="background:{sent_color}; color:#fff; padding:1px 8px; border-radius:100px; font-size:0.65rem; font-weight:800;">{sentiment}</span>
    </div>
    <a href="{link}" target="_blank"
       style="color:#0f172a; font-weight:700; font-size:0.95rem; line-height:1.4; text-decoration:none;">
        {title} ↗
    </a>
    <div style="color:#94a3b8; font-size:0.75rem; margin-top:5px;">
        <b>{source}</b> &nbsp;|&nbsp; {pub_date}
    </div>
</div>""", unsafe_allow_html=True)


def _parse_ts(pub_date_str: str) -> float:
    """Parse pub date string to Unix timestamp for sorting. Returns 0 on failure."""
    if not pub_date_str:
        return 0.0
    try:
        dt = datetime.strptime(pub_date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        try:
            return datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).timestamp()
        except Exception:
            return 0.0


def render_news_section(company_info: dict):
    """
    Render 2-segment corporate news panel:
    Segment 1 — Today's stock performance + company-specific news (last 7 days only, newest first)
    Segment 2 — Sector & global macro news (last 7 days only, newest first)
    """
    company_name = company_info.get('company_name', 'Company')
    ticker_symbol = company_info.get('ticker_symbol', '')

    st.markdown("---")
    st.subheader("📰 Live Corporate News, Market Catalysts & Global Context")

    # ── Stock Performance Metrics: FULL WIDTH above the news columns ──────────
    if ticker_symbol:
        hist = _fetch_stock_history(ticker_symbol)
        if hist:
            day_sign  = "+" if hist['day_pct'] >= 0 else ""
            day_color = "#10b981" if hist['day_pct'] >= 0 else "#ef4444"
            m3mo_sign = "+" if hist['month3_pct'] >= 0 else ""
            m3mo_color= "#10b981" if hist['month3_pct'] >= 0 else "#ef4444"

            st.markdown(f"""
<div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:16px;">
  <div style="flex:1; min-width:140px; background:#f8fafc; border:1px solid #e2e8f0;
              border-radius:12px; padding:12px 16px;">
    <div style="font-size:0.7rem; color:#64748b; font-weight:700; text-transform:uppercase;
                letter-spacing:0.06em; margin-bottom:4px;">Today's Close</div>
    <div style="font-size:1.5rem; font-weight:900; color:#0f172a; line-height:1.1;">
      ₹{hist['today_close']:,.2f}
    </div>
    <div style="font-size:0.78rem; font-weight:700; color:{day_color}; margin-top:3px;">
      {day_sign}{hist['day_pct']:.2f}% today
    </div>
  </div>
  <div style="flex:1; min-width:140px; background:#f8fafc; border:1px solid #e2e8f0;
              border-radius:12px; padding:12px 16px;">
    <div style="font-size:0.7rem; color:#64748b; font-weight:700; text-transform:uppercase;
                letter-spacing:0.06em; margin-bottom:4px;">3-Month Change</div>
    <div style="font-size:1.5rem; font-weight:900; color:{m3mo_color}; line-height:1.1;">
      {m3mo_sign}{hist['month3_pct']:.2f}%
    </div>
  </div>
  <div style="flex:1; min-width:140px; background:#f8fafc; border:1px solid #e2e8f0;
              border-radius:12px; padding:12px 16px;">
    <div style="font-size:0.7rem; color:#64748b; font-weight:700; text-transform:uppercase;
                letter-spacing:0.06em; margin-bottom:4px;">52-Week High</div>
    <div style="font-size:1.5rem; font-weight:900; color:#0f172a; line-height:1.1;">
      ₹{hist['52w_high']:,.2f}
    </div>
  </div>
  <div style="flex:1; min-width:140px; background:#f8fafc; border:1px solid #e2e8f0;
              border-radius:12px; padding:12px 16px;">
    <div style="font-size:0.7rem; color:#64748b; font-weight:700; text-transform:uppercase;
                letter-spacing:0.06em; margin-bottom:4px;">52-Week Low</div>
    <div style="font-size:1.5rem; font-weight:900; color:#0f172a; line-height:1.1;">
      ₹{hist['52w_low']:,.2f}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Two-column news panels ────────────────────────────────────────────────
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(f"**📈 {company_name} — Company News (Last 7 Days)**")

        with st.spinner("Loading company news..."):
            raw_news1 = fetch_segment1_news(company_info)

        # Strict 7-day filter + sort newest first
        news1 = [n for n in raw_news1 if n.get('is_recent', False)]
        news1.sort(key=lambda x: _parse_ts(x.get('pub_date', '')), reverse=True)

        if not news1:
            st.info("No company news found in the last 7 days.")
        else:
            for item in news1:
                _news_card(item)

    with col2:
        sector = company_info.get('sector', 'Market')
        st.markdown(f"**🌏 {sector} Sector & Global Macro News**")

        with st.spinner("Loading sector & global news..."):
            raw_news2 = fetch_segment2_news(company_info)

        # Strict 7-day filter + sort newest first
        news2 = [n for n in raw_news2 if _is_within_7_days(n.get('pub_date', ''))]
        news2.sort(key=lambda x: _parse_ts(x.get('pub_date', '')), reverse=True)

        if not news2:
            st.info("No sector or global news found in the last 7 days.")
        else:
            for item in news2:
                _news_card(item)

