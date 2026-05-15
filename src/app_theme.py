import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def ensure_project_root():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def page_config(*, title):
    st.set_page_config(
        page_title=title,
        layout="wide",
        initial_sidebar_state="collapsed",
    )


APP_CSS = """
<style>
    .block-container { padding-top: 1rem; max-width: 1200px; }
    .fs-tab-head {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 0.75rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid #e2e8f0;
    }
    .fs-section-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748b;
        margin: 0.75rem 0 0.5rem 0;
    }
    div[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.4rem 0.6rem;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    }
    .fs-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
    }
    .fs-card h4 { margin: 0 0 0.5rem 0; font-size: 0.95rem; color: #1e293b; }
</style>
"""


def apply_theme():
    st.markdown(APP_CSS, unsafe_allow_html=True)


def tab_heading(title):
    st.markdown(f'<p class="fs-tab-head">{title}</p>', unsafe_allow_html=True)


def section_label(text):
    st.markdown(f'<p class="fs-section-label">{text}</p>', unsafe_allow_html=True)


def insight_card(title, body, *, empty_hint="Run analysis to generate this insight."):
    st.markdown(f'<div class="fs-card"><h4>{title}</h4>', unsafe_allow_html=True)
    if body:
        st.markdown(body)
    else:
        st.caption(empty_hint)
    st.markdown("</div>", unsafe_allow_html=True)


def panel_section(title):
    st.markdown(f"#### {title}")
