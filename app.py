import streamlit as st

from src.app_theme import apply_theme, ensure_project_root, page_config

ensure_project_root()
page_config(title="FinAnalytica")

apply_theme()

st.markdown("### FinAnalytica")
st.caption("AI-powered financial analysis — fundamentals, commentary, and annual-report RAG.")
section = st.radio(
    "Section",
    ["Financial Metrics", "Annual Report Analyzer"],
    horizontal=True,
    label_visibility="collapsed",
    key="finanalytica_section",
)
st.divider()

if section == "Financial Metrics":
    from src.financial_metrics import run as run_financial_metrics

    run_financial_metrics()
else:
    from src.annual_report_analyzer import run as run_annual_report

    run_annual_report()
