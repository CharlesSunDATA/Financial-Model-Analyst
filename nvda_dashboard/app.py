"""
Streamlit entrypoint: multipage app (valuation, quarterly financials, Markowitz).
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Finance Analytics Suite", layout="wide")

pg = st.navigation(
    [
        st.Page("valuation_dashboard.py", title="Stock Valuation", default=True),
        st.Page("pages/1_Quarterly_financials.py", title="Quarterly financials"),
        st.Page("markowitz_portfolio.py", title="Markowitz optimization"),
    ],
)
pg.run()
