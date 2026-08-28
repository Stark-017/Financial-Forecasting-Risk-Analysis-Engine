# storage/db.py
# SQLite database: schema creation and CRUD helpers

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "financial_data.db"

# Make sure cache/raw/clean/exports directories exist
for sub in ("raw", "clean", "exports", "cache"):
    (DB_DIR / sub).mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name    TEXT NOT NULL,
            nse_symbol      TEXT,
            bse_code        TEXT,
            isin            TEXT,
            sector          TEXT,
            industry        TEXT,
            exchange        TEXT,
            market_cap_cr   REAL,
            ticker_symbol   TEXT,
            retrieval_date  TEXT
        );

        CREATE TABLE IF NOT EXISTS financial_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER REFERENCES companies(id),
            fy              TEXT NOT NULL,
            statement_type  TEXT NOT NULL,
            metric          TEXT NOT NULL,
            raw_value       REAL,
            std_value       REAL,
            unit            TEXT DEFAULT 'Crore',
            currency        TEXT DEFAULT 'INR',
            source          TEXT,
            retrieval_date  TEXT
        );

        CREATE TABLE IF NOT EXISTS financial_ratios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER REFERENCES companies(id),
            fy              TEXT NOT NULL,
            metric          TEXT NOT NULL,
            value           REAL,
            retrieval_date  TEXT
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER REFERENCES companies(id),
            fy              TEXT,
            check_name      TEXT NOT NULL,
            status          TEXT NOT NULL,
            message         TEXT,
            retrieval_date  TEXT
        );

        CREATE TABLE IF NOT EXISTS forecasts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER REFERENCES companies(id),
            scenario        TEXT NOT NULL,
            fy              TEXT NOT NULL,
            metric          TEXT NOT NULL,
            value           REAL,
            created_date    TEXT
        );
    """)
    conn.commit()
    conn.close()


def upsert_company(info: dict) -> int:
    """Insert or update company record; return company_id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM companies WHERE nse_symbol = ? OR company_name = ?",
        (info.get('nse_symbol'), info.get('company_name'))
    )
    row = c.fetchone()
    now = datetime.now().isoformat()
    if row:
        cid = row['id']
        c.execute("""
            UPDATE companies
            SET company_name=?, nse_symbol=?, bse_code=?, isin=?, sector=?,
                industry=?, exchange=?, market_cap_cr=?, ticker_symbol=?,
                retrieval_date=?
            WHERE id=?
        """, (
            info.get('company_name'), info.get('nse_symbol'), info.get('bse_code'),
            info.get('isin'), info.get('sector'), info.get('industry'),
            info.get('exchange'), info.get('market_cap_cr'), info.get('ticker_symbol'),
            now, cid
        ))
    else:
        c.execute("""
            INSERT INTO companies
                (company_name, nse_symbol, bse_code, isin, sector, industry,
                 exchange, market_cap_cr, ticker_symbol, retrieval_date)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            info.get('company_name'), info.get('nse_symbol'), info.get('bse_code'),
            info.get('isin'), info.get('sector'), info.get('industry'),
            info.get('exchange'), info.get('market_cap_cr'), info.get('ticker_symbol'),
            now
        ))
        cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


def save_raw_json(company_name: str, data: dict, tag: str = ""):
    """Save raw API response as JSON for auditability."""
    safe_name = company_name.replace(' ', '_').replace('/', '_')[:30]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = DB_DIR / "raw" / f"{safe_name}_{tag}_{ts}.json"
    try:
        with open(fname, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass
    return str(fname)


def get_company_by_symbol(symbol: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM companies WHERE nse_symbol=? OR bse_code=?",
        (symbol, symbol)
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# Initialise DB on import
init_db()
