from src.yahoo_finance import fetch_news


def classify_sentiment(mean_score):
    if mean_score <= -0.35:
        return "Bearish"
    if mean_score <= -0.15:
        return "Somewhat bearish"
    if mean_score < 0.15:
        return "Neutral"
    if mean_score < 0.35:
        return "Somewhat bullish"
    return "Bullish"


def top_news(symbol, limit=10):
    return fetch_news(symbol, limit)
