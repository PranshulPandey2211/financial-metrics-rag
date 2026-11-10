import hashlib
import json
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
_CACHE_ROOT = _ROOT / "cache" / "reports"


def cache_key(ticker, income_flags, balance_flags, cash_flags):
    blob = json.dumps(
        {
            "ticker": ticker.strip().upper(),
            "income": income_flags,
            "balance": balance_flags,
            "cash": cash_flags,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]
    return f"{ticker.strip().upper()}_{digest}"


def _dir(key):
    return _CACHE_ROOT / key


def has_saved_report(key):
    d = _dir(key)
    return d.is_dir() and (d / "meta.json").is_file() and (d / "company.json").is_file()


def save_report(
    key,
    *,
    company_overview=None,
    income_statement=None,
    balance_sheet=None,
    cash_flow=None,
    news=None,
):
    d = _dir(key)
    d.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        if obj is None:
            return
        with open(d / name, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, default=str)

    meta = {"cache_key": key}
    with open(d / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    dump("company.json", company_overview)
    dump("income.json", income_statement)
    dump("balance.json", balance_sheet)
    dump("cash.json", cash_flow)

    if news and "Error" not in news and "news" in news:
        news_df = news["news"]
        news_df.to_csv(d / "news.csv", index=False)
        side = {
            "mean_sentiment_score": float(news["mean_sentiment_score"])
            if news.get("mean_sentiment_score") is not None
            and not (
                isinstance(news["mean_sentiment_score"], float)
                and pd.isna(news["mean_sentiment_score"])
            )
            else None,
            "mean_sentiment_class": news.get("mean_sentiment_class"),
        }
        with open(d / "news_meta.json", "w", encoding="utf-8") as f:
            json.dump(side, f, indent=2)


def load_report(key):
    if not has_saved_report(key):
        return None
    d = _dir(key)
    out = {}

    def load_json(name):
        p = d / name
        if not p.is_file():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    out["company_overview"] = load_json("company.json")
    out["income_statement"] = load_json("income.json")
    out["balance_sheet"] = load_json("balance.json")
    out["cash_flow"] = load_json("cash.json")

    news_csv = d / "news.csv"
    news_meta = d / "news_meta.json"
    if news_csv.is_file() and news_meta.is_file():
        df = pd.read_csv(news_csv)
        with open(news_meta, "r", encoding="utf-8") as f:
            meta = json.load(f)
        score = meta.get("mean_sentiment_score")
        if score is not None:
            score = float(score)
        out["news"] = {
            "news": df,
            "mean_sentiment_score": score,
            "mean_sentiment_class": meta.get("mean_sentiment_class"),
        }
    else:
        out["news"] = None

    return out


_AR_ROOT = _ROOT / "cache" / "annual_reports"


def annual_report_cache_key(pdf_hash, fiscal, strat, risk, innov):
    blob = json.dumps(
        {
            "pdf": pdf_hash,
            "fiscal": fiscal,
            "strat": strat,
            "risk": risk,
            "innov": innov,
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _annual_path(key):
    return _AR_ROOT / f"{key}.json"


def has_annual_report(key):
    return _annual_path(key).is_file()


def save_annual_report_session(key, snapshot):
    _AR_ROOT.mkdir(parents=True, exist_ok=True)
    with open(_annual_path(key), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)


def load_annual_report_session(key):
    p = _annual_path(key)
    if not p.is_file():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
