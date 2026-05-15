import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from src.insight_themes import bal_sheet, balance_sheet_attributes
from src.helpers import generate_insight, get_total_revenue, safe_float, statement_error_response
from src.yahoo_finance import fetch_balance_sheet


def charts(data):
    report = data['annualReports'][0]
    asset_composition = {"total_current_assets": report['totalCurrentAssets'],
        "total_non_current_assets": report['totalNonCurrentAssets']              
    }

    liabilities_composition = {
        "total_current_liabilities": report['totalCurrentLiabilities'],
        "total_non_current_liabilities": report['totalNonCurrentLiabilities']
    }

    debt_structure = {
        "short_term_debt": report['shortTermDebt'],
        "long_term_debt": report['longTermDebt']
    }

    return {
        "asset_composition": asset_composition,
        "liabilities_composition": liabilities_composition,
        "debt_structure": debt_structure
    }

         

def metrics(data, total_revenue):
    totalCurrentAssets = safe_float(data.get("totalCurrentAssets"))
    totalCurrentLiabilities = safe_float(data.get("totalCurrentLiabilities"))
    totalLiabilities = safe_float(data.get("totalLiabilities"))
    totalShareholderEquity = safe_float(data.get("totalShareholderEquity"))
    totalAssets = safe_float(data.get("totalAssets"))
    inventory = safe_float(data.get("inventory"))

    current_ratio = (
        "N/A"
        if "N/A" in (totalCurrentAssets, totalCurrentLiabilities)
        else totalCurrentAssets / totalCurrentLiabilities
    )
    debt_to_equity_ratio = (
        "N/A"
        if "N/A" in (totalLiabilities, totalShareholderEquity)
        else totalLiabilities / totalShareholderEquity
    )
    quick_ratio = (
        "N/A"
        if "N/A" in (totalCurrentAssets, totalCurrentLiabilities, inventory)
        else (totalCurrentAssets - inventory) / totalCurrentLiabilities
    )
    asset_turnover = (
        "N/A" if "N/A" in (total_revenue, totalAssets) else total_revenue / totalAssets
    )
    equity_multiplier = (
        "N/A"
        if "N/A" in (totalAssets, totalShareholderEquity)
        else totalAssets / totalShareholderEquity
    )

    return {
        "current_ratio": current_ratio,
        "debt_to_equity_ratio": debt_to_equity_ratio,
        "quick_ratio": quick_ratio,
        "asset_turnover": asset_turnover,
        "equity_multiplier": equity_multiplier,
    }


def balance_sheet(symbol, fields_to_include, api_key, total_revenue=None):
    data = fetch_balance_sheet(symbol)
    if data.get("Error"):
        return data
    if "annualReports" not in data or not data["annualReports"]:
        return statement_error_response(
            "No balance sheet annual reports for this symbol."
        )

    chart_data = charts(data)

    report = data["annualReports"][0]
    if total_revenue is None:
        total_revenue = get_total_revenue(symbol)
    met = metrics(report, total_revenue)

    data_for_insights = {
        "annual_report_data": report,
        "historical_data": chart_data,
    }

    ins = {}
    for i, field in enumerate(balance_sheet_attributes):
        if fields_to_include[i]:
            ins[field] = generate_insight(
                field,
                "balance sheet",
                data_for_insights,
                str({field: bal_sheet[field]}),
                api_key,
            )

    return {
        "metrics": met,
        "chart_data": chart_data,
        "insights": ins
    }

if __name__ == "__main__":
    from src.helpers import get_openai_api_key

    fields = [True, True, False, False, False]
    data = balance_sheet("MSFT", fields, get_openai_api_key())
    print("Metrics: ", data['metrics'])
    print("Chart Data: ", data['chart_data'])
    print("Insights", data['insights'])


