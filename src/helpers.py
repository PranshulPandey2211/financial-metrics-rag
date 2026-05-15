import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from langchain.prompts import PromptTemplate

from src.llm_prompts import INSIGHT_FINANCIAL
from langchain.chat_models import ChatOpenAI
import streamlit as st
import json
import plotly.graph_objects as go
import os


def _secret_value(name):
    try:
        return (st.secrets.get(name) or "").strip()
    except Exception:
        return ""


def get_openai_api_key():
    key = _secret_value("openai_api_key") or (os.environ.get("OPENAI_API_KEY") or "").strip()
    if key:
        os.environ["OPENAI_API_KEY"] = key
    return key


def statement_error_response(message):
    return {
        "Error": True,
        "Error Message": message,
        "metrics": {},
        "chart_data": {},
        "insights": {},
    }


def api_error(message):
    return {"Error": True, "Error Message": message}


def api_error_message(payload):
    if payload.get("Error Message"):
        return str(payload["Error Message"])
    error = payload.get("Error")
    if isinstance(error, str):
        return error
    return "Unknown API error."


def get_model(model_name, api_key):
    if model_name == "openai":
        model = ChatOpenAI(openai_api_key=api_key, model_name="gpt-3.5-turbo")
    return model


def safe_float(value):
    if value == "None" or value == None:
        return "N/A"
    return float(value)


def round_numeric(value, decimal_places=2):
    if isinstance(value, (int, float)):
        return round(value, decimal_places)
    elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
        return round(float(value), decimal_places)
    else:
        return value


def format_currency(value):
    if value is None or value == "N/A" or value == "None":
        return "N/A"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f} billion"
    if num >= 1_000_000:
        return f"${num / 1_000_000:.2f} million"
    return f"${num:.2f}"


def get_total_revenue(symbol):
    from src.yahoo_finance import latest_total_revenue

    return latest_total_revenue(symbol)


def get_total_debt(symbol):
    from src.yahoo_finance import latest_total_debt

    return latest_total_debt(symbol)


def insights(insight_name, type_of_data, data, output_format, api_key):
    if not (api_key or "").strip():
        raise ValueError("OpenAI API key is missing.")

    template = INSIGHT_FINANCIAL
    prompt = PromptTemplate(
        template=template,
        input_variables=["insight_name", "type_of_data", "inputs", "output_format"],
    )
    model = get_model("openai", api_key)
    payload = json.dumps(data)
    formatted_input = prompt.format(
        insight_name=insight_name,
        type_of_data=type_of_data,
        inputs=payload,
        output_format=output_format,
    )
    return model.predict(formatted_input)


def generate_insight(insight_name, type_of_data, data, output_format, api_key):
    try:
        return insights(insight_name, type_of_data, data, output_format, api_key)
    except Exception as exc:
        return f"*Insight could not be generated ({exc}).*"


def format_title(s):
    return " ".join(word.capitalize() for word in s.split("_"))


def create_donut_chart(data, type_of_data, title=None, hole_size=0.3):
    labels = list(data[type_of_data].keys())
    values = [safe_float(v) for v in data[type_of_data].values()]
    numeric_values = []
    numeric_labels = []
    for label, val in zip(labels, values):
        if val != "N/A":
            numeric_values.append(val)
            numeric_labels.append(label)
    if not numeric_values:
        numeric_labels, numeric_values = labels, [0.0] * len(labels)

    fig = go.Figure(data=[go.Pie(labels=numeric_labels, values=numeric_values, hole=hole_size)])
    fig.update_layout(title=title or format_title(type_of_data))
    return fig


def create_bar_chart(data, type_of_data, title=None):
    yaxis_title = format_title(type_of_data)
    fig = go.Figure(data=[go.Bar(x=data["dates"], y=data[type_of_data])])
    fig.update_layout(
        title=title or format_title(type_of_data),
        xaxis_title="Date",
        yaxis_title=yaxis_title,
    )
    return fig
