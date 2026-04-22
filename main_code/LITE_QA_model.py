"""
LITE (Lumentum) 季報財務資料：以 yfinance 抓取、輸出 CSV、寫入 MySQL。

MySQL 連線請設定環境變數：MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

from lite_mysql import upsert_statements

warnings.filterwarnings("ignore", category=FutureWarning)

TICKER = "LITE"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "database"
CSV_INCOME = OUTPUT_DIR / "LITE_quarterly_income.csv"
CSV_BALANCE = OUTPUT_DIR / "LITE_quarterly_balance.csv"
CSV_CASHFLOW = OUTPUT_DIR / "LITE_quarterly_cashflow.csv"

STMT_TYPE_MAP = {
    "季損益 (Quarterly Income)": "income",
    "資產負債 (Quarterly Balance)": "balance",
    "現金流量 (Quarterly Cashflow)": "cashflow",
}


def _statement_to_df(raw) -> pd.DataFrame:
    if raw is None:
        return pd.DataFrame()
    if isinstance(raw, pd.DataFrame) and raw.empty:
        return pd.DataFrame()
    return raw.copy()


def fetch_lite_quarterly() -> dict[str, pd.DataFrame]:
    t = yf.Ticker(TICKER)
    return {
        "季損益 (Quarterly Income)": _statement_to_df(t.quarterly_financials),
        "資產負債 (Quarterly Balance)": _statement_to_df(t.quarterly_balance_sheet),
        "現金流量 (Quarterly Cashflow)": _statement_to_df(t.quarterly_cashflow),
    }


def save_csvs(statements: dict[str, pd.DataFrame]) -> dict[str, Path]:
    paths = {
        "季損益 (Quarterly Income)": CSV_INCOME,
        "資產負債 (Quarterly Balance)": CSV_BALANCE,
        "現金流量 (Quarterly Cashflow)": CSV_CASHFLOW,
    }
    for name, df in statements.items():
        p = paths[name]
        if df.empty:
            pd.DataFrame({"message": [f"無資料: {name}"]}).to_csv(p, index=False, encoding="utf-8-sig")
            print(f"警告: {name} 無資料，已寫入占位 CSV: {p}")
        else:
            out = df.reset_index().rename(columns={"index": "Line_Item"})
            out.to_csv(p, index=False, encoding="utf-8-sig")
            print(f"已儲存: {p}")
    return paths


def upload_mysql(statements: dict[str, pd.DataFrame]) -> None:
    try:
        n = upsert_statements(TICKER, statements, STMT_TYPE_MAP)
        print(f"MySQL 已寫入 / 更新 {n} 筆季報列。")
    except Exception as e:
        print(f"MySQL 寫入失敗: {e}")
        print("（請確認 MySQL 已啟動且環境變數 MYSQL_* 正確、已授權該使用者建表與寫入）")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"抓取 {TICKER} 季報財務資料 (yfinance)...")
    statements = fetch_lite_quarterly()
    save_csvs(statements)
    upload_mysql(statements)
    print("完成。")


if __name__ == "__main__":
    main()
