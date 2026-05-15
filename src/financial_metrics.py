import streamlit as st

from src import analysis_cache
from src.yahoo_finance import resolve_ticker, _has_financials
from src.balance_sheet import balance_sheet
from src.cash_flow import cash_flow
from src.company_profile import company_overview
from src.insight_themes import balance_sheet_attributes, cashflow_attributes, inc_stat_attributes
from src.income_statement import income_statement
from src.company_news import top_news
from src.app_theme import insight_card, panel_section, section_label, tab_heading
from src.helpers import (
    api_error_message,
    create_bar_chart,
    create_donut_chart,
    format_currency,
    get_openai_api_key,
    round_numeric,
    safe_float,
    statement_error_response,
)


def _statement_failed(data):
    return not data or bool(data.get("Error"))


def _bundle_ready(co, inc_s, bal_s, cf_s, nw, inc_t, bal_t, cf_t):
    if not co or "Error" in co:
        return False
    if any(inc_t) and (not inc_s or "Error" in inc_s):
        return False
    if any(bal_t) and (not bal_s or "Error" in bal_s):
        return False
    if any(cf_t) and (not cf_s or "Error" in cf_s):
        return False
    return True


def _income_toggles():
    return {k: st.session_state.get(f"t_{k}", True) for k in inc_stat_attributes}


def _balance_toggles():
    return {k: st.session_state.get(f"t_{k}", True) for k in balance_sheet_attributes}


def _cash_toggles():
    return {k: st.session_state.get(f"t_{k}", True) for k in cashflow_attributes}


def _flag_list(toggles, keys):
    return [toggles[k] for k in keys]


def _revenue_from_income(data):
    if not data or "Error" in data:
        return None
    revs = data.get("chart_data", {}).get("total_revenue") or []
    if not revs:
        return None
    return safe_float(revs[-1])


def _debt_from_balance(data):
    if not data or "Error" in data:
        return None
    ds = data.get("chart_data", {}).get("debt_structure") or {}
    st_d = safe_float(ds.get("short_term_debt"))
    lt = safe_float(ds.get("long_term_debt"))
    if st_d == "N/A" or lt == "N/A":
        return "N/A"
    return st_d + lt


def _tab_error(tab, data, empty_msg):
    with tab:
        if not data:
            st.info(empty_msg)
            return True
        if "Error" in data:
            st.error(api_error_message(data))
            return True
    return False


def _metrics_grid(tab, rows):
    with tab:
        section_label("Key metrics")
        for row in rows:
            cols = st.columns(len(row))
            for col, (label, val) in zip(cols, row):
                col.metric(label, val)


def _insight_blocks(tab, blocks, toggles, chart_data, chart_fn):
    with tab:
        section_label("AI commentary")
        shown = False
        for key, title, chart_key in blocks:
            if not toggles.get(key):
                continue
            shown = True
            text = st.session_state.get(key)
            insight_card(title, text, empty_hint="Commentary not generated for this theme.")
            if text and chart_key and chart_data:
                st.plotly_chart(
                    chart_fn(chart_data, chart_key, title),
                    use_container_width=True,
                )
        if not shown:
            st.caption("No themes selected for this section — enable themes in **Analysis setup** above.")


def _render_overview(tab, data):
    with tab:
        tab_heading("Company overview")
        if not data:
            st.info("Run **Generate analysis** using the controls above.")
            return
        if "Error" in data:
            st.error(api_error_message(data))
            return
        st.markdown(f"### {data.get('Name', 'Company')}")
        section_label("Profile")
        c1, c2, c3 = st.columns(3)
        c1.metric("Symbol", data.get("Symbol", "—"))
        c2.metric("Exchange", data.get("Exchange", "—"))
        c3.metric("Currency", data.get("Currency", "—"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Sector", data.get("Sector", "—"))
        c2.metric("Industry", data.get("Industry", "—"))
        c3.metric("Market cap", format_currency(data.get("MarketCapitalization", "N/A")))
        with st.expander("Business description", expanded=False):
            st.write(data.get("Description", ""))


def _render_statement_tab(
    tab,
    title,
    data,
    empty_msg,
    metric_rows,
    insight_blocks_spec,
    toggles,
    chart_data_key,
    use_donut=False,
):
    with tab:
        tab_heading(title)
    if _tab_error(tab, data, empty_msg):
        return
    if not data or "Error" in data:
        return
    _metrics_grid(tab, metric_rows)
    chart = data.get(chart_data_key, {})
    fn = create_donut_chart if use_donut else create_bar_chart
    _insight_blocks(tab, insight_blocks_spec, toggles, chart, fn)


def _render_news(tab, data, ticker=""):
    with tab:
        tab_heading("News")
        if not data:
            st.info("News not loaded yet. Run **Generate analysis**.")
            return
        if "Error" in data:
            st.error(api_error_message(data))
            return
        df = data.get("news")
        if df is None or (hasattr(df, "empty") and df.empty):
            st.info("No headlines returned for this ticker.")
            return
        section_label("Sentiment summary")
        mean_score = data.get("mean_sentiment_score")
        st.metric(
            "Mean sentiment score",
            round_numeric(mean_score, 3) if mean_score is not None else "N/A",
            delta=data.get("mean_sentiment_class"),
        )
        section_label("Recent headlines")
        show = df.copy()
        if "publisher" in show.columns:
            show = show.rename(columns={"publisher": "source"})
        display_cols = [
            c
            for c in (
                "title",
                "source",
                "published",
                "sentiment_score",
                "sentiment_label",
                "url",
            )
            if c in show.columns
        ]
        show = show[display_cols] if display_cols else show
        st.caption("Sentiment scored from headline text (VADER). Refresh with **Force fresh fetch**.")
        st.dataframe(show, use_container_width=True, hide_index=True)


def run():
    openai_key = get_openai_api_key()
    if not openai_key:
        st.warning("Add `openai_api_key` to `.streamlit/secrets.toml` or set the OPENAI_API_KEY environment variable.")
        return

    panel_section("Analysis setup")
    ticker = st.text_input(
        "Ticker",
        placeholder="AAPL",
        key="fm_ticker",
        help="US symbols only, e.g. AAPL (Apple), MSFT, TSLA — not APPL",
    ).strip().upper()
    force_refresh = st.checkbox("Force fresh fetch", value=False)

    with st.expander("Income statement themes", expanded=False):
        for label, key in [
            ("Revenue health", "revenue_health"),
            ("Operational efficiency", "operational_efficiency"),
            ("R&D focus", "r_and_d_focus"),
            ("Debt management", "debt_management"),
            ("Profit retention", "profit_retention"),
        ]:
            st.toggle(label, value=True, key=f"t_{key}")

    with st.expander("Balance sheet themes", expanded=False):
        for label, key in [
            ("Liquidity", "liquidity_position"),
            ("Asset efficiency", "assets_efficiency"),
            ("Capital structure", "capital_structure"),
            ("Inventory", "inventory_management"),
            ("Solvency", "overall_solvency"),
        ]:
            st.toggle(label, value=True, key=f"t_{key}")

    with st.expander("Cash flow themes", expanded=False):
        for label, key in [
            ("Operating cash", "operational_cash_efficiency"),
            ("Investments", "investment_capability"),
            ("Flexibility", "financial_flexibility"),
            ("Dividends", "dividend_sustainability"),
            ("Debt service", "debt_service_capability"),
        ]:
            st.toggle(label, value=True, key=f"t_{key}")

    run_clicked = st.button("Generate analysis", type="primary", use_container_width=True)
    st.divider()

    inc_toggles = _income_toggles()
    bal_toggles = _balance_toggles()
    cash_toggles = _cash_toggles()
    inc_flags = _flag_list(inc_toggles, list(inc_stat_attributes))
    bal_flags = _flag_list(bal_toggles, list(balance_sheet_attributes))
    cf_flags = _flag_list(cash_toggles, list(cashflow_attributes))

    for key in inc_stat_attributes + balance_sheet_attributes + cashflow_attributes:
        st.session_state.setdefault(key, None)
    for field in ("company_overview", "income_statement", "balance_sheet", "cash_flow", "news", "fm_has_results"):
        st.session_state.setdefault(field, None)
    st.session_state.setdefault("fm_active_ticker", None)

    if ticker and ticker != st.session_state.fm_active_ticker:
        st.session_state.fm_active_ticker = ticker
        for f in ("company_overview", "income_statement", "balance_sheet", "cash_flow", "news"):
            st.session_state[f] = None
        st.session_state.fm_has_results = False

    if run_clicked and ticker:
        resolved, ticker_note = resolve_ticker(ticker)
        if not _has_financials(resolved):
            st.error(
                ticker_note
                or f"**{ticker}** has no financial data. For Apple use **AAPL** (not APPL)."
            )
            return
        if ticker_note:
            st.info(ticker_note)
        ticker = resolved

        cache_key = analysis_cache.cache_key(ticker, inc_flags, bal_flags, cf_flags)
        use_cache = (not force_refresh) and analysis_cache.has_saved_report(cache_key)

        if use_cache:
            bundle = analysis_cache.load_report(cache_key)
            cached_news = bundle.get("news") if bundle else None
            news_stale = False
            if cached_news and "news" in cached_news:
                df = cached_news["news"]
                if hasattr(df, "empty") and df.empty:
                    news_stale = True
                elif "title" in df.columns and df["title"].astype(str).str.strip().eq("").all():
                    news_stale = True
                elif (
                    "sentiment_score" in df.columns
                    and (df["sentiment_score"] == 0).all()
                    and "sentiment_label" in df.columns
                    and (df["sentiment_label"] == "Neutral").all()
                ):
                    news_stale = True

            if bundle and bundle.get("company_overview") and not news_stale:
                st.session_state.company_overview = bundle["company_overview"]
                st.session_state.income_statement = bundle.get("income_statement")
                st.session_state.balance_sheet = bundle.get("balance_sheet")
                st.session_state.cash_flow = bundle.get("cash_flow")
                st.session_state.news = cached_news
                analysis_cache.apply_insights_to_session(bundle)
                st.session_state.fm_has_results = True
                st.success("Loaded saved analysis (no new API calls).")
            else:
                use_cache = False
                if news_stale:
                    st.info("Refreshing news (cached headlines were empty).")

        if not use_cache:
            with st.status("Fetching market data…", expanded=True):
                for k in inc_stat_attributes + balance_sheet_attributes + cashflow_attributes:
                    st.session_state[k] = None

                st.write("1/5 — Company overview")
                st.session_state.company_overview = company_overview(ticker)

                cached_revenue = None
                cached_debt = None

                if any(inc_flags):
                    st.write("2/5 — Income statement")
                    try:
                        st.session_state.income_statement = income_statement(
                            ticker, inc_flags, openai_key
                        )
                    except Exception as exc:
                        st.session_state.income_statement = statement_error_response(str(exc))
                    for k, v in (st.session_state.income_statement or {}).get("insights", {}).items():
                        st.session_state[k] = v
                    cached_revenue = _revenue_from_income(st.session_state.income_statement)
                else:
                    st.session_state.income_statement = None

                if any(bal_flags):
                    st.write("3/5 — Balance sheet")
                    try:
                        st.session_state.balance_sheet = balance_sheet(
                            ticker, bal_flags, openai_key, total_revenue=cached_revenue
                        )
                    except Exception as exc:
                        st.session_state.balance_sheet = statement_error_response(str(exc))
                    for k, v in (st.session_state.balance_sheet or {}).get("insights", {}).items():
                        st.session_state[k] = v
                    cached_debt = _debt_from_balance(st.session_state.balance_sheet)
                else:
                    st.session_state.balance_sheet = None

                if any(cf_flags):
                    st.write("4/5 — Cash flow")
                    try:
                        st.session_state.cash_flow = cash_flow(
                            ticker,
                            cf_flags,
                            openai_key,
                            total_revenue=cached_revenue,
                            total_debt=cached_debt,
                        )
                    except Exception as exc:
                        st.session_state.cash_flow = statement_error_response(str(exc))
                    for k, v in (st.session_state.cash_flow or {}).get("insights", {}).items():
                        st.session_state[k] = v
                else:
                    st.session_state.cash_flow = None

                st.write("5/5 — News")
                st.session_state.news = top_news(ticker, 10)

            st.session_state.fm_has_results = True
            st.session_state.fm_active_ticker = ticker

            failed = []
            if any(inc_flags) and _statement_failed(st.session_state.income_statement):
                failed.append("Income statement")
            if any(bal_flags) and _statement_failed(st.session_state.balance_sheet):
                failed.append("Balance sheet")
            if any(cf_flags) and _statement_failed(st.session_state.cash_flow):
                failed.append("Cash flow")

            if _bundle_ready(
                st.session_state.company_overview,
                st.session_state.income_statement,
                st.session_state.balance_sheet,
                st.session_state.cash_flow,
                st.session_state.news,
                inc_flags,
                bal_flags,
                cf_flags,
            ):
                analysis_cache.save_report(
                    cache_key,
                    company_overview=st.session_state.company_overview,
                    income_statement=st.session_state.income_statement,
                    balance_sheet=st.session_state.balance_sheet,
                    cash_flow=st.session_state.cash_flow,
                    news=st.session_state.news,
                )
                st.success("Analysis complete and saved for reuse.")
            elif failed:
                st.warning(
                    "Could not load: **" + ", ".join(failed) + "**. Check those tabs for details."
                )
            else:
                st.warning("Some sections could not be loaded. Check each tab.")

    if st.session_state.get("fm_has_results"):
        co = st.session_state.company_overview or {}
        st.subheader(co.get("Name") or st.session_state.fm_active_ticker or "Analysis")

        tab_ov, tab_inc, tab_bal, tab_cf, tab_news = st.tabs(
            ["Overview", "Income statement", "Balance sheet", "Cash flow", "News"]
        )

        _render_overview(tab_ov, st.session_state.company_overview)

        inc = st.session_state.income_statement
        m = (inc or {}).get("metrics", {})
        _render_statement_tab(
            tab_inc,
            "Income statement",
            inc,
            "Income statement not loaded.",
            [
                [
                    ("Gross margin", round_numeric(m.get("gross_profit_margin"), 2)),
                    ("Operating margin", round_numeric(m.get("operating_profit_margin"), 2)),
                    ("Net margin", round_numeric(m.get("net_profit_margin"), 2)),
                ],
                [
                    ("Cost efficiency", round_numeric(m.get("cost_efficiency"), 2)),
                    ("SG&A efficiency", round_numeric(m.get("sg_and_a_efficiency"), 2)),
                    ("Interest coverage", round_numeric(m.get("interest_coverage_ratio"), 2)),
                ],
            ],
            [
                ("revenue_health", "Revenue health", "total_revenue"),
                ("operational_efficiency", "Operational efficiency", None),
                ("r_and_d_focus", "R&D focus", None),
                ("debt_management", "Debt management", "interest_expense"),
                ("profit_retention", "Profit retention", "net_income"),
            ],
            inc_toggles,
            "chart_data",
        )

        bal = st.session_state.balance_sheet
        bm = (bal or {}).get("metrics", {})
        _render_statement_tab(
            tab_bal,
            "Balance sheet",
            bal,
            "Balance sheet not loaded.",
            [
                [
                    ("Current ratio", round_numeric(bm.get("current_ratio"), 2)),
                    ("Debt / equity", round_numeric(bm.get("debt_to_equity_ratio"), 2)),
                    ("Quick ratio", round_numeric(bm.get("quick_ratio"), 2)),
                ],
                [
                    ("Asset turnover", round_numeric(bm.get("asset_turnover"), 2)),
                    ("Equity multiplier", round_numeric(bm.get("equity_multiplier"), 2)),
                ],
            ],
            [
                ("liquidity_position", "Liquidity", "asset_composition"),
                ("assets_efficiency", "Asset efficiency", None),
                ("capital_structure", "Capital structure", "liabilities_composition"),
                ("inventory_management", "Inventory", None),
                ("overall_solvency", "Solvency", "debt_structure"),
            ],
            bal_toggles,
            "chart_data",
            use_donut=True,
        )

        cf = st.session_state.cash_flow
        cm = (cf or {}).get("metrics", {})
        _render_statement_tab(
            tab_cf,
            "Cash flow",
            cf,
            "Cash flow not loaded.",
            [
                [
                    ("OCF margin", round_numeric(cm.get("operating_cash_flow_margin"), 2)),
                    ("CapEx coverage", round_numeric(cm.get("capital_expenditure_coverage_ratio"), 2)),
                    ("Dividend coverage", round_numeric(cm.get("dividend_coverage_ratio"), 2)),
                ],
                [
                    ("CF / debt", round_numeric(cm.get("cash_flow_to_debt_ratio"), 2)),
                    ("Free cash flow", format_currency(cm.get("free_cash_flow"))),
                ],
            ],
            [
                ("operational_cash_efficiency", "Operating cash", "operating_cash_flow"),
                ("investment_capability", "Investments", "cash_flow_from_investment"),
                ("financial_flexibility", "Financing cash", "cash_flow_from_financing"),
                ("dividend_sustainability", "Dividends", None),
                ("debt_service_capability", "Debt service", None),
            ],
            cash_toggles,
            "chart_data",
        )

        _render_news(
            tab_news,
            st.session_state.news,
            st.session_state.get("fm_active_ticker") or "",
        )

    elif not ticker:
        st.info("Enter a ticker above, then click **Generate analysis**.")
    else:
        st.info(f"Ready to analyze **{ticker}**.")
