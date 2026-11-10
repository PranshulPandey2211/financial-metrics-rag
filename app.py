import os

from flask import Flask, flash, redirect, render_template, request, url_for

from src.analysis import run_analysis
from src.helpers import format_currency, format_ratio_as_pct, get_openai_api_key, round_numeric
from src.insight_themes import FILING_GROUPS, FUNDAMENTALS_GROUPS, GROUPS, THEMES, default_theme_flags

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

# In-process only — fine for local use; use cache/ if you need persistence later.
reports = {}


@app.get("/")
def index():
    return render_template(
        "index.html",
        theme_groups=_theme_groups(),
        themes=THEMES,
    )


@app.post("/analyze")
def analyze():
    ticker = (request.form.get("ticker") or "").strip().upper()
    api_key = get_openai_api_key()
    if not api_key:
        flash("Set OPENAI_API_KEY in the environment.", "error")
        return redirect(url_for("index"))

    flags = default_theme_flags()
    for key in flags:
        flags[key] = request.form.get(f"theme_{key}") == "on"

    pdf = request.files.get("annual_report")
    pdf_bytes = pdf.read() if pdf and pdf.filename else None

    out = run_analysis(
        ticker,
        theme_flags=flags,
        api_key=api_key,
        pdf_bytes=pdf_bytes,
        force_refresh=request.form.get("force_refresh") == "on",
    )
    if out.get("error"):
        flash(out["error"], "error")
        return redirect(url_for("index"))

    reports[out["run_id"]] = out
    return redirect(url_for("report", run_id=out["run_id"]))


@app.get("/report/<run_id>")
def report(run_id):
    out = reports.get(run_id)
    if not out:
        flash("That run is gone — start again.", "error")
        return redirect(url_for("index"))
    company = out.get("company") or {}
    news_rows, news_score, news_label = _news_for_template(out.get("news"))
    return render_template(
        "report.html",
        out=out,
        company=company,
        themes=THEMES,
        groups=GROUPS,
        fundamentals_groups=FUNDAMENTALS_GROUPS,
        filing_groups=FILING_GROUPS,
        format_currency=format_currency,
        format_ratio_as_pct=format_ratio_as_pct,
        round_numeric=round_numeric,
        news_rows=news_rows,
        news_sentiment_score=news_score,
        news_sentiment_label=news_label,
    )


def _news_for_template(packet):
    if not packet or packet.get("Error"):
        return [], None, None
    df = packet.get("news")
    if df is None:
        return [], packet.get("mean_sentiment_score"), packet.get("mean_sentiment_class")
    try:
        rows = df.to_dict("records")
    except Exception:
        rows = []
    return rows, packet.get("mean_sentiment_score"), packet.get("mean_sentiment_class")


def _theme_groups():
    rows = []
    for name in (*FUNDAMENTALS_GROUPS, *FILING_GROUPS):
        rows.append((name.replace("_", " ").title(), GROUPS[name]))
    return rows


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
