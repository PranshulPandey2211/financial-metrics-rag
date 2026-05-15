
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from src.helpers import generate_insight, get_total_revenue, get_total_debt, safe_float, statement_error_response
from src.insight_themes import cashflow, cashflow_attributes
from src.yahoo_finance import fetch_cash_flow


def charts(data):
    dates = []
    operating_cash_flow = []
    cash_flow_from_investment = []
    cash_flow_from_financing = []

    for report in reversed(data["annualReports"]):
        dates.append(report["fiscalDateEnding"])
        operating_cash_flow.append(report["operatingCashflow"])
        cash_flow_from_investment.append(report["cashflowFromInvestment"])
        cash_flow_from_financing.append(report["cashflowFromFinancing"])

    return {
        "dates": dates,
        "operating_cash_flow": operating_cash_flow,
        "cash_flow_from_investment": cash_flow_from_investment,
        "cash_flow_from_financing": cash_flow_from_financing
    }
    

def metrics(data, total_revenue, total_debt):
    operatingCashFlow = safe_float(data.get("operatingCashflow"))
    capitalExpenditures = safe_float(data.get("capitalExpenditures"))
    dividendPayout = safe_float(data.get("dividendPayout"))
    netIncome = safe_float(data.get("netIncome"))

    operating_cash_flow_margin = "N/A" if "N/A" in (operatingCashFlow, total_revenue) else operatingCashFlow / total_revenue
    capital_expenditure_coverage_ratio = "N/A" if "N/A" in (operatingCashFlow, capitalExpenditures) else operatingCashFlow / capitalExpenditures
    free_cash_flow = "N/A" if "N/A" in (operatingCashFlow, capitalExpenditures) else operatingCashFlow - capitalExpenditures
    dividend_coverage_ratio = "N/A" if "N/A" in (dividendPayout, netIncome) else netIncome / dividendPayout
    cash_flow_to_debt_ratio = "N/A" if "N/A" in (operatingCashFlow, total_debt) else operatingCashFlow / total_debt

    return {
        "operating_cash_flow_margin": operating_cash_flow_margin,
        "capital_expenditure_coverage_ratio": capital_expenditure_coverage_ratio,
        "free_cash_flow": free_cash_flow,
        "dividend_coverage_ratio": dividend_coverage_ratio,
        "cash_flow_to_debt_ratio": cash_flow_to_debt_ratio
    }


def cash_flow(symbol, fields_to_include, api_key, total_revenue=None, total_debt=None):
    data = fetch_cash_flow(symbol)
    if data.get("Error"):
        return data
    if "annualReports" not in data or not data["annualReports"]:
        return statement_error_response(
            "No cash flow annual reports for this symbol."
        )

    chart_data = charts(data)

    report = data["annualReports"][0]
    if total_revenue is None:
        total_revenue = get_total_revenue(symbol)
    if total_debt is None:
        total_debt = get_total_debt(symbol)
    met = metrics(report, total_revenue, total_debt)

    data_for_insights = {
        "annual_report_data": report,
        "historical_data": chart_data,
    }
    ins = {}
    for i, field in enumerate(cashflow_attributes):
        if fields_to_include[i]:
            ins[field] = generate_insight(
                field,
                "cash flow",
                data_for_insights,
                str({field: cashflow[field]}),
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
    data = cash_flow("AAPL", fields, get_openai_api_key())
    print("Metrics: ", data['metrics'])
    print("Chart Data: ", data['chart_data'])
    print("Insights", data['insights'])