from src.helpers import safe_float, statement_error_response
from src.yahoo_finance import fetch_cash_flow, latest_total_debt, latest_total_revenue


def _chart_data(data):
    dates, ocf, inv, fin = [], [], [], []
    for report in reversed(data["annualReports"]):
        dates.append(report["fiscalDateEnding"])
        ocf.append(report["operatingCashflow"])
        inv.append(report["cashflowFromInvestment"])
        fin.append(report["cashflowFromFinancing"])
    return {
        "dates": dates,
        "operating_cash_flow": ocf,
        "cash_flow_from_investment": inv,
        "cash_flow_from_financing": fin,
    }


def _metrics(report, total_revenue, total_debt):
    ocf = safe_float(report.get("operatingCashflow"))
    capex = safe_float(report.get("capitalExpenditures"))
    div = safe_float(report.get("dividendPayout"))
    net = safe_float(report.get("netIncome"))

    def ratio(num, den):
        if "N/A" in (num, den):
            return "N/A"
        return num / den

    fcf = "N/A" if "N/A" in (ocf, capex) else ocf - capex

    return {
        "operating_cash_flow_margin": ratio(ocf, total_revenue),
        "capital_expenditure_coverage_ratio": ratio(ocf, capex),
        "free_cash_flow": fcf,
        "dividend_coverage_ratio": ratio(net, div),
        "cash_flow_to_debt_ratio": ratio(ocf, total_debt),
    }


def cash_flow(symbol, total_revenue=None, total_debt=None):
    data = fetch_cash_flow(symbol)
    if data.get("Error"):
        return data
    if not data.get("annualReports"):
        return statement_error_response("No cash flow statement for this symbol.")

    chart_data = _chart_data(data)
    report = data["annualReports"][0]
    if total_revenue is None:
        total_revenue = latest_total_revenue(symbol)
    if total_debt is None:
        total_debt = latest_total_debt(symbol)
    return {"metrics": _metrics(report, total_revenue, total_debt), "chart_data": chart_data}
