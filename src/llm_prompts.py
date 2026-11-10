FUNDAMENTALS_BATCH_INSIGHT = """You are writing equity research notes. Use ONLY the JSON payload from Yahoo Finance.

Themes (return one string per key):
{themes_spec}

Data:
{payload}

Reply with JSON only: keys = theme ids, values = paragraphs (about 40+ words when data allows).
If the numbers do not support a theme, use: "Insufficient data in payload."
"""

FILING_BATCH_INSIGHT = """You are summarizing an annual report. Use ONLY the retrieved passages below—not market data.

Themes:
{themes_spec}

Evidence (per theme):
{evidence}

Reply with JSON only. Ground each answer in that theme's evidence list.
If evidence is empty, use: "No information available."
"""
