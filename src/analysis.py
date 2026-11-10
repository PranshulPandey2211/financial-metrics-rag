import json
import uuid

from langchain.prompts import PromptTemplate

from src import analysis_cache
from src.balance_sheet import balance_sheet
from src.cash_flow import cash_flow
from src.company_news import top_news
from src.company_profile import company_overview
from src.helpers import get_chat_model, safe_float
from src.income_statement import income_statement
from src.insight_themes import (
    ALL_FILING_KEYS,
    ALL_FUNDAMENTALS_KEYS,
    GROUPS,
    THEMES,
)
from src.llm_prompts import FILING_BATCH_INSIGHT, FUNDAMENTALS_BATCH_INSIGHT
from src.rag import build_retriever, pdf_fingerprint, retrieve_for_theme
from src.yahoo_finance import _has_financials, fetch_quote_stats, resolve_ticker


def run_analysis(
    ticker: str,
    *,
    theme_flags: dict[str, bool],
    api_key: str,
    pdf_bytes: bytes | None = None,
    force_refresh: bool = False,
):
    """Ticker fundamentals (Yahoo) + optional 10-K PDF RAG. Returns a result dict for the UI."""
    result = {
        "run_id": uuid.uuid4().hex[:12],
        "ticker": ticker.strip().upper(),
        "resolved_ticker": None,
        "ticker_note": None,
        "steps": [],
        "company": None,
        "income": None,
        "balance": None,
        "cash": None,
        "news": None,
        "fundamentals_insights": {},
        "filing_insights": {},
        "filing_sources": {},
        "quote": {},
        "error": None,
    }

    symbol, note = resolve_ticker(result["ticker"])
    if not _has_financials(symbol):
        result["error"] = note or f"{result['ticker']} has no financial data."
        return result
    result["resolved_ticker"] = symbol
    result["ticker_note"] = note
    result["quote"] = fetch_quote_stats(symbol)

    inc_flags = [theme_flags.get(k, True) for k in GROUPS["income"]]
    bal_flags = [theme_flags.get(k, True) for k in GROUPS["balance"]]
    cf_flags = [theme_flags.get(k, True) for k in GROUPS["cash"]]
    want_fund_llm = any(inc_flags + bal_flags + cf_flags)

    loaded_cache = False
    if want_fund_llm and not force_refresh:
        key = analysis_cache.cache_key(symbol, inc_flags, bal_flags, cf_flags)
        if analysis_cache.has_saved_report(key):
            bundle = analysis_cache.load_report(key)
            if bundle and bundle.get("company_overview"):
                loaded_cache = True
                result["steps"].append("Loaded cached Yahoo data.")
                result["company"] = bundle["company_overview"]
                result["income"] = bundle.get("income_statement")
                result["balance"] = bundle.get("balance_sheet")
                result["cash"] = bundle.get("cash_flow")
                result["news"] = bundle.get("news")
                for block in (result["income"], result["balance"], result["cash"]):
                    if block:
                        result["fundamentals_insights"].update(block.get("insights") or {})

    if not loaded_cache:
        result["steps"].append("Pulling company profile and statements from Yahoo…")
        result["company"] = company_overview(symbol)
        result["income"] = income_statement(symbol)
        rev = _latest_revenue(result["income"])
        result["balance"] = balance_sheet(symbol, total_revenue=rev)
        debt = _total_debt(result["balance"])
        result["cash"] = cash_flow(symbol, total_revenue=rev, total_debt=debt)
        result["news"] = top_news(symbol, 10)
    elif result["fundamentals_insights"]:
        return _maybe_rag(result, theme_flags, api_key, pdf_bytes)

    fund_keys = [k for k in ALL_FUNDAMENTALS_KEYS if theme_flags.get(k, True)]
    if fund_keys and not result["fundamentals_insights"]:
        result["steps"].append("Writing fundamentals commentary (one LLM call)…")
        payload = {"income": result["income"], "balance": result["balance"], "cash": result["cash"]}
        result["fundamentals_insights"] = _batch_fundamentals(fund_keys, payload, api_key)
        _attach_insights(result)

    if result.get("income") and result["company"]:
        analysis_cache.save_report(
            analysis_cache.cache_key(symbol, inc_flags, bal_flags, cf_flags),
            company_overview=result["company"],
            income_statement=result["income"],
            balance_sheet=result["balance"],
            cash_flow=result["cash"],
            news=result["news"],
        )

    return _maybe_rag(result, theme_flags, api_key, pdf_bytes)


def _maybe_rag(result, theme_flags, api_key, pdf_bytes):
    if not pdf_bytes:
        return result

    filing_keys = [k for k in ALL_FILING_KEYS if theme_flags.get(k, True)]
    if not filing_keys:
        return result

    try:
        result["steps"].append("Indexing PDF for retrieval…")
        retriever = build_retriever(pdf_bytes, api_key)
        pdf_hash = pdf_fingerprint(pdf_bytes)

        for key in filing_keys:
            result["filing_sources"][key] = retrieve_for_theme(retriever, key)

        result["steps"].append("Writing filing commentary from retrieved chunks…")
        result["filing_insights"] = _batch_filing(filing_keys, result["filing_sources"], api_key)

        ar_key = analysis_cache.annual_report_cache_key(
            pdf_hash,
            [theme_flags.get(k, True) for k in GROUPS["fiscal_year"]],
            [theme_flags.get(k, True) for k in GROUPS["strategy"]],
            [theme_flags.get(k, True) for k in GROUPS["risk"]],
            [theme_flags.get(k, True) for k in GROUPS["innovation"]],
        )
        analysis_cache.save_annual_report_session(ar_key, dict(result["filing_insights"]))
    except Exception as exc:
        result["steps"].append(f"PDF step failed: {exc}")

    return result


def _latest_revenue(income):
    if not income or income.get("Error"):
        return None
    series = (income.get("chart_data") or {}).get("total_revenue") or []
    return safe_float(series[-1]) if series else None


def _total_debt(balance):
    if not balance or balance.get("Error"):
        return None
    ds = (balance.get("chart_data") or {}).get("debt_structure") or {}
    a, b = safe_float(ds.get("short_term_debt")), safe_float(ds.get("long_term_debt"))
    if a == "N/A" or b == "N/A":
        return "N/A"
    return a + b


def _attach_insights(result):
    mapping = (
        ("income", result["income"]),
        ("balance", result["balance"]),
        ("cash", result["cash"]),
    )
    for group, block in mapping:
        if not block or block.get("Error"):
            continue
        block["insights"] = {
            k: result["fundamentals_insights"].get(k, "")
            for k in GROUPS[group]
            if k in result["fundamentals_insights"]
        }


def _theme_spec(keys):
    lines = []
    for k in keys:
        t = THEMES[k]
        lines.append(f"{k}: {t['spec']}")
    return "\n".join(lines)


def _batch_fundamentals(keys, payload, api_key):
    prompt = PromptTemplate(template=FUNDAMENTALS_BATCH_INSIGHT, input_variables=["themes_spec", "payload"])
    text = get_chat_model(api_key).predict(
        prompt.format(themes_spec=_theme_spec(keys), payload=json.dumps(payload, default=str)[:120_000])
    )
    return _parse_json_insights(text, keys)


def _batch_filing(keys, sources, api_key):
    evidence = {k: sources.get(k, []) for k in keys}
    prompt = PromptTemplate(template=FILING_BATCH_INSIGHT, input_variables=["themes_spec", "evidence"])
    text = get_chat_model(api_key).predict(
        prompt.format(themes_spec=_theme_spec(keys), evidence=json.dumps(evidence, default=str)[:120_000])
    )
    return _parse_json_insights(text, keys)


def _parse_json_insights(raw, keys):
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {k: str(data.get(k, "")).strip() for k in keys}
    except json.JSONDecodeError:
        pass
    if len(keys) == 1:
        return {keys[0]: raw}
    return {k: "" for k in keys}
