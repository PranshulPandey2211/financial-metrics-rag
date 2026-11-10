from src.helpers import safe_float
from src.yahoo_finance import fetch_overview


def company_overview(symbol):
    data = fetch_overview(symbol)
    if data.get("Error"):
        return data
    cap = data.get("MarketCapitalization")
    if cap not in (None, "None"):
        data["MarketCapitalization"] = safe_float(cap)
    return data
