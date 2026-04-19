"""
LITE (Lumentum) 季報財務資料：以 yfinance 抓取、輸出 CSV、上傳 Google Sheets。
執行目錄不限；credentials 預設為專案根目錄的 credentials.json。

目標試算表（QA_01_FM）：
https://docs.google.com/spreadsheets/d/1AkHVsRUHlMnjs1Ean4YfyvySfWVCIDdsq2_ZMI1b3UE/edit
請將該檔案與 service account 電子郵件共用（編輯者），API 才能寫入。
"""

from __future__ import annotations

import warnings
from pathlib import Path

import gspread
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

TICKER = "LITE"
# 共享試算表 ID（網址 .../d/<這段>/edit...）
SPREADSHEET_ID = "1AkHVsRUHlMnjs1Ean4YfyvySfWVCIDdsq2_ZMI1b3UE"
CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "credentials.json"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "database"
CSV_INCOME = OUTPUT_DIR / "LITE_quarterly_income.csv"
CSV_BALANCE = OUTPUT_DIR / "LITE_quarterly_balance.csv"
CSV_CASHFLOW = OUTPUT_DIR / "LITE_quarterly_cashflow.csv"


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


def _df_to_sheet_rows(df: pd.DataFrame) -> list[list]:
    if df.empty:
        return [["No data"]]
    out = df.reset_index().rename(columns={"index": "Line_Item"})
    out = out.fillna("")
    header = [str(c) for c in out.columns.tolist()]
    rows = out.values.tolist()
    return [header] + rows


def upload_google_sheets(statements: dict[str, pd.DataFrame]) -> None:
    if not CREDENTIALS_PATH.is_file():
        print(f"上傳略過: 找不到 credentials 檔案 {CREDENTIALS_PATH}")
        return
    try:
        gc = gspread.service_account(filename=str(CREDENTIALS_PATH))
        sh = gc.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        print(f"連線 Google Sheets 失敗: {e}")
        print("（請確認試算表已與 credentials 內 service account 信箱共用為編輯者）")
        return

    sheet_slug = {
        "季損益 (Quarterly Income)": "LITE_QA_Income",
        "資產負債 (Quarterly Balance)": "LITE_QA_Balance",
        "現金流量 (Quarterly Cashflow)": "LITE_QA_Cashflow",
    }

    for name, df in statements.items():
        title = sheet_slug[name]
        try:
            ws = sh.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=300, cols=30)
        try:
            ws.clear()
            data = _df_to_sheet_rows(df)
            ws.update(data, value_input_option="USER_ENTERED")
            print(f"已上傳工作表: {title}")
        except Exception as e:
            print(f"上傳工作表 {title} 失敗: {e}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"抓取 {TICKER} 季報財務資料 (yfinance)...")
    statements = fetch_lite_quarterly()
    save_csvs(statements)
    upload_google_sheets(statements)
    print("完成。")


if __name__ == "__main__":
    main()
