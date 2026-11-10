from src.helpers import safe_float, statement_error_response
from src.yahoo_finance import fetch_balance_sheet, latest_total_revenue


def _chart_data(data):
    report = data["annualReports"][0]
    return {
        "asset_composition": {
            "total_current_assets": report["totalCurrentAssets"],
            "total_non_current_assets": report["totalNonCurrentAssets"],
        },
        "liabilities_composition": {
            "total_current_liabilities": report["totalCurrentLiabilities"],
            "total_non_current_liabilities": report["totalNonCurrentLiabilities"],
        },
        "debt_structure": {
            "short_term_debt": report["shortTermDebt"],
            "long_term_debt": report["longTermDebt"],
        },
    }


def _metrics(report, total_revenue):
    ca = safe_float(report.get("totalCurrentAssets"))
    cl = safe_float(report.get("totalCurrentLiabilities"))
    liab = safe_float(report.get("totalLiabilities"))
    equity = safe_float(report.get("totalShareholderEquity"))
    assets = safe_float(report.get("totalAssets"))
    inventory = safe_float(report.get("inventory"))

    def ratio(num, den):
        if "N/A" in (num, den):
            return "N/A"
        return num / den

    quick_num = "N/A" if ca == "N/A" or cl == "N/A" or inventory == "N/A" else ca - inventory

    return {
        "current_ratio": ratio(ca, cl),
        "debt_to_equity_ratio": ratio(liab, equity),
        "quick_ratio": ratio(quick_num, cl),
        "asset_turnover": ratio(total_revenue, assets),
        "equity_multiplier": ratio(assets, equity),
    }


def balance_sheet(symbol, total_revenue=None):
    data = fetch_balance_sheet(symbol)
    if data.get("Error"):
        return data
    if not data.get("annualReports"):
        return statement_error_response("No balance sheet for this symbol.")

    chart_data = _chart_data(data)
    report = data["annualReports"][0]
    if total_revenue is None:
        total_revenue = latest_total_revenue(symbol)
    return {"metrics": _metrics(report, total_revenue), "chart_data": chart_data}
