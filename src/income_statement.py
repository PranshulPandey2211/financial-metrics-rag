from src.helpers import safe_float, statement_error_response
from src.yahoo_finance import fetch_income_statement


def _chart_data(data):
    dates, revenue, net_income, interest = [], [], [], []
    for report in reversed(data["annualReports"]):
        dates.append(report["fiscalDateEnding"])
        revenue.append(report["totalRevenue"])
        net_income.append(report["netIncome"])
        interest.append(report["interestAndDebtExpense"])
    return {
        "dates": dates,
        "total_revenue": revenue,
        "net_income": net_income,
        "interest_expense": interest,
    }


def _metrics(report):
    gross = safe_float(report.get("grossProfit"))
    revenue = safe_float(report.get("totalRevenue"))
    op_inc = safe_float(report.get("operatingIncome"))
    net = safe_float(report["netIncome"])
    ebit = safe_float(report.get("ebit"))
    interest = safe_float(report.get("interestAndDebtExpense"))

    def ratio(num, den):
        if "N/A" in (num, den):
            return "N/A"
        return num / den

    return {
        "gross_profit_margin": ratio(gross, revenue),
        "operating_profit_margin": ratio(op_inc, revenue),
        "net_profit_margin": ratio(net, revenue),
        "interest_coverage_ratio": ratio(ebit, interest),
    }


def income_statement(symbol):
    data = fetch_income_statement(symbol)
    if data.get("Error"):
        return data
    if not data.get("annualReports"):
        return statement_error_response("No income statement for this symbol.")

    chart_data = _chart_data(data)
    report = data["annualReports"][0]
    return {"metrics": _metrics(report), "chart_data": chart_data}
