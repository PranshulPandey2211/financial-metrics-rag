import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

import pandas as pd

from src.yahoo_finance import fetch_news
from src.helpers import api_error

def classify_sentiment(mean_score):
    if mean_score <= -0.35:
        return "Bearish"
    elif -0.35 < mean_score <= -0.15:
        return "Somewhat-Bearish"
    elif -0.15 < mean_score < 0.15:
        return "Neutral"
    elif 0.15 <= mean_score < 0.35:
        return "Somewhat_Bullish"
    elif mean_score >= 0.35:
        return "Bullish"
    else:
        return "Undefined"

def top_news(symbol, max_feed):
    return fetch_news(symbol, max_feed)

if __name__ == "__main__":
    news = top_news("AAPL", 10)
    print(news)

