"""LITE 財報寫入 MySQL：共用連線、建表與 upsert。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import pymysql

# 環境變數：MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE


def get_mysql_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", "financial_qa"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }


@contextmanager
def get_connection() -> Generator[pymysql.Connection, None, None]:
    cfg = get_mysql_config()
    conn = pymysql.connect(**cfg)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_schema(conn: pymysql.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lite_statement_quarterly (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(16) NOT NULL,
                statement_type VARCHAR(20) NOT NULL,
                line_item VARCHAR(512) NOT NULL,
                period_end DATE NOT NULL,
                value_usd DOUBLE NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_row (ticker, statement_type, line_item(255), period_end),
                KEY idx_ticker_period (ticker, period_end)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )


def dataframe_to_rows(
    ticker: str,
    statement_type: str,
    df,
) -> list[tuple[str, str, str, Any, float | None]]:
    """將 yfinance 財報 DataFrame（index=科目, columns=季末日期）展開成列。"""
    import pandas as pd

    if df is None or df.empty:
        return []
    rows: list[tuple[str, str, str, Any, float | None]] = []
    for line_item in df.index:
        for col in df.columns:
            period_end = pd.Timestamp(col).date()
            val = df.loc[line_item, col]
            if pd.isna(val):
                fval: float | None = None
            else:
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    fval = None
            rows.append((ticker, statement_type, str(line_item), period_end, fval))
    return rows


def upsert_statements(
    ticker: str,
    statements: dict[str, Any],
    type_map: dict[str, str],
) -> int:
    """
    statements: 中文名稱 -> DataFrame
    type_map: 中文名稱 -> 'income'|'balance'|'cashflow'
    回傳寫入列數。
    """
    import pandas as pd

    total = 0
    with get_connection() as conn:
        ensure_schema(conn)
        sql = """
            INSERT INTO lite_statement_quarterly
                (ticker, statement_type, line_item, period_end, value_usd)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE value_usd = VALUES(value_usd), updated_at = CURRENT_TIMESTAMP
        """
        with conn.cursor() as cur:
            for name, df in statements.items():
                stype = type_map.get(name)
                if not stype or not isinstance(df, pd.DataFrame):
                    continue
                for row in dataframe_to_rows(ticker, stype, df):
                    cur.execute(sql, row)
                    total += 1
    return total
