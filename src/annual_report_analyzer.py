import hashlib
import time

import faiss
import streamlit as st
from langchain.prompts import PromptTemplate
from llama_index import ServiceContext, StorageContext, VectorStoreIndex
from llama_index.node_parser import UnstructuredElementNodeParser
from llama_index.query_engine import SubQuestionQueryEngine
from llama_index.schema import Document
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.vector_stores import FaissVectorStore
from pypdf import PdfReader

from src import analysis_cache
from src.insight_themes import (
    fiscal_year,
    fiscal_year_attributes,
    innovation,
    innovation_attributes,
    risk_management,
    risk_management_attributes,
    strat_outlook,
    strat_outlook_attributes,
)
from src.app_theme import insight_card, panel_section, section_label, tab_heading
from src.helpers import get_model, get_openai_api_key
from src.llm_prompts import ANNUAL_REPORT_INSIGHT

_AR_INSIGHT_KEYS = (
    list(fiscal_year_attributes)
    + list(strat_outlook_attributes)
    + list(risk_management_attributes)
    + list(innovation_attributes)
)

_INSIGHT_TITLES = {
    "performance_highlights": "Performance highlights",
    "major_events": "Major events",
    "challenges_encountered": "Challenges encountered",
    "strategic_initiatives": "Strategic initiatives",
    "market_outlook": "Market outlook",
    "product_roadmap": "Product roadmap",
    "risk_factors": "Risk factors",
    "risk_mitigation": "Risk mitigation",
    "r_and_d_activities": "R&D activities",
    "innovation_focus": "Innovation focus",
}


def _process_pdf(pdf):
    file = PdfReader(pdf)
    documents = [Document(text=str(page.extract_text())) for page in file.pages]
    parser = UnstructuredElementNodeParser()
    return parser.get_nodes_from_documents(documents, show_progress=True)


def _get_vector_index(nodes, openai_key):
    llm = get_model("openai", openai_key)
    d = 1536
    faiss_index = faiss.IndexFlatL2(d)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    service_context = ServiceContext.from_defaults(llm=llm)
    return VectorStoreIndex(
        nodes,
        service_context=service_context,
        storage_context=storage_context,
    )


def _generate_insight(engine, insight_name, section_name, output_format):
    template = ANNUAL_REPORT_INSIGHT
    prompt_template = PromptTemplate(
        template=template,
        input_variables=["insight_name", "section_name", "output_format"],
    )
    formatted = prompt_template.format(
        insight_name=insight_name,
        section_name=section_name,
        output_format=output_format,
    )
    return engine.query(formatted).response


def _report_insights(engine, section_name, fields_to_include, section_num):
    if section_num == 1:
        fields, attribs = fiscal_year, fiscal_year_attributes
    elif section_num == 2:
        fields, attribs = strat_outlook, strat_outlook_attributes
    elif section_num == 3:
        fields, attribs = risk_management, risk_management_attributes
    else:
        fields, attribs = innovation, innovation_attributes

    ins = {}
    for i, field in enumerate(attribs):
        if fields_to_include[i]:
            ins[field] = _generate_insight(
                engine, field, section_name, str({field: fields[field]})
            )
    return {"insights": ins}


def _get_query_engine(base_engine, openai_key):
    llm = get_model("openai", openai_key)
    service_context = ServiceContext.from_defaults(llm=llm)
    tools = [
        QueryEngineTool(
            query_engine=base_engine,
            metadata=ToolMetadata(
                name="Annual Report",
                description="Information about the company from its annual report.",
            ),
        ),
    ]
    return SubQuestionQueryEngine.from_defaults(
        query_engine_tools=tools,
        service_context=service_context,
    )


def _render_insight_tab(tab, heading, keys, toggles):
    with tab:
        tab_heading(heading)
        section_label("Insights")
        any_on = False
        for key in keys:
            if not toggles.get(key):
                continue
            any_on = True
            title = _INSIGHT_TITLES.get(key, key.replace("_", " ").title())
            insight_card(title, st.session_state.get(key))
        if not any_on:
            st.caption("Enable themes under **Insight themes** above to see insights here.")


def run():
    for key in _AR_INSIGHT_KEYS:
        st.session_state.setdefault(key, None)
    st.session_state.setdefault("end_time", None)
    st.session_state.setdefault("process_doc", False)
    st.session_state.setdefault("ar_has_results", False)

    openai_key = get_openai_api_key()
    if not openai_key:
        st.warning("Add `openai_api_key` to `.streamlit/secrets.toml` or set the OPENAI_API_KEY environment variable.")
        return

    panel_section("Document")
    pdf_file = st.file_uploader("Annual report (PDF)", type="pdf", key="ar_pdf")
    st.caption("Use a 10-K or full annual report for best results.")
    process_clicked = st.button("Process document", use_container_width=True)

    panel_section("Insight themes")
    with st.expander("Fiscal year highlights", expanded=False):
        t_perf = st.toggle("Performance highlights", value=True, key="ar_t_perf")
        t_events = st.toggle("Major events", value=True, key="ar_t_events")
        t_chal = st.toggle("Challenges encountered", value=True, key="ar_t_chal")
    with st.expander("Strategy outlook", expanded=False):
        t_strat = st.toggle("Strategic initiatives", value=True, key="ar_t_strat")
        t_market = st.toggle("Market outlook", value=True, key="ar_t_market")
        t_road = st.toggle("Product roadmap", value=True, key="ar_t_road")
    with st.expander("Risk management", expanded=False):
        t_risk = st.toggle("Risk factors", value=True, key="ar_t_risk")
        t_mit = st.toggle("Risk mitigation", value=True, key="ar_t_mit")
    with st.expander("Innovation & R&D", expanded=False):
        t_rd = st.toggle("R&D activities", value=True, key="ar_t_rd")
        t_innov = st.toggle("Innovation focus", value=True, key="ar_t_innov")

    force_fresh = st.checkbox("Force fresh analysis", value=False, key="ar_force_refresh")
    analyze_clicked = st.button("Analyze report", type="primary", use_container_width=True)
    st.divider()

    fiscal_flags = [t_perf, t_events, t_chal]
    strat_flags = [t_strat, t_market, t_road]
    risk_flags = [t_risk, t_mit]
    innov_flags = [t_rd, t_innov]

    fiscal_toggles = dict(zip(fiscal_year_attributes, fiscal_flags))
    strat_toggles = dict(zip(strat_outlook_attributes, strat_flags))
    risk_toggles = dict(zip(risk_management_attributes, risk_flags))
    innov_toggles = dict(zip(innovation_attributes, innov_flags))

    if process_clicked:
        if pdf_file is None:
            st.error("Choose a PDF first.")
        else:
            body = pdf_file.getvalue()
            st.session_state.pdf_bytes_hash = hashlib.sha256(body).hexdigest()
            with st.spinner("Parsing and indexing document…"):
                nodes = _process_pdf(pdf_file)
                st.session_state.index = _get_vector_index(nodes, openai_key)
                st.session_state.process_doc = True
                st.session_state.ar_has_results = False
            st.success("Document ready for analysis.")

    if analyze_clicked:
        if not st.session_state.process_doc:
            st.error("Process a document first.")
        else:
            pdf_fp = st.session_state.get("pdf_bytes_hash") or ""
            ar_key = analysis_cache.annual_report_cache_key(
                pdf_fp, fiscal_flags, strat_flags, risk_flags, innov_flags
            )
            if (not force_fresh) and analysis_cache.has_annual_report(ar_key):
                loaded = analysis_cache.load_annual_report_session(ar_key)
                if loaded:
                    for k, v in loaded.items():
                        st.session_state[k] = v
                    st.session_state.ar_has_results = True
                    st.success("Loaded saved analysis (no new LLM calls).")
            else:
                engine = _get_query_engine(
                    st.session_state.index.as_query_engine(similarity_top_k=3),
                    openai_key,
                )
                start = time.time()
                with st.status("Analyzing report…", expanded=True):
                    if any(fiscal_flags):
                        st.write("Fiscal year highlights…")
                        fy = list(fiscal_flags)
                        for i, insight in enumerate(fiscal_year_attributes):
                            if st.session_state.get(insight):
                                fy[i] = False
                        resp = _report_insights(engine, "Fiscal Year Highlights", fy, 1)
                        for k, v in resp["insights"].items():
                            st.session_state[k] = v

                    if any(strat_flags):
                        st.write("Strategy outlook…")
                        sl = list(strat_flags)
                        for i, insight in enumerate(strat_outlook_attributes):
                            if st.session_state.get(insight):
                                sl[i] = False
                        resp = _report_insights(
                            engine, "Strategy Outlook and Future Direction", sl, 2
                        )
                        for k, v in resp["insights"].items():
                            st.session_state[k] = v

                    if any(risk_flags):
                        st.write("Risk management…")
                        rl = list(risk_flags)
                        for i, insight in enumerate(risk_management_attributes):
                            if st.session_state.get(insight):
                                rl[i] = False
                        resp = _report_insights(engine, "Risk Management", rl, 3)
                        for k, v in resp["insights"].items():
                            st.session_state[k] = v

                    if any(innov_flags):
                        st.write("Innovation and R&D…")
                        il = list(innov_flags)
                        for i, insight in enumerate(innovation_attributes):
                            if st.session_state.get(insight):
                                il[i] = False
                        resp = _report_insights(engine, "Innovation and R&D", il, 4)
                        for k, v in resp["insights"].items():
                            st.session_state[k] = v

                    st.session_state.end_time = f"{time.time() - start:.2f}"

                st.session_state.ar_has_results = True
                snap = {k: st.session_state.get(k) for k in _AR_INSIGHT_KEYS}
                snap["end_time"] = st.session_state.get("end_time")
                analysis_cache.save_annual_report_session(ar_key, snap)
                st.success("Analysis complete.")

    if st.session_state.get("end_time"):
        st.caption(f"Last run: {st.session_state.end_time} s")

    if not st.session_state.process_doc:
        st.info("Upload a PDF above and click **Process document** to begin.")
        return

    if not st.session_state.ar_has_results and not any(
        st.session_state.get(k) for k in _AR_INSIGHT_KEYS
    ):
        st.info("Document indexed. Select themes and click **Analyze report**.")
        return

    tab_fy, tab_strat, tab_risk, tab_innov = st.tabs(
        ["Fiscal year", "Strategy outlook", "Risk management", "Innovation & R&D"]
    )

    _render_insight_tab(tab_fy, "Fiscal year highlights", list(fiscal_year_attributes), fiscal_toggles)
    _render_insight_tab(tab_strat, "Strategy outlook", list(strat_outlook_attributes), strat_toggles)
    _render_insight_tab(tab_risk, "Risk management", list(risk_management_attributes), risk_toggles)
    _render_insight_tab(tab_innov, "Innovation & R&D", list(innovation_attributes), innov_toggles)
