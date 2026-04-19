# Finance Analytics Suite (Streamlit)

Single Streamlit app with three pages:

1. **Stock Valuation** — DCF and trailing P/E vs. historical range (`valuation_dashboard.py`)
2. **Quarterly financials** — Yahoo quarterly statements and charts (`pages/1_Quarterly_financials.py`)
3. **Markowitz optimization** — efficient frontier, Monte Carlo, max-Sharpe & min-vol weights (`markowitz_portfolio.py`)

## Local run

```bash
cd nvda_dashboard
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Or: `./run.sh`

## Deploy on Streamlit Community Cloud

1. Push this repository (or a fork) to GitHub.
2. In [share.streamlit.io](https://share.streamlit.io), **New app** → connect the repo.
3. **Main file path:** `nvda_dashboard/app.py`  
   **App URL** (optional): choose a subdomain.
4. **Python version:** 3.11+ recommended.
5. If the UI asks for **App root** / working directory, set it to the repo root so the path `nvda_dashboard/app.py` resolves correctly (some UIs use **Main file** = `app.py` with **Repository root** = folder `nvda_dashboard`).

Dependencies are listed in `nvda_dashboard/requirements.txt`.

## Disclaimer

Educational and research use only — not investment advice.
