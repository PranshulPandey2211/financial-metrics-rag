import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

import os

from src.insight_themes import inc_stat, inc_stat_attributes
from src.yahoo_finance import fetch_income_statement
from src.helpers import generate_insight, safe_float, statement_error_response

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def charts(data):
    dates = []
    total_revenue = []
    net_income = []
    interest_expense = []

    for report in reversed(data["annualReports"]):
        dates.append(report["fiscalDateEnding"])
        total_revenue.append(report["totalRevenue"])
        net_income.append(report["netIncome"])
        interest_expense.append(report["interestAndDebtExpense"])

    return {
        "dates": dates,
        "total_revenue": total_revenue,
        "net_income": net_income,
        "interest_expense": interest_expense
    }


def metrics(data):
    grossProfit = safe_float(data.get("grossProfit"))
    totalRevenue = safe_float(data.get("totalRevenue"))
    operatingIncome = safe_float(data.get("operatingIncome"))
    costOfRevenue = safe_float(data.get("costOfRevenue"))
    costofGoodsAndServicesSold = safe_float(data.get("costofGoodsAndServicesSold"))
    sellingGeneralAndAdministrative = safe_float(data.get("sellingGeneralAndAdministrative"))
    ebit = safe_float(data.get("ebit"))
    interestAndDebtExpense = safe_float(data.get("interestAndDebtExpense"))
    netIncome = safe_float(data["netIncome"])

    gross_profit_margin = (
        "N/A" if "N/A" in (grossProfit, totalRevenue) else grossProfit / totalRevenue
    )
    operating_profit_margin = (
        "N/A" if "N/A" in (operatingIncome, totalRevenue) else operatingIncome / totalRevenue
    )
    net_profit_margin = (
        "N/A" if "N/A" in (netIncome, totalRevenue) else netIncome / totalRevenue
    )
    cost_efficiency = (
        "N/A"
        if "N/A" in (totalRevenue, costOfRevenue, costofGoodsAndServicesSold)
        else totalRevenue / (costOfRevenue + costofGoodsAndServicesSold)
    )
    sg_and_a_efficiency = (
        "N/A"
        if "N/A" in (totalRevenue, sellingGeneralAndAdministrative)
        else totalRevenue / sellingGeneralAndAdministrative
    )
    interest_coverage_ratio = (
        "N/A" if "N/A" in (ebit, interestAndDebtExpense) else ebit / interestAndDebtExpense
    )

    return {
        "gross_profit_margin": gross_profit_margin,
        "operating_profit_margin": operating_profit_margin,
        "net_profit_margin": net_profit_margin,
        "cost_efficiency": cost_efficiency,
        "sg_and_a_efficiency": sg_and_a_efficiency,
        "interest_coverage_ratio": interest_coverage_ratio,
    }



def income_statement(symbol, fields_to_include, api_key):
    data = fetch_income_statement(symbol)
    if data.get("Error"):
        return data
    if "annualReports" not in data or not data["annualReports"]:
        return statement_error_response(
            "No income statement annual reports for this symbol."
        )

    chart_data = charts(data)

    report = data["annualReports"][0]
    met = metrics(report)

    data_for_insights = {
        "annual_report_data": report,
        "historical_data": chart_data,
    }

    ins = {}
    for i, field in enumerate(inc_stat_attributes):
        if fields_to_include[i]:
            ins[field] = generate_insight(
                field,
                "income statement",
                data_for_insights,
                str({field: inc_stat[field]}),
                api_key,
            )

    return {
        "metrics": met,
        "chart_data": chart_data,
        "insights": ins,
    }


if __name__ == "__main__":
    from src.helpers import get_openai_api_key

    fields_to_include = [True, False, False, False, True]

    data = income_statement("TSLA", fields_to_include, get_openai_api_key())
    print("Metrics: ", data['metrics'])
    print("Chart Data: ", data['chart_data'])
    print("Insights", data['insights'])


