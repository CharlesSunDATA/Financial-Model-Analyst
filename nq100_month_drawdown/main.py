"""
NQ100：從 Yahoo Finance 下載日線 → 計算最近 N 個交易日區間內最大回撤 → 排行 CSV。

預設成分與產業自上一層 `database/nq100_health_metrics.csv`；日線存 `database/nq100_daily_prices.csv`；
排行存 `database/nq100_max_drawdown_last_month_rank.csv`。

離線模式：`--local-only` 只讀既有日線 CSV（不上網）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _max_drawdown(closes: pd.Series) -> float:
    c = closes.astype(float)
    if c.isna().any() or len(c) < 2:
        return float("nan")
    run_max = c.cummax()
    dd = c / run_max - 1.0
    return float(dd.min())


def _load_universe(path: Path) -> pd.DataFrame:
    u = pd.read_csv(path)
    if "ticker" not in u.columns:
        raise ValueError(f"universe 需有 ticker 欄：{path}")
    u = u[["ticker", "sector"]].copy() if "sector" in u.columns else u[["ticker"]].copy()
    if "sector" not in u.columns:
        u["sector"] = ""
    u["ticker"] = u["ticker"].astype(str).str.strip().str.upper()
    return u.drop_duplicates("ticker")


def _yf_download_long(tickers: list[str], period: str) -> pd.DataFrame:
    import yfinance as yf

    if not tickers:
        return pd.DataFrame(columns=["date", "ticker", "close_price"])

    raw = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "close_price"])

    if "Close" not in raw.columns:
        return pd.DataFrame(columns=["date", "ticker", "close_price"])

    closes = raw["Close"].copy()
    closes.index = pd.to_datetime(closes.index).tz_localize(None).normalize()

    if isinstance(closes, pd.Series):
        sym = tickers[0]
        s = closes.dropna()
        return pd.DataFrame({"date": s.index, "ticker": sym, "close_price": s.astype(float).values})

    wide = closes.reset_index()
    date_col = wide.columns[0]
    long_df = wide.melt(id_vars=[date_col], var_name="ticker", value_name="close_price")
    long_df = long_df.dropna(subset=["close_price"])
    long_df = long_df.rename(columns={date_col: "date"})
    long_df["date"] = pd.to_datetime(long_df["date"]).dt.normalize()
    long_df["ticker"] = long_df["ticker"].astype(str).str.upper()
    long_df["close_price"] = long_df["close_price"].astype(float)
    return long_df


def _rank_from_prices(df: pd.DataFrame, days: int) -> pd.DataFrame:
    df = df.sort_values(["ticker", "date"])
    rows: list[dict] = []
    for ticker, g in df.groupby("ticker", sort=False):
        w = g.tail(days)
        if len(w) < 2:
            continue
        sector = w["sector"].iloc[-1] if "sector" in w.columns else ""
        mdd = _max_drawdown(w["close_price"])
        if pd.isna(mdd):
            continue
        rows.append(
            {
                "ticker": ticker,
                "sector": sector if pd.notna(sector) else "",
                "max_drawdown_pct": round(mdd * 100.0, 4),
                "window_start": w["date"].iloc[0].strftime("%Y-%m-%d"),
                "window_end": w["date"].iloc[-1].strftime("%Y-%m-%d"),
                "n_trading_days": len(w),
            }
        )
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.sort_values("max_drawdown_pct", ascending=True).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def main() -> int:
    root = Path(__file__).resolve().parent
    parent = root.parent
    db = parent / "database"
    default_univ = db / "nq100_health_metrics.csv"
    default_prices = db / "nq100_daily_prices.csv"
    default_rank = db / "nq100_max_drawdown_last_month_rank.csv"

    p = argparse.ArgumentParser(description="NQ100 上網抓日線 → 最大回撤排行 CSV")
    p.add_argument("--local-only", action="store_true", help="不上網，只讀 --prices 既有 CSV")
    p.add_argument("--universe", type=Path, default=default_univ, help="成分 ticker + sector")
    p.add_argument("--prices", type=Path, default=default_prices, help="日線 CSV（--local-only 讀取；預設下載後覆寫）")
    p.add_argument("--rank-out", type=Path, default=default_rank, help="輸出排行 CSV")
    p.add_argument("--no-save-prices", action="store_true", help="下載後不寫入日線檔（仍會算排行）")
    p.add_argument(
        "--yf-period",
        default="3mo",
        help="yfinance period（須涵蓋 --days 個交易日），預設 3mo",
    )
    p.add_argument(
        "--days",
        type=int,
        default=22,
        help="每檔取最後幾個交易日計算回撤（預設 22）",
    )
    args = p.parse_args()

    if not args.universe.is_file():
        print(f"找不到成分檔：{args.universe}", file=sys.stderr)
        return 1

    try:
        univ = _load_universe(args.universe)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    tickers = univ["ticker"].tolist()

    if args.local_only:
        if not args.prices.is_file():
            print(f"找不到日線檔：{args.prices}", file=sys.stderr)
            return 1
        prices = pd.read_csv(args.prices)
    else:
        try:
            long_px = _yf_download_long(tickers, args.yf_period)
        except Exception as e:
            print(f"Yahoo Finance 下載失敗：{e}", file=sys.stderr)
            return 1
        if long_px.empty:
            print("下載結果為空（請檢查網路或 ticker 是否有效）。", file=sys.stderr)
            return 1
        prices = long_px.merge(univ, on="ticker", how="left")
        prices["sector"] = prices["sector"].fillna("")
        if not args.no_save_prices:
            args.prices.parent.mkdir(parents=True, exist_ok=True)
            out_px = prices[["date", "ticker", "close_price", "sector"]].sort_values(["date", "ticker"])
            out_px.to_csv(args.prices, index=False)
            print(f"Saved prices -> {args.prices} ({len(out_px)} rows)")

    need = {"date", "ticker", "close_price"}
    if not need.issubset(prices.columns):
        print(f"日線需含欄位 {sorted(need)}，目前有：{list(prices.columns)}", file=sys.stderr)
        return 1

    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    if "sector" not in prices.columns:
        prices = prices.merge(univ, on="ticker", how="left")
        prices["sector"] = prices["sector"].fillna("")

    ranked = _rank_from_prices(prices, args.days)
    if ranked.empty:
        print("沒有足夠資料可計算（每檔至少需要 2 個交易日）。", file=sys.stderr)
        return 1

    fetched = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ranked.insert(1, "fetched_at_utc", fetched)

    args.rank_out.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(args.rank_out, index=False)
    print(f"Wrote rank -> {args.rank_out} ({len(ranked)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
