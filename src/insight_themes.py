MIN_WORDS = 40


def _fund(text):
    return f"Must be more than {MIN_WORDS} words. {text}"


THEMES = {
    "revenue_health": {
        "label": "Revenue health",
        "group": "income",
        "source": "fundamentals",
        "spec": _fund("Insight into total revenue and health of primary business activity."),
    },
    "operational_efficiency": {
        "label": "Operational efficiency",
        "group": "income",
        "source": "fundamentals",
        "spec": _fund("Operating expenses vs revenue and operational efficiency."),
    },
    "r_and_d_focus": {
        "label": "R&D focus",
        "group": "income",
        "source": "fundamentals",
        "spec": _fund("Commitment to R&D, innovation, and future growth."),
    },
    "debt_management": {
        "label": "Debt management",
        "group": "income",
        "source": "fundamentals",
        "spec": _fund("Interest expense, debt scale, and leverage approach."),
    },
    "profit_retention": {
        "label": "Profit retention",
        "group": "income",
        "source": "fundamentals",
        "spec": _fund("Net income and retention after expenses."),
    },
    "liquidity_position": {
        "label": "Liquidity",
        "group": "balance",
        "source": "fundamentals",
        "spec": _fund("Ability to meet short-term obligations with short-term assets."),
    },
    "assets_efficiency": {
        "label": "Asset efficiency",
        "group": "balance",
        "source": "fundamentals",
        "spec": _fund("How efficiently assets generate sales."),
    },
    "capital_structure": {
        "label": "Capital structure",
        "group": "balance",
        "source": "fundamentals",
        "spec": _fund("Leverage and liabilities vs equity."),
    },
    "inventory_management": {
        "label": "Inventory",
        "group": "balance",
        "source": "fundamentals",
        "spec": _fund("Efficiency in managing and turning inventory."),
    },
    "overall_solvency": {
        "label": "Solvency",
        "group": "balance",
        "source": "fundamentals",
        "spec": _fund("Ability to meet long-term debt and obligations."),
    },
    "operational_cash_efficiency": {
        "label": "Operating cash",
        "group": "cash",
        "source": "fundamentals",
        "spec": _fund("Cash generated from core operations."),
    },
    "investment_capability": {
        "label": "Investments",
        "group": "cash",
        "source": "fundamentals",
        "spec": _fund("Ability to invest using operational cash flows."),
    },
    "financial_flexibility": {
        "label": "Financing cash",
        "group": "cash",
        "source": "fundamentals",
        "spec": _fund("Cash after operations and investments for dividends or buybacks."),
    },
    "dividend_sustainability": {
        "label": "Dividends",
        "group": "cash",
        "source": "fundamentals",
        "spec": _fund("Ability to cover dividends with net earnings."),
    },
    "debt_service_capability": {
        "label": "Debt service",
        "group": "cash",
        "source": "fundamentals",
        "spec": _fund("Ability to service debt from operating cash flows."),
    },
    "performance_highlights": {
        "label": "Performance highlights",
        "group": "fiscal_year",
        "source": "filing",
        "spec": "Key performance and financial stats over the fiscal year.",
        "retrieval_query": "fiscal year financial performance revenue earnings key metrics",
    },
    "major_events": {
        "label": "Major events",
        "group": "fiscal_year",
        "source": "filing",
        "spec": "Significant events, acquisitions, or strategic shifts during the year.",
        "retrieval_query": "acquisitions mergers divestitures major corporate events fiscal year",
    },
    "challenges_encountered": {
        "label": "Challenges encountered",
        "group": "fiscal_year",
        "source": "filing",
        "spec": "Challenges faced and how management addressed them.",
        "retrieval_query": "challenges risks difficulties management response fiscal year",
    },
    "strategic_initiatives": {
        "label": "Strategic initiatives",
        "group": "strategy",
        "source": "filing",
        "spec": "Primary objectives and growth strategies for upcoming years.",
        "retrieval_query": "strategy growth initiatives long-term objectives business direction",
    },
    "market_outlook": {
        "label": "Market outlook",
        "group": "strategy",
        "source": "filing",
        "spec": "Market, competition, and industry trends anticipated.",
        "retrieval_query": "market outlook competition industry trends demand",
    },
    "product_roadmap": {
        "label": "Product roadmap",
        "group": "strategy",
        "source": "filing",
        "spec": "Upcoming launches, expansions, or innovations.",
        "retrieval_query": "product roadmap new products launches innovation pipeline",
    },
    "risk_factors": {
        "label": "Risk factors",
        "group": "risk",
        "source": "filing",
        "spec": "Primary risks the company acknowledges.",
        "retrieval_query": "risk factors material risks uncertainties",
    },
    "risk_mitigation": {
        "label": "Risk mitigation",
        "group": "risk",
        "source": "filing",
        "spec": "Strategies for managing acknowledged risks.",
        "retrieval_query": "risk management mitigation controls hedging",
    },
    "r_and_d_activities": {
        "label": "R&D activities",
        "group": "innovation",
        "source": "filing",
        "spec": "R&D focus, achievements, or breakthroughs.",
        "retrieval_query": "research and development R&D spending programs",
    },
    "innovation_focus": {
        "label": "Innovation focus",
        "group": "innovation",
        "source": "filing",
        "spec": "New technologies, patents, or research areas.",
        "retrieval_query": "innovation patents technology intellectual property",
    },
}

GROUPS = {
    "income": [k for k, t in THEMES.items() if t["group"] == "income"],
    "balance": [k for k, t in THEMES.items() if t["group"] == "balance"],
    "cash": [k for k, t in THEMES.items() if t["group"] == "cash"],
    "fiscal_year": [k for k, t in THEMES.items() if t["group"] == "fiscal_year"],
    "strategy": [k for k, t in THEMES.items() if t["group"] == "strategy"],
    "risk": [k for k, t in THEMES.items() if t["group"] == "risk"],
    "innovation": [k for k, t in THEMES.items() if t["group"] == "innovation"],
}

FUNDAMENTALS_GROUPS = ("income", "balance", "cash")
FILING_GROUPS = ("fiscal_year", "strategy", "risk", "innovation")

ALL_FILING_KEYS = [k for k, t in THEMES.items() if t["source"] == "filing"]
ALL_FUNDAMENTALS_KEYS = [k for k, t in THEMES.items() if t["source"] == "fundamentals"]

def default_theme_flags():
    return {k: True for k in THEMES}
