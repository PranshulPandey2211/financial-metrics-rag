# FinAnalytica

**FinAnalytica** is an **AI-powered financial analysis** app built with [Streamlit](https://streamlit.io/). It pulls fundamentals from Yahoo Finance, adds LLM commentary on the themes you choose, and can analyze an annual report PDF with RAG (LlamaIndex).

The UI is a single page with a top **section** switch (**Financial Metrics** vs **Annual Report Analyzer**). Main controls and results stay in the main column (the default Streamlit sidebar is hidden via CSS).

## Features

### Financial Metrics

- Enter a US ticker (e.g. `AAPL`). Data comes from **Yahoo Finance** via [yfinance](https://github.com/ranaroussi/yfinance) (no market-data API key).
- Tabs: **Overview**, **Income statement**, **Balance sheet**, **Cash flow**, **News**.
- Toggle which **insight themes** you want; OpenAI generates commentary per theme using templates in `src/llm_prompts.py`.
- News headlines include **VADER** sentiment labels on the text returned by Yahoo.
- Successful runs can be **cached on disk** under `cache/reports/` so repeat requests with the same ticker and theme flags avoid refetching (unless you use **Force fresh fetch**).

### Annual Report Analyzer

- Upload a **PDF** (10-K or full annual report works best).
- **Process document** builds a vector index; **Analyze report** runs themed questions through a LlamaIndex query setup.
- Optional **Force fresh analysis** bypasses the saved snapshot in `cache/annual_reports/`.

## Tech stack

| Piece | Role |
|--------|------|
| Streamlit | Web UI |
| yfinance | Fundamentals, profile, news |
| LangChain + OpenAI | Chat model for financial-metrics commentary (`gpt-3.5-turbo` in code) |
| LlamaIndex + FAISS | Annual report RAG |
| NLTK VADER | Headline sentiment scores |

## Requirements

- **Python 3.10 or 3.11** (3.12 may work; this stack pins older LlamaIndex / LangChain.)
- Install: `pip install -r requirements.txt` — first run can download **PyTorch** and PDF-parsing dependencies (large).
- **OpenAI**: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set `openai_api_key`, or set `OPENAI_API_KEY`.

If a package fails to build on your OS, create a fresh venv and retry; the annual-report tab needs the `unstructured` / `torch` lines above.

## Project layout

```
app.py                 # Entrypoint: section radio + runs the selected module
src/
  llm_prompts.py            # LLM system / task strings (financial + annual report)
  financial_metrics.py       # Yahoo metrics UI and orchestration
  annual_report_analyzer.py  # PDF RAG UI and flow
  yahoo_finance.py           # Yahoo fetch + normalization
  income_statement.py        # Income metrics + insights
  balance_sheet.py
  cash_flow.py
  company_profile.py
  company_news.py
  insight_themes.py          # Theme keys and prompt snippets
  helpers.py                 # OpenAI key, charts, shared helpers
  app_theme.py               # CSS + small UI helpers
  analysis_cache.py          # Disk cache for both flows
.streamlit/
  config.toml              # Theme / server options (safe to commit)
  secrets.toml.example     # Copy to secrets.toml locally
  secrets.toml             # Your API key (create locally — gitignored)
```

## Local setup

1. Open this project directory in your terminal.

2. **Python 3.10+** recommended. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **OpenAI API key** — get a key from [OpenAI](https://platform.openai.com/api-keys).

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Edit `.streamlit/secrets.toml` and set `openai_api_key`, or set the environment variable `OPENAI_API_KEY`.

5. **Run the app** from the repository root:

   ```bash
   python -m streamlit run app.py
   ```

   Open the URL Streamlit prints (usually `http://localhost:8501`).
