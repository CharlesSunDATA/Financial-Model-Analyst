"""
Technical Strategy Backtester — single-file Streamlit app.

Data: yfinance
Indicators: pandas_ta
UI/Charts: streamlit + plotly
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

TRADING_DAYS = 252


@dataclass
class BacktestResult:
    df: pd.DataFrame
    equity_strategy: pd.Series
    equity_buyhold: pd.Series
    trades: pd.DataFrame  # entry_date, exit_date, entry_px, exit_px, pnl, pnl_pct, exit_reason


def _pct(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"{x*100:.2f}%"


def _money(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"${x:,.0f}"


@st.cache_data(show_spinner=False, ttl=60 * 30)
def load_ohlcv(ticker: str, start: date, end: date) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        progress=False,
        threads=True,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        # sometimes yfinance returns a multi-index; take the first level match
        df.columns = [c[0] for c in df.columns]
    # Normalize columns to standard OHLCV names (defensive: ensure string keys)
    df = df.rename(columns={str(c): str(c).title() for c in df.columns})

    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return pd.DataFrame()

    df = df[needed].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna()
    return df


def add_indicators(
    df: pd.DataFrame,
    rsi_len: int,
    sma_len: int,
    sma_200_len: int,
    sma_20_len: int,
    atr_len: int,
) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["Close"].pct_change().fillna(0.0)

    out[f"SMA_{sma_len}"] = ta.sma(out["Close"], length=sma_len)
    out[f"SMA_{sma_200_len}"] = ta.sma(out["Close"], length=sma_200_len)
    out[f"SMA_{sma_20_len}"] = ta.sma(out["Close"], length=sma_20_len)
    out[f"RSI_{rsi_len}"] = ta.rsi(out["Close"], length=rsi_len)
    out[f"ATR_{atr_len}"] = ta.atr(out["High"], out["Low"], out["Close"], length=atr_len)

    return out


def backtest_simple_vectorized(
    df: pd.DataFrame,
    sma_len: int,
    rsi_len: int,
    rsi_buy: float,
    rsi_sell: float,
    initial_capital: float,
) -> BacktestResult:
    d = df.copy()
    sma_col = f"SMA_{sma_len}"
    rsi_col = f"RSI_{rsi_len}"

    buy = (d["Close"] > d[sma_col]) & (d[rsi_col] < rsi_buy)
    sell = d[rsi_col] > rsi_sell

    # Position: hold from first buy until sell; vectorized via forward-filled state
    sig = pd.Series(np.nan, index=d.index, dtype=float)
    sig.loc[buy] = 1.0
    sig.loc[sell] = 0.0
    pos = sig.ffill().fillna(0.0).astype(int)

    strat_ret = pos.shift(1).fillna(0).astype(float) * d["ret"]
    equity = float(initial_capital) * (1.0 + strat_ret).cumprod()
    buyhold = float(initial_capital) * (d["Close"] / float(d["Close"].iloc[0]))

    d["position"] = pos
    d["strategy_ret"] = strat_ret
    d["equity_strategy"] = equity
    d["equity_buyhold"] = buyhold

    # Trades from position changes (entry when pos goes 0->1, exit 1->0)
    chg = d["position"].diff().fillna(0)
    entries = d.index[chg == 1]
    exits = d.index[chg == -1]
    if len(exits) and len(entries) and exits[0] < entries[0]:
        exits = exits[1:]
    n = min(len(entries), len(exits))
    entries = entries[:n]
    exits = exits[:n]

    trades = []
    for en, ex in zip(entries, exits):
        ep = float(d.loc[en, "Close"])
        xp = float(d.loc[ex, "Close"])
        pnl = (xp / ep - 1.0) * float(initial_capital)  # scaled; only used for sign
        trades.append(
            {
                "entry_date": en,
                "exit_date": ex,
                "entry_px": ep,
                "exit_px": xp,
                "pnl": pnl,
                "pnl_pct": xp / ep - 1.0,
                "exit_reason": "RSI Sell",
            }
        )

    return BacktestResult(
        df=d,
        equity_strategy=equity,
        equity_buyhold=buyhold,
        trades=pd.DataFrame(trades),
    )


def backtest_advanced_atr_stop_sma20(
    df: pd.DataFrame,
    rsi_len: int,
    rsi_buy: float,
    sma_200_len: int,
    sma_20_len: int,
    atr_len: int,
    atr_mult: float,
    initial_capital: float,
) -> BacktestResult:
    """
    Advanced logic:
    - Buy when Close > SMA_200 and RSI < rsi_buy
    - On buy: entry_price = Close[t], stop = entry_price - atr_mult*ATR[t]
    - Exit triggers:
        A stop-loss: Low[t] < stop
        B trailing exit: Close[t] < SMA_20
      If A or B triggers on day t, we go flat on day t+1.
    """
    d = df.copy()
    rsi_col = f"RSI_{rsi_len}"
    sma200_col = f"SMA_{sma_200_len}"
    sma20_col = f"SMA_{sma_20_len}"
    atr_col = f"ATR_{atr_len}"

    buy_sig = (d["Close"] > d[sma200_col]) & (d[rsi_col] < rsi_buy)

    pos = np.zeros(len(d), dtype=int)
    entry_px = np.full(len(d), np.nan, dtype=float)
    stop_px = np.full(len(d), np.nan, dtype=float)
    exit_reason = np.array([None] * len(d), dtype=object)
    buy_mark = np.zeros(len(d), dtype=bool)
    sell_mark = np.zeros(len(d), dtype=bool)

    in_pos = False
    entry_price = math.nan
    stop_price = math.nan
    pending_exit_reason: str | None = None

    idx = d.index
    for i in range(len(d)):
        # 1) execute exit at open of day i if there was a trigger yesterday
        if pending_exit_reason is not None:
            in_pos = False
            sell_mark[i] = True
            exit_reason[i] = pending_exit_reason
            pending_exit_reason = None
            entry_price = math.nan
            stop_price = math.nan

        # 2) entry at today's close (position becomes 1 from today close onwards)
        if (not in_pos) and bool(buy_sig.iloc[i]):
            # enter at close (signal day). Position is effective next day via shift(1) returns calc.
            in_pos = True
            buy_mark[i] = True
            entry_price = float(d["Close"].iloc[i])
            atr = float(d[atr_col].iloc[i]) if pd.notna(d[atr_col].iloc[i]) else math.nan
            stop_price = entry_price - float(atr_mult) * atr if np.isfinite(atr) else math.nan

        # 3) exit triggers evaluated at end of day i (then exit next day)
        if in_pos:
            low = float(d["Low"].iloc[i])
            close = float(d["Close"].iloc[i])
            sma20 = float(d[sma20_col].iloc[i]) if pd.notna(d[sma20_col].iloc[i]) else math.nan

            hit_stop = np.isfinite(stop_price) and (low < stop_price)
            hit_sma20 = np.isfinite(sma20) and (close < sma20)
            if hit_stop or hit_sma20:
                pending_exit_reason = "Stop Loss" if hit_stop else "SMA20 Trailing Exit"

        # 4) record end-of-day position & diagnostics
        pos[i] = 1 if in_pos else 0
        entry_px[i] = entry_price
        stop_px[i] = stop_price

    d["position"] = pos
    d["entry_px"] = entry_px
    d["stop_px"] = stop_px
    d["buy_mark"] = buy_mark
    d["sell_mark"] = sell_mark
    d["exit_reason"] = exit_reason

    strat_ret = d["position"].shift(1).fillna(0).astype(float) * d["ret"]
    equity = float(initial_capital) * (1.0 + strat_ret).cumprod()
    buyhold = float(initial_capital) * (d["Close"] / float(d["Close"].iloc[0]))

    d["strategy_ret"] = strat_ret
    d["equity_strategy"] = equity
    d["equity_buyhold"] = buyhold

    # Trades: pair buy_mark and sell_mark
    entry_idx = list(d.index[d["buy_mark"]])
    exit_idx = list(d.index[d["sell_mark"]])
    # ensure pairing in time order
    trades = []
    j = 0
    for en in entry_idx:
        while j < len(exit_idx) and exit_idx[j] <= en:
            j += 1
        if j >= len(exit_idx):
            break
        ex = exit_idx[j]
        ep = float(d.loc[en, "Close"])
        # exit occurs at close of exit day (we mark on execution day i). Approx.
        xp = float(d.loc[ex, "Close"])
        trades.append(
            {
                "entry_date": en,
                "exit_date": ex,
                "entry_px": ep,
                "exit_px": xp,
                "pnl": (xp / ep - 1.0) * float(initial_capital),
                "pnl_pct": xp / ep - 1.0,
                "exit_reason": str(d.loc[ex, "exit_reason"]) if d.loc[ex, "exit_reason"] else "Exit",
            }
        )
        j += 1

    return BacktestResult(
        df=d,
        equity_strategy=equity,
        equity_buyhold=buyhold,
        trades=pd.DataFrame(trades),
    )


def perf_metrics(res: BacktestResult, initial_capital: float) -> dict[str, float]:
    eq = res.equity_strategy
    bh = res.equity_buyhold
    if eq.empty:
        return {}
    total_ret = float(eq.iloc[-1] / float(initial_capital) - 1.0)
    n_days = max(1, int(eq.shape[0]))
    ann_ret = float((1.0 + total_ret) ** (TRADING_DAYS / n_days) - 1.0)

    dd = eq / eq.cummax() - 1.0
    max_dd = float(dd.min()) if not dd.empty else 0.0

    bh_ret = float(bh.iloc[-1] / float(initial_capital) - 1.0)

    trades = res.trades
    win_rate = np.nan
    if trades is not None and not trades.empty and "pnl_pct" in trades.columns:
        win_rate = float((trades["pnl_pct"] > 0).mean())

    return {
        "total_return": total_ret,
        "annualized_return": ann_ret,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "buy_hold_return": bh_ret,
    }


def plot_equity(res: BacktestResult) -> go.Figure:
    d = res.df
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d["equity_buyhold"], mode="lines", name="Buy & Hold"))
    fig.add_trace(go.Scatter(x=d.index, y=d["equity_strategy"], mode="lines", name="Strategy"))
    fig.update_layout(
        title="Equity Curve (Strategy vs Buy & Hold)",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        height=420,
    )
    return fig


def plot_price_signals(res: BacktestResult, mode: str) -> go.Figure:
    d = res.df
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d["Close"], mode="lines", name="Close", line=dict(width=2)))

    if mode == "Advanced":
        buy_idx = d.index[d["buy_mark"].fillna(False)]
        sell_idx = d.index[d["sell_mark"].fillna(False)]

        fig.add_trace(
            go.Scatter(
                x=buy_idx,
                y=d.loc[buy_idx, "Close"],
                mode="markers",
                name="Buy",
                marker=dict(symbol="triangle-up", size=12, color="#00C853"),
                hovertemplate="Buy<br>%{x|%Y-%m-%d}<br>Close=%{y:.2f}<extra></extra>",
            )
        )

        # Split sell markers by exit reason
        stop_mask = d["exit_reason"].astype(str).eq("Stop Loss")
        sma_mask = d["exit_reason"].astype(str).eq("SMA20 Trailing Exit")
        stop_idx = d.index[d["sell_mark"].fillna(False) & stop_mask]
        sma_idx = d.index[d["sell_mark"].fillna(False) & sma_mask]
        other_idx = d.index[d["sell_mark"].fillna(False) & ~(stop_mask | sma_mask)]

        if len(stop_idx):
            fig.add_trace(
                go.Scatter(
                    x=stop_idx,
                    y=d.loc[stop_idx, "Close"],
                    mode="markers",
                    name="Sell (Stop Loss)",
                    marker=dict(symbol="triangle-down", size=12, color="#FF5252"),
                    hovertemplate="Stop Loss Exit<br>%{x|%Y-%m-%d}<br>Close=%{y:.2f}<extra></extra>",
                )
            )
        if len(sma_idx):
            fig.add_trace(
                go.Scatter(
                    x=sma_idx,
                    y=d.loc[sma_idx, "Close"],
                    mode="markers",
                    name="Sell (SMA20 Exit)",
                    marker=dict(symbol="triangle-down", size=12, color="#FFB300"),
                    hovertemplate="SMA20 Exit<br>%{x|%Y-%m-%d}<br>Close=%{y:.2f}<extra></extra>",
                )
            )
        if len(other_idx):
            fig.add_trace(
                go.Scatter(
                    x=other_idx,
                    y=d.loc[other_idx, "Close"],
                    mode="markers",
                    name="Sell",
                    marker=dict(symbol="triangle-down", size=12, color="#FF5252"),
                )
            )

    else:
        # Simple: infer entries/exits from position diff
        chg = d["position"].diff().fillna(0)
        buy_idx = d.index[chg == 1]
        sell_idx = d.index[chg == -1]
        fig.add_trace(
            go.Scatter(
                x=buy_idx,
                y=d.loc[buy_idx, "Close"],
                mode="markers",
                name="Buy",
                marker=dict(symbol="triangle-up", size=12, color="#00C853"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=sell_idx,
                y=d.loc[sell_idx, "Close"],
                mode="markers",
                name="Sell",
                marker=dict(symbol="triangle-down", size=12, color="#FF5252"),
            )
        )

    fig.update_layout(
        title="Price with Buy/Sell Signals",
        xaxis_title="Date",
        yaxis_title="Price",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        height=460,
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Technical Strategy Backtester", layout="wide")
    st.title("Technical Strategy Backtester")
    st.caption("Data: yfinance • Indicators: pandas_ta • Charts: plotly • For research/education only.")

    with st.sidebar:
        st.header("Parameters")
        ticker = st.text_input("Ticker", value="SPY").strip().upper() or "SPY"

        end_d = date.today()
        start_d = st.date_input("Start date", value=end_d - timedelta(days=365 * 10))
        end_d_in = st.date_input("End date", value=end_d)
        if start_d >= end_d_in:
            st.error("Start date must be before end date.")
            st.stop()

        initial_capital = st.number_input(
            "Initial capital ($)",
            min_value=100.0,
            max_value=10_000_000.0,
            value=10_000.0,
            step=500.0,
            format="%.0f",
        )

        st.divider()
        mode = st.selectbox("Strategy mode", ["Advanced", "Simple (vectorized)"], index=0)

        st.subheader("Indicator settings")
        rsi_len = st.slider("RSI length", 5, 50, 14, 1)
        sma_len = st.slider("SMA length (Simple mode)", 20, 300, 200, 5)

        st.subheader("Simple strategy thresholds")
        rsi_buy = st.slider("RSI buy threshold (RSI < x)", 1, 60, 30, 1)
        rsi_sell = st.slider("RSI sell threshold (RSI > x)", 40, 99, 70, 1)

        st.subheader("Advanced strategy settings")
        sma_200_len = 200
        sma_20_len = 20
        atr_len = st.slider("ATR length", 5, 50, 14, 1)
        atr_mult = st.slider("Stop loss ATR multiple", 0.5, 5.0, 2.0, 0.25)

        run = st.button("Run backtest", type="primary", width="stretch")

    if not run:
        st.info("Set parameters in the sidebar, then click **Run backtest**.")
        return

    with st.spinner("Downloading data…"):
        raw = load_ohlcv(ticker, start_d, end_d_in)
    if raw.empty or len(raw) < 250:
        st.error("Not enough data returned. Try a longer period or a different ticker.")
        return

    with st.spinner("Computing indicators…"):
        df = add_indicators(
            raw,
            rsi_len=rsi_len,
            sma_len=sma_len,
            sma_200_len=sma_200_len,
            sma_20_len=sma_20_len,
            atr_len=atr_len,
        )
        df = df.dropna().copy()
    if df.empty:
        st.error("Indicators produced no usable rows (too few periods).")
        return

    with st.spinner("Running strategy…"):
        if mode == "Advanced":
            res = backtest_advanced_atr_stop_sma20(
                df=df,
                rsi_len=rsi_len,
                rsi_buy=float(rsi_buy),
                sma_200_len=sma_200_len,
                sma_20_len=sma_20_len,
                atr_len=atr_len,
                atr_mult=float(atr_mult),
                initial_capital=float(initial_capital),
            )
        else:
            res = backtest_simple_vectorized(
                df=df,
                sma_len=sma_len,
                rsi_len=rsi_len,
                rsi_buy=float(rsi_buy),
                rsi_sell=float(rsi_sell),
                initial_capital=float(initial_capital),
            )

    m = perf_metrics(res, float(initial_capital))

    st.subheader("1) Performance metrics")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Return", _pct(m.get("total_return", np.nan)))
    with c2:
        st.metric("Annualized Return", _pct(m.get("annualized_return", np.nan)))
    with c3:
        st.metric("Max Drawdown", _pct(m.get("max_drawdown", np.nan)))
    with c4:
        st.metric("Win Rate", _pct(m.get("win_rate", np.nan)))
    with c5:
        st.metric("Buy & Hold Return", _pct(m.get("buy_hold_return", np.nan)))

    st.caption(
        f"Initial capital: **{_money(float(initial_capital))}** • "
        f"Rows used: **{len(res.df):,}** • Trades: **{0 if res.trades is None else len(res.trades):,}**"
    )

    st.subheader("2) Equity curve")
    st.plotly_chart(plot_equity(res), use_container_width=True)

    st.subheader("3) Price with trade markers")
    st.plotly_chart(plot_price_signals(res, "Advanced" if mode == "Advanced" else "Simple"), use_container_width=True)

    with st.expander("Trades (entry/exit)", expanded=False):
        if res.trades is None or res.trades.empty:
            st.info("No completed trades.")
        else:
            tdf = res.trades.copy()
            tdf["entry_date"] = pd.to_datetime(tdf["entry_date"]).dt.strftime("%Y-%m-%d")
            tdf["exit_date"] = pd.to_datetime(tdf["exit_date"]).dt.strftime("%Y-%m-%d")
            tdf["pnl_pct"] = (tdf["pnl_pct"] * 100.0).round(2)
            tdf = tdf.rename(
                columns={
                    "entry_date": "Entry",
                    "exit_date": "Exit",
                    "entry_px": "Entry Px",
                    "exit_px": "Exit Px",
                    "pnl_pct": "PnL %",
                    "exit_reason": "Exit reason",
                }
            )
            st.dataframe(tdf, use_container_width=True, hide_index=True)

    with st.expander("Data preview (indicators)", expanded=False):
        show_cols = ["Open", "High", "Low", "Close", "Volume", "ret"]
        show_cols += [c for c in res.df.columns if c.startswith("SMA_") or c.startswith("RSI_") or c.startswith("ATR_")]
        show = res.df[show_cols].tail(200).copy()
        st.dataframe(show, use_container_width=True)


if __name__ == "__main__":
    main()

