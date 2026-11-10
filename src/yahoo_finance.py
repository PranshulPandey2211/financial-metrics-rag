import pandas as pd

TICKER_ALIASES = {
    "APPL": "AAPL",
    "APPLE": "AAPL",
    "GOOGLE": "GOOGL",
    "AMAZON": "AMZN",
    "FACEBOOK": "META",
    "FB": "META",
    "MICROSOFT": "MSFT",
    "TESLA": "TSLA",
    "NVIDIA": "NVDA",
}


def _has_financials(symbol):
    try:
        t = _yf_ticker(symbol)
        inc = t.income_stmt
        if inc is not None and not inc.empty:
            return True
        info = t.info or {}
        return bool(info.get("shortName") or info.get("longName"))
    except Exception:
        return False


def resolve_ticker(symbol):
    raw = (symbol or "").strip().upper()
    if not raw:
        return raw, None

    if raw in TICKER_ALIASES:
        fixed = TICKER_ALIASES[raw]
        return fixed, f"Using **{fixed}** instead of **{raw}** (that symbol has no financials on Yahoo Finance)."

    if _has_financials(raw):
        return raw, None

    if raw in TICKER_ALIASES.values():
        return raw, None

    return raw, (
        f"**{raw}** has no income statement or company profile on Yahoo Finance. "
        "Check the spelling (e.g. **AAPL** for Apple, not APPL)."
    )


def _api_error(message):
    return {"Error": True, "Error Message": message}


def _statement_error(message):
    return {
        "Error": True,
        "Error Message": message,
        "metrics": {},
        "chart_data": {},
        "insights": {},
    }


def _safe_float(value):
    if value is None or value == "None":
        return "N/A"
    try:
        return float(value)
    except (TypeError, ValueError):
        return "N/A"


def _val_to_str(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "None"
    num = float(value)
    if num == int(num):
        return str(int(num))
    return str(num)


def _df_to_annual_reports(df, mapping):
    if df is None or df.empty:
        return []
    reports = []
    for col in sorted(df.columns, reverse=True):
        report = {
            "fiscalDateEnding": pd.Timestamp(col).strftime("%Y-%m-%d"),
        }
        for field_key, yf_row in mapping.items():
            if yf_row and yf_row in df.index:
                report[field_key] = _val_to_str(df.loc[yf_row, col])
            else:
                report[field_key] = "None"
        reports.append(report)
    return reports


def _yf_ticker(symbol):
    import yfinance as yf

    return yf.Ticker(symbol.upper())


_INCOME_MAP = {
    "totalRevenue": "Total Revenue",
    "grossProfit": "Gross Profit",
    "operatingIncome": "Operating Income",
    "netIncome": "Net Income",
    "costOfRevenue": "Cost Of Revenue",
    "costofGoodsAndServicesSold": "Cost Of Revenue",
    "sellingGeneralAndAdministrative": "Selling General And Administration",
    "ebit": "EBIT",
    "interestAndDebtExpense": "Interest Expense",
}

_BALANCE_MAP = {
    "totalAssets": "Total Assets",
    "totalCurrentAssets": "Current Assets",
    "totalNonCurrentAssets": "Total Non Current Assets",
    "totalLiabilities": "Total Liabilities Net Minority Interest",
    "totalCurrentLiabilities": "Current Liabilities",
    "totalNonCurrentLiabilities": "Total Non Current Liabilities Net Minority Interest",
    "totalShareholderEquity": "Stockholders Equity",
    "inventory": "Inventory",
    "shortTermDebt": "Current Debt",
    "longTermDebt": "Long Term Debt",
}

_CASHFLOW_MAP = {
    "operatingCashflow": "Operating Cash Flow",
    "cashflowFromInvestment": "Investing Cash Flow",
    "cashflowFromFinancing": "Financing Cash Flow",
    "capitalExpenditures": "Capital Expenditure",
    "dividendPayout": "Cash Dividends Paid",
    "netIncome": "Net Income",
}


def _fix_balance_reports(reports):
    for r in reports:
        if r.get("totalNonCurrentAssets") == "None":
            ta, ca = r.get("totalAssets"), r.get("totalCurrentAssets")
            if ta != "None" and ca != "None":
                r["totalNonCurrentAssets"] = _val_to_str(float(ta) - float(ca))
        if r.get("totalNonCurrentLiabilities") == "None":
            tl, cl = r.get("totalLiabilities"), r.get("totalCurrentLiabilities")
            if tl != "None" and cl != "None":
                r["totalNonCurrentLiabilities"] = _val_to_str(float(tl) - float(cl))
    return reports


def fetch_overview(symbol):
    try:
        info = _yf_ticker(symbol).info or {}
    except Exception as e:
        return _api_error(f"Yahoo Finance error: {e}")

    if not info.get("symbol") and not info.get("shortName"):
        return _api_error(f"No company data for ticker {symbol.upper()}.")

    cap = info.get("marketCap")
    return {
        "Symbol": info.get("symbol", symbol.upper()),
        "AssetType": info.get("quoteType", ""),
        "Name": info.get("longName") or info.get("shortName", symbol.upper()),
        "Description": info.get("longBusinessSummary", ""),
        "CIK": str(info.get("cik", "") or ""),
        "Exchange": info.get("exchange", ""),
        "Currency": info.get("currency", "USD"),
        "Country": info.get("country", ""),
        "Sector": info.get("sector", ""),
        "Industry": info.get("industry", ""),
        "Address": info.get("address1", ""),
        "FiscalYearEnd": "",
        "LatestQuarter": "",
        "MarketCapitalization": cap if cap is not None else "None",
    }


def fetch_income_statement(symbol):
    try:
        df = _yf_ticker(symbol).income_stmt
    except Exception as e:
        return _statement_error(f"Yahoo Finance error: {e}")
    reports = _df_to_annual_reports(df, _INCOME_MAP)
    if not reports:
        hint = " Try **AAPL** for Apple (not APPL)." if symbol.upper() == "APPL" else ""
        return _statement_error(f"No income statement for {symbol.upper()}.{hint}")
    return {"annualReports": reports}


def fetch_balance_sheet(symbol):
    try:
        df = _yf_ticker(symbol).balance_sheet
    except Exception as e:
        return _statement_error(f"Yahoo Finance error: {e}")
    reports = _fix_balance_reports(_df_to_annual_reports(df, _BALANCE_MAP))
    if not reports:
        hint = " Try **AAPL** for Apple (not APPL)." if symbol.upper() == "APPL" else ""
        return _statement_error(f"No balance sheet for {symbol.upper()}.{hint}")
    return {"annualReports": reports}


def fetch_cash_flow(symbol):
    try:
        t = _yf_ticker(symbol)
        cf = t.cashflow
        inc = t.income_stmt
    except Exception as e:
        return _statement_error(f"Yahoo Finance error: {e}")

    mapping = {k: v for k, v in _CASHFLOW_MAP.items() if k != "netIncome"}
    reports = _df_to_annual_reports(cf, mapping)
    if not reports:
        hint = " Try **AAPL** for Apple (not APPL)." if symbol.upper() == "APPL" else ""
        return _statement_error(f"No cash flow for {symbol.upper()}.{hint}")

    if inc is not None and not inc.empty and "Net Income" in inc.index:
        for report in reports:
            date = report["fiscalDateEnding"]
            for col in inc.columns:
                if pd.Timestamp(col).strftime("%Y-%m-%d") == date:
                    report["netIncome"] = _val_to_str(inc.loc["Net Income", col])
                    break

    for report in reports:
        for key in ("capitalExpenditures", "dividendPayout"):
            if report.get(key) not in (None, "None"):
                try:
                    v = float(report[key])
                    if v < 0:
                        report[key] = _val_to_str(abs(v))
                except ValueError:
                    pass

    return {"annualReports": reports}


def _url_from_content(content):
    for key in ("clickThroughUrl", "canonicalUrl", "previewUrl"):
        block = content.get(key)
        if isinstance(block, dict) and block.get("url"):
            return str(block["url"])
    return ""


_vader_analyzer = None


def _get_vader():
    global _vader_analyzer
    if _vader_analyzer is None:
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer

        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        _vader_analyzer = SentimentIntensityAnalyzer()
    return _vader_analyzer


def _headline_sentiment(text):
    from src.company_news import classify_sentiment

    compound = float(_get_vader().polarity_scores(text or "")["compound"])
    return round(compound, 4), classify_sentiment(compound)


def _parse_yf_news_item(item):
    content = item.get("content")
    if isinstance(content, dict):
        title = (content.get("title") or "").strip()
        if not title:
            return None
        publisher = ""
        provider = content.get("provider")
        if isinstance(provider, dict):
            publisher = provider.get("displayName") or ""
        summary = (content.get("summary") or content.get("description") or "").strip()
        return {
            "title": title,
            "url": _url_from_content(content),
            "publisher": publisher,
            "published": content.get("pubDate") or content.get("displayTime") or "",
            "summary": summary,
        }

    title = (item.get("title") or "").strip()
    if not title:
        return None
    return {
        "title": title,
        "url": item.get("link") or item.get("url") or "",
        "publisher": item.get("publisher") or "",
        "published": item.get("providerPublishTime") or "",
        "summary": "",
    }


def fetch_news(symbol, max_feed=10):
    try:
        items = _yf_ticker(symbol).news or []
    except Exception as e:
        return _api_error(f"Yahoo Finance news error: {e}")

    rows = []
    for item in items:
        if len(rows) >= max_feed:
            break
        parsed = _parse_yf_news_item(item)
        if parsed:
            blob = f"{parsed['title']}. {parsed.get('summary', '')}".strip()
            score, label = _headline_sentiment(blob)
            parsed["sentiment_score"] = score
            parsed["sentiment_label"] = label
            rows.append(parsed)

    if not rows:
        return _api_error(f"No recent news for {symbol.upper()}.")

    news_df = pd.DataFrame(rows)
    from src.company_news import classify_sentiment

    mean_score = float(news_df["sentiment_score"].mean())
    return {
        "news": news_df,
        "mean_sentiment_score": mean_score,
        "mean_sentiment_class": classify_sentiment(mean_score),
    }


def fetch_quote_stats(symbol):
    try:
        info = _yf_ticker(symbol).info or {}
    except Exception:
        return {}
    if not info:
        return {}

    def pick(*keys):
        for k in keys:
            v = info.get(k)
            if v is not None:
                return v
        return None

    return {
        "price": pick("currentPrice", "regularMarketPrice"),
        "trailing_pe": pick("trailingPE"),
        "forward_pe": pick("forwardPE"),
        "price_to_book": pick("priceToBook"),
        "ev_to_ebitda": pick("enterpriseToEbitda"),
        "beta": pick("beta"),
        "dividend_yield": pick("dividendYield"),
        "fifty_two_week_low": pick("fiftyTwoWeekLow"),
        "fifty_two_week_high": pick("fiftyTwoWeekHigh"),
    }


def latest_total_revenue(symbol):
    data = fetch_income_statement(symbol)
    if data.get("Error"):
        return "N/A"
    return _safe_float(data["annualReports"][0].get("totalRevenue"))


def latest_total_debt(symbol):
    data = fetch_balance_sheet(symbol)
    if data.get("Error"):
        return "N/A"
    r = data["annualReports"][0]
    st_d = _safe_float(r.get("shortTermDebt"))
    lt = _safe_float(r.get("longTermDebt"))
    if st_d == "N/A" or lt == "N/A":
        return "N/A"
    return st_d + lt
