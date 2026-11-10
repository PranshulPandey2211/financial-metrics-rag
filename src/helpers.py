import os

from langchain.chat_models import ChatOpenAI


def get_openai_api_key():
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if key:
        os.environ["OPENAI_API_KEY"] = key
    return key


def statement_error_response(message):
    return {
        "Error": True,
        "Error Message": message,
        "metrics": {},
        "chart_data": {},
    }


def get_chat_model(api_key, model_name="gpt-3.5-turbo"):
    return ChatOpenAI(openai_api_key=api_key, model_name=model_name)


def safe_float(value):
    if value is None or value == "None":
        return "N/A"
    return float(value)


def round_numeric(value, decimal_places=2):
    if isinstance(value, (int, float)):
        return round(value, decimal_places)
    if isinstance(value, str) and value.replace(".", "", 1).isdigit():
        return round(float(value), decimal_places)
    return value


def format_ratio_as_pct(value):
    if value is None or value == "N/A":
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_currency(value):
    if value is None or value == "N/A" or value == "None":
        return "N/A"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    if num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    return f"${num:.2f}"
