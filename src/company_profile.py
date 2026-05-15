import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from src.yahoo_finance import fetch_overview
from src.helpers import safe_float


def company_overview(symbol):
    data = fetch_overview(symbol)
    if data.get("Error"):
        return data
    if data.get("MarketCapitalization") not in (None, "None"):
        data["MarketCapitalization"] = safe_float(data["MarketCapitalization"])
    return data


if __name__ == "__main__":
    ans = company_overview("TSLA")
    print(ans)
