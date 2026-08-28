# utils/constants.py
# Central definitions: field mappings, schema, thresholds, colours

# ─────────────────────────────────────────────
#  YFINANCE → STANDARDISED FIELD MAPPINGS
# ─────────────────────────────────────────────

INCOME_STMT_MAP = {
    # Revenue
    "Total Revenue":                           "revenue",
    "Operating Revenue":                       "revenue",
    # COGS
    "Cost Of Revenue":                         "cost_of_goods_sold",
    "Reconciled Cost Of Revenue":              "cost_of_goods_sold",
    # Gross Profit
    "Gross Profit":                            "gross_profit",
    # Employee / SGA
    "Selling General Administrative":          "sga_expenses",
    "General And Administrative Expense":      "sga_expenses",
    "Research And Development":                "rd_expenses",
    # EBITDA (sometimes reported directly)
    "EBITDA":                                  "ebitda",
    "Normalized EBITDA":                       "ebitda",
    # D&A
    "Reconciled Depreciation":                 "depreciation_amortization",
    "Depreciation And Amortization In Income Statement": "depreciation_amortization",
    "Depreciation Amortization Depletion":     "depreciation_amortization",
    # EBIT / Operating Income
    "Operating Income":                        "ebit",
    "EBIT":                                    "ebit",
    # Interest
    "Interest Expense":                        "interest_expense",
    "Interest Expense Non Operating":          "interest_expense",
    # Other Income
    "Other Income Expense":                    "other_income",
    "Non Operating Income Total Other":        "other_income",
    "Total Other Income Expense Net":          "other_income",
    # PBT
    "Pretax Income":                           "profit_before_tax",
    # Tax
    "Tax Provision":                           "tax_expense",
    "Income Tax Expense":                      "tax_expense",
    # Net Income
    "Net Income":                              "net_income",
    "Net Income Common Stockholders":          "net_income",
    "Net Income From Continuing Operations":   "net_income",
    # EPS
    "Basic EPS":                               "eps_basic",
    "Diluted EPS":                             "eps_diluted",
    "Basic Average Shares":                    "shares_basic",
    "Diluted Average Shares":                  "shares_diluted",
    # Total Operating Expenses
    "Total Expenses":                          "total_operating_expenses",
    "Operating Expense":                       "other_operating_expenses",
}

BALANCE_SHEET_MAP = {
    # Cash
    "Cash And Cash Equivalents":               "cash",
    "Cash Cash Equivalents And Short Term Investments": "cash",
    "Cash And Short Term Investments":         "cash",
    # Receivables
    "Receivables":                             "trade_receivables",
    "Net Receivables":                         "trade_receivables",
    "Accounts Receivable":                     "trade_receivables",
    # Inventory
    "Inventory":                               "inventory",
    # Other Current Assets
    "Other Current Assets":                    "other_current_assets",
    "Prepaid Assets":                          "other_current_assets",
    # Total Current Assets
    "Current Assets":                          "total_current_assets",
    "Total Current Assets":                    "total_current_assets",
    # PP&E
    "Net PPE":                                 "net_ppe",
    "Property Plant Equipment Net":            "net_ppe",
    # Intangibles
    "Goodwill And Other Intangible Assets":    "intangibles",
    "Goodwill":                                "goodwill",
    "Other Intangible Assets":                 "intangibles",
    # Investments
    "Long Term Equity Investment":             "investments",
    "Available For Sale Securities":           "investments",
    "Investmentin Financial Assets":           "investments",
    # Other Non-Current
    "Other Non Current Assets":                "other_non_current_assets",
    # Total Assets
    "Total Assets":                            "total_assets",
    # Payables
    "Accounts Payable":                        "trade_payables",
    "Payables And Accrued Expenses":           "trade_payables",
    # Short Term Debt
    "Current Debt":                            "short_term_debt",
    "Short Term Debt":                         "short_term_debt",
    "Current Debt And Capital Lease Obligation": "short_term_debt",
    # Other Current Liabilities
    "Other Current Liabilities":               "other_current_liabilities",
    "Current Accrued Expenses":                "other_current_liabilities",
    # Total Current Liabilities
    "Current Liabilities":                     "total_current_liabilities",
    "Total Current Liabilities":               "total_current_liabilities",
    # Long Term Debt
    "Long Term Debt":                          "long_term_debt",
    "Long Term Debt And Capital Lease Obligation": "long_term_debt",
    # Other Non-Current Liabilities
    "Other Non Current Liabilities":           "other_non_current_liabilities",
    "Tradeand Other Payables Non Current":     "other_non_current_liabilities",
    # Total Liabilities
    "Total Liabilities Net Minority Interest": "total_liabilities",
    # Share Capital
    "Common Stock":                            "share_capital",
    "Share Issued":                            "share_capital",
    # Retained Earnings
    "Retained Earnings":                       "retained_earnings",
    # Other Equity
    "Additional Paid In Capital":              "other_equity",
    "Capital Surplus":                         "other_equity",
    # Total Equity
    "Stockholders Equity":                     "total_equity",
    "Total Equity Gross Minority Interest":    "total_equity",
    "Common Stock Equity":                     "total_equity",
}

CASH_FLOW_MAP = {
    # Operating
    "Net Income From Continuing Operations":   "net_income_cf",
    "Net Income":                              "net_income_cf",
    "Depreciation And Amortization":           "depreciation_amortization_cf",
    "Depreciation Amortization Depletion":     "depreciation_amortization_cf",
    "Change In Working Capital":               "working_capital_changes",
    "Changes In Account Receivables":          "changes_in_receivables",
    "Change In Inventory":                     "changes_in_inventory",
    "Change In Payable":                       "changes_in_payables",
    "Other Non Cash Items":                    "other_operating",
    "Deferred Tax":                            "deferred_tax",
    "Operating Cash Flow":                     "cash_from_operations",
    "Cash Flow From Continuing Operating Activities": "cash_from_operations",
    # Investing
    "Capital Expenditure":                     "capex",
    "Purchase Of PPE":                         "capex",
    "Purchase Of Business":                    "acquisitions",
    "Purchase Of Investment":                  "purchase_of_investments",
    "Sale Of Investment":                      "proceeds_from_investments",
    "Other Investing Cash Flow":               "other_investing",
    "Investing Cash Flow":                     "cash_from_investing",
    "Cash Flow From Continuing Investing Activities": "cash_from_investing",
    # Financing
    "Issuance Of Debt":                        "debt_issuance",
    "Repayment Of Debt":                       "debt_repayment",
    "Common Stock Dividend Paid":              "dividends_paid",
    "Repurchase Of Capital Stock":             "share_buybacks",
    "Proceeds From Stock Option Exercised":    "share_issuance",
    "Other Financing Cash Flow":               "other_financing",
    "Financing Cash Flow":                     "cash_from_financing",
    "Cash Flow From Continuing Financing Activities": "cash_from_financing",
    # Net Change
    "Changes In Cash":                         "net_change_in_cash",
    "Beginning Cash Position":                 "beginning_cash",
    "End Cash Position":                       "ending_cash",
    "Free Cash Flow":                          "free_cash_flow",
}

# ─────────────────────────────────────────────
#  STANDARD COLUMN LISTS
# ─────────────────────────────────────────────

IS_COLUMNS = [
    "revenue", "cost_of_goods_sold", "gross_profit",
    "sga_expenses", "rd_expenses", "other_operating_expenses",
    "total_operating_expenses", "ebitda", "depreciation_amortization",
    "ebit", "interest_expense", "other_income", "profit_before_tax",
    "tax_expense", "net_income", "eps_basic", "eps_diluted",
    "shares_basic", "shares_diluted",
]

BS_COLUMNS = [
    "cash", "trade_receivables", "inventory", "other_current_assets",
    "total_current_assets", "net_ppe", "goodwill", "intangibles",
    "investments", "other_non_current_assets", "total_assets",
    "trade_payables", "short_term_debt", "other_current_liabilities",
    "total_current_liabilities", "long_term_debt",
    "other_non_current_liabilities", "total_liabilities",
    "share_capital", "retained_earnings", "other_equity", "total_equity",
    "total_liabilities_equity",
]

CF_COLUMNS = [
    "net_income_cf", "depreciation_amortization_cf",
    "working_capital_changes", "other_operating",
    "cash_from_operations", "capex", "acquisitions",
    "purchase_of_investments", "proceeds_from_investments",
    "other_investing", "cash_from_investing",
    "debt_issuance", "debt_repayment", "dividends_paid",
    "share_buybacks", "share_issuance", "other_financing",
    "cash_from_financing", "net_change_in_cash",
    "beginning_cash", "ending_cash", "free_cash_flow",
]

# ─────────────────────────────────────────────
#  UNIT CONVERSION
# ─────────────────────────────────────────────

UNIT_TO_CRORE = {
    "Crore":   1.0,
    "Cr":      1.0,
    "Lakh":    0.01,
    "Million": 0.1,
    "Mn":      0.1,
    "Billion": 100.0,
    "Bn":      100.0,
    "INR":     1e-7,   # raw INR → Crore
}

YFINANCE_UNIT = 1e-7   # yfinance reports in INR; divide by 1e7 to get Crore

# ─────────────────────────────────────────────
#  RISK THRESHOLDS
# ─────────────────────────────────────────────

RISK_THRESHOLDS = {
    "current_ratio":       {"good": 2.0, "ok": 1.0, "bad": 0.5},
    "quick_ratio":         {"good": 1.5, "ok": 0.8, "bad": 0.4},
    "debt_to_equity":      {"good": 0.5, "ok": 1.5, "bad": 3.0},
    "net_debt_ebitda":     {"good": 1.0, "ok": 3.0, "bad": 5.0},
    "interest_coverage":   {"good": 5.0, "ok": 2.0, "bad": 1.0},
    "ebitda_margin_pct":   {"good": 20.0, "ok": 10.0, "bad": 5.0},
    "net_margin_pct":      {"good": 10.0, "ok": 5.0,  "bad": 0.0},
    "roe_pct":             {"good": 15.0, "ok": 8.0,  "bad": 0.0},
    "fcf_margin_pct":      {"good": 10.0, "ok": 3.0,  "bad": 0.0},
}

# ─────────────────────────────────────────────
#  UI COLOURS — SCHEMATIQ INSPIRED DESIGN SYSTEM
# ─────────────────────────────────────────────

COLOUR = {
    "good":        "#059669",   # emerald green
    "base":        "#d97706",   # warm amber
    "bad":         "#dc2626",   # crimson red
    "accent":      "#0f172a",   # deep slate / obsidian
    "brand_gradient": "linear-gradient(135deg, #ff7e5f 0%, #feb47b 50%, #ff6b8b 100%)",
    "card_bg":     "#ffffff",
    "border":      "#e2e8f0",
    "border_focus":"#0f172a",
    "text_main":   "#0f172a",
    "text_muted":  "#64748b",
    "bg_subtle":   "#f8fafc",
    "positive":    "#059669",
    "negative":    "#dc2626",
    "neutral":     "#64748b",
}

# ─────────────────────────────────────────────
#  SCENARIO MULTIPLIERS  (applied to base driver)
# ─────────────────────────────────────────────
# These are default adjustments; scenario_engine replaces them with
# σ-based values once historical data is available.

SCENARIO_DEFAULTS = {
    "good": {
        "revenue_growth_add":      2.0,   # percentage points added to base
        "ebitda_margin_add":       1.5,
        "receivable_days_mult":    0.90,  # 10% better collections
        "inventory_days_mult":     0.95,
        "payable_days_mult":       1.00,
        "capex_rev_mult":          1.15,  # higher expansion investment
        "interest_rate_add":      -0.25,  # lower cost of debt (pp)
        "tax_rate_add":            0.00,
    },
    "base": {
        "revenue_growth_add":      0.0,
        "ebitda_margin_add":       0.0,
        "receivable_days_mult":    1.00,
        "inventory_days_mult":     1.00,
        "payable_days_mult":       1.00,
        "capex_rev_mult":          1.00,
        "interest_rate_add":       0.00,
        "tax_rate_add":            0.00,
    },
    "bad": {
        "revenue_growth_add":     -3.0,
        "ebitda_margin_add":      -2.5,
        "receivable_days_mult":    1.15,
        "inventory_days_mult":     1.10,
        "payable_days_mult":       1.05,
        "capex_rev_mult":          0.75,
        "interest_rate_add":       0.50,
        "tax_rate_add":            1.00,
    },
}
