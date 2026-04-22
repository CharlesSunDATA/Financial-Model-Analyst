"""
LITE 營收趨勢：從 MySQL 讀取季報營收，Streamlit 顯示最近四期趨勢圖。

說明：公開財報僅有「季」頻率，無週營收；圖表為「最近四季」合計營收（Total Revenue）趨勢。

執行：cd main_code && streamlit run lite_revenue_streamlit.py
環境變數：與 LITE_QA_model 相同之 MYSQL_*
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pymysql
import streamlit as st

from lite_mysql import ensure_schema, get_connection, get_mysql_config

TICKER = "LITE"
# 與 yfinance 損益表常見列名對應
REVENUE_LINE_PRIORITY = (
    "Total Revenue",
    "Total Revenues",
    "Revenue",
    "Net Sales",
)


def _pick_revenue_line(df: pd.DataFrame) -> str | None:
    if df.empty or "line_item" not in df.columns:
        return None
    items = df["line_item"].astype(str).unique()
    for name in REVENUE_LINE_PRIORITY:
        if name in items:
            return name
    for it in items:
        if "revenue" in it.lower() and "cost" not in it.lower():
            return it
    return None


def load_revenue_last_quarters(limit: int = 4) -> pd.DataFrame:
    """最近 n 個季度之營收（依 period_end 新到舊取 n 期，再依時間正序畫圖）。"""
    with get_connection() as conn:
        ensure_schema(conn)
        q = """
            SELECT line_item, period_end, value_usd
            FROM lite_statement_quarterly
            WHERE ticker = %s AND statement_type = 'income'
            ORDER BY period_end DESC
        """
        raw = pd.read_sql(q, conn, params=(TICKER,))
    if raw.empty:
        return pd.DataFrame(columns=["period_end", "revenue_usd"])

    line = _pick_revenue_line(raw)
    if not line:
        return pd.DataFrame(columns=["period_end", "revenue_usd"])

    sub = raw[raw["line_item"] == line].copy()
    sub["period_end"] = pd.to_datetime(sub["period_end"])
    sub = sub.sort_values("period_end", ascending=False).head(limit)
    sub = sub.sort_values("period_end", ascending=True)
    out = sub.rename(columns={"value_usd": "revenue_usd"})[["period_end", "revenue_usd"]]
    out["revenue_mm"] = out["revenue_usd"] / 1e6
    return out


def main() -> None:
    st.set_page_config(page_title="LITE 營收趨勢", layout="wide")
    st.title("Lumentum (LITE) 營收趨勢")
    st.caption(
        "資料來源：本機 MySQL（由 `LITE_QA_model.py` 自 yfinance 寫入）。"
        "公開財報僅有季資料，故圖表為「最近四季」合計營收，而非週頻。"
    )

    cfg = get_mysql_config()
    st.sidebar.markdown("**MySQL**")
    st.sidebar.text(f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}")

    try:
        df = load_revenue_last_quarters(4)
    except Exception as e:
        st.error(f"無法連線或查詢 MySQL：{e}")
        st.info("請先設定 MYSQL_* 環境變數並執行 `python LITE_QA_model.py` 匯入資料。")
        return

    if df.empty:
        st.warning("尚無營收資料。請先執行：`python LITE_QA_model.py`")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["period_end"].dt.strftime("%Y-%m-%d"),
            y=df["revenue_mm"],
            mode="lines+markers",
            name="營收",
            line=dict(width=2),
            marker=dict(size=10),
        )
    )
    fig.update_layout(
        title="最近四季 Total Revenue（百萬美元）",
        xaxis_title="季末",
        yaxis_title="百萬美元 (USD mm)",
        hovermode="x unified",
        height=480,
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("數據表")
    show = df.assign(
        period_end=df["period_end"].dt.strftime("%Y-%m-%d"),
        revenue_usd=df["revenue_usd"].map(lambda x: f"{x:,.0f}" if pd.notna(x) else ""),
    )
    st.dataframe(show, width="stretch")


if __name__ == "__main__":
    main()
