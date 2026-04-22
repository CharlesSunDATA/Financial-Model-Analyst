"""
Markowitz efficient frontier & portfolio optimization — Streamlit dashboard.
"""

from __future__ import annotations

import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from scipy.optimize import Bounds, LinearConstraint, minimize

warnings.filterwarnings("ignore", category=FutureWarning)

TRADING_DAYS = 252
N_MONTE_CARLO = 10_000

WEIGHT_MIN = 0.05
WEIGHT_MAX = 0.2
MIN_ASSETS_FOR_WEIGHT_CAP = 5
MAX_ASSETS_FOR_WEIGHT_FLOOR = 20
OPTIMIZER_BUILD_ID = "min5-max20-per-asset-bounds-2026-04"


def _weight_bounds(n: int) -> tuple[tuple[float, float], ...]:
    return tuple((WEIGHT_MIN, WEIGHT_MAX) for _ in range(n))


def _feasible_weight_cap(n: int) -> bool:
    return (
        n >= MIN_ASSETS_FOR_WEIGHT_CAP
        and n <= MAX_ASSETS_FOR_WEIGHT_FLOOR
        and n * WEIGHT_MAX >= 1.0 - 1e-12
        and n * WEIGHT_MIN <= 1.0 + 1e-12
    )


def _budget_constraint(n: int) -> LinearConstraint:
    return LinearConstraint(np.ones((1, n)), 1.0, 1.0)


def _feasible_start(n: int) -> np.ndarray:
    w = np.full(n, WEIGHT_MIN, dtype=float)
    remaining = 1.0 - float(n) * WEIGHT_MIN
    if remaining <= 0:
        return np.full(n, 1.0 / n, dtype=float)
    w += remaining / n
    w = np.clip(w, WEIGHT_MIN, WEIGHT_MAX)
    return w / w.sum()


def _weights_feasible(w: np.ndarray) -> bool:
    s = float(w.sum())
    if abs(s - 1.0) > 5e-4:
        return False
    if float(w.max()) > WEIGHT_MAX + 1e-5 or float(w.min()) < WEIGHT_MIN - 1e-5:
        return False
    return True


def _parse_tickers(raw: list[str]) -> list[str]:
    out: list[str] = []
    for s in raw:
        t = (s or "").strip().upper()
        if t and t not in out:
            out.append(t)
    return out


def fetch_adj_close(
    tickers: list[str],
    start: date,
    end: date,
) -> pd.DataFrame:
    """Download adjusted close for all tickers; align on dates."""
    if not tickers:
        raise ValueError("At least one ticker is required.")
    data = yf.download(
        tickers,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if data.empty:
        raise ValueError("No price data returned. Check tickers and date range.")

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"].copy()
        else:
            prices = data.xs("Close", axis=1, level=0, drop_level=True)
    else:
        prices = data[["Close"]].copy() if "Close" in data.columns else data.copy()
        if len(tickers) == 1:
            prices.columns = [tickers[0]]

    prices = prices.dropna(how="all").ffill().dropna()
    if prices.empty or len(prices) < 30:
        raise ValueError("Insufficient overlapping history after cleaning. Try a wider date range.")
    return prices.astype(float)


def ann_stats(returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Annualized mean returns vector and covariance matrix."""
    mu_daily = returns.mean().values
    cov_daily = returns.cov().values
    mu_ann = mu_daily * TRADING_DAYS
    cov_ann = cov_daily * TRADING_DAYS
    return mu_ann, cov_ann


def portfolio_return(w: np.ndarray, mu: np.ndarray) -> float:
    return float(np.dot(w, mu))


def portfolio_volatility(w: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(w @ cov @ w, 0.0)))


def neg_sharpe(
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float,
) -> float:
    vol = portfolio_volatility(w, cov)
    if vol < 1e-12:
        return 1e12
    return -(portfolio_return(w, mu) - rf) / vol


def optimize_max_sharpe(mu: np.ndarray, cov: np.ndarray, rf: float) -> np.ndarray:
    n = len(mu)
    x0 = _feasible_start(n)
    bounds = Bounds(WEIGHT_MIN, WEIGHT_MAX, keep_feasible=True)
    lc = _budget_constraint(n)
    res = minimize(
        neg_sharpe,
        x0,
        args=(mu, cov, rf),
        method="trust-constr",
        bounds=bounds,
        constraints=[lc],
        options={"maxiter": 3000, "gtol": 1e-8},
    )
    w = np.asarray(res.x, dtype=float)
    if not res.success:
        st.warning(f"Max-Sharpe (trust-constr): {res.message}")
    if not _weights_feasible(w):
        res2 = minimize(
            neg_sharpe,
            _feasible_start(n),
            args=(mu, cov, rf),
            method="SLSQP",
            bounds=_weight_bounds(n),
            constraints={"type": "eq", "fun": lambda ww: float(np.sum(ww)) - 1.0},
            options={"maxiter": 3000, "ftol": 1e-11},
        )
        w = np.asarray(res2.x, dtype=float)
        if not res2.success:
            st.warning(f"Max-Sharpe (SLSQP fallback): {res2.message}")
    return np.clip(w, WEIGHT_MIN, WEIGHT_MAX)


def optimize_min_volatility(cov: np.ndarray) -> np.ndarray:
    n = cov.shape[0]
    x0 = _feasible_start(n)
    bounds = Bounds(WEIGHT_MIN, WEIGHT_MAX, keep_feasible=True)
    lc = _budget_constraint(n)

    def obj(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    res = minimize(
        obj,
        x0,
        method="trust-constr",
        bounds=bounds,
        constraints=[lc],
        options={"maxiter": 3000, "gtol": 1e-8},
    )
    w = np.asarray(res.x, dtype=float)
    if not res.success:
        st.warning(f"Min-vol (trust-constr): {res.message}")
    if not _weights_feasible(w):
        cons = {"type": "eq", "fun": lambda ww: float(np.sum(ww)) - 1.0}
        res2 = minimize(
            obj,
            _feasible_start(n),
            method="SLSQP",
            bounds=_weight_bounds(n),
            constraints=cons,
            options={"maxiter": 3000, "ftol": 1e-11},
        )
        w = np.asarray(res2.x, dtype=float)
        if not res2.success:
            st.warning(f"Min-vol (SLSQP fallback): {res2.message}")
    return np.clip(w, WEIGHT_MIN, WEIGHT_MAX)


def _sample_capped_simplex_weights(
    n: int,
    rng: np.random.Generator,
    n_sims: int,
) -> np.ndarray:
    """
    Random portfolios on {w : sum w = 1, WEIGHT_MIN <= w_i <= WEIGHT_MAX}.
    Rejection sampling on Dirichlet(α); α is raised if acceptance is too low.
    When 1 - n×WEIGHT_MIN = 0, the feasible set is a single point (all weights = WEIGHT_MIN).
    """
    if not _feasible_weight_cap(n):
        raise ValueError("Infeasible weight bounds for this n.")
    remaining_mass = 1.0 - float(n) * WEIGHT_MIN
    if abs(remaining_mass) < 1e-12:
        return np.tile(np.full(n, WEIGHT_MIN, dtype=float), (n_sims, 1))

    u_cap = (WEIGHT_MAX - WEIGHT_MIN) / remaining_mass

    out: list[np.ndarray] = []
    alpha = max(12.0, float(n) * 2.0)
    attempts = 0
    max_attempts = max(500_000, n_sims * 500)
    while len(out) < n_sims and attempts < max_attempts:
        batch = min(65536, (n_sims - len(out)) * 4 + 1024)
        W = rng.dirichlet(np.ones(n) * alpha, size=batch)
        attempts += batch
        for u in W:
            if float(u.max()) <= u_cap + 1e-12:
                w = WEIGHT_MIN + remaining_mass * np.asarray(u, dtype=np.float64)
                out.append(w)
                if len(out) >= n_sims:
                    break
        if len(out) < max(1, n_sims // 100) and attempts >= n_sims * 20:
            alpha *= 1.35

    while len(out) < n_sims:
        out.append(_feasible_start(n))
    return np.stack(out[:n_sims], axis=0)


def monte_carlo_portfolios(
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float,
    n_sims: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    n = len(mu)
    W = _sample_capped_simplex_weights(n, rng, n_sims)
    rows: list[dict] = []
    for i in range(n_sims):
        w = W[i]
        ret = portfolio_return(w, mu)
        vol = portfolio_volatility(w, cov)
        sharpe = (ret - rf) / vol if vol > 1e-12 else np.nan
        rows.append(
            {
                "sim_id": i,
                "ann_return": ret,
                "ann_volatility": vol,
                "sharpe_ratio": sharpe,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    st.set_page_config(
        page_title="Markowitz Portfolio Optimizer",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("馬可維茲效率前緣與投資組合最佳化")
    st.caption(
        f"**Build `{OPTIMIZER_BUILD_ID}`** — 蒙地卡羅 + SciPy **trust-constr**（明確 **Bounds**）。"
        f"最大夏普／最小波動：每檔 **{WEIGHT_MIN:.0%}–{WEIGHT_MAX:.0%}**（每檔都有配置，不會是 0%），"
        f"需 **{MIN_ASSETS_FOR_WEIGHT_CAP}–{MAX_ASSETS_FOR_WEIGHT_FLOOR}** 檔標的。"
        "僅供教育與研究，非投資建議。"
    )

    default_end = date.today()
    default_start = default_end - timedelta(days=365 * 5)
    defaults = ["NVDA", "AAPL", "MSFT", "TLT", "GLD", "", "", "", "", ""]

    with st.sidebar:
        st.header("參數設定")
        tickers_in: list[str] = []
        for i in range(10):
            lab = f"股票代號 {i + 1}"
            v = st.text_input(lab, value=defaults[i], key=f"t{i}")
            tickers_in.append(v)

        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("開始日期", value=default_start)
        with c2:
            end_d = st.date_input("結束日期", value=default_end)

        rf = st.number_input(
            "無風險利率（年化，小數）",
            min_value=0.0,
            max_value=0.5,
            value=0.02,
            step=0.005,
            format="%.4f",
            help="e.g. 0.02 = 2%",
        )

        run = st.button("🚀 開始最佳化計算", type="primary", width="stretch")

    tickers = _parse_tickers(tickers_in)
    if not tickers:
        st.info("請在側邊欄至少輸入一檔股票代號。")
        return

    if start_d >= end_d:
        st.error("開始日期必須早於結束日期。")
        return

    if not run:
        st.info("設定 ticker 與日期後，點擊 **🚀 開始最佳化計算**。")
        return

    try:
        with st.spinner("下載價格並建立報酬序列…"):
            prices = fetch_adj_close(tickers, start_d, end_d)
            # yfinance may reorder / subset columns
            cols = [c for c in tickers if c in prices.columns]
            if len(cols) < len(tickers):
                missing = set(tickers) - set(cols)
                st.warning(f"以下代號無資料已略過：{', '.join(sorted(missing))}。使用：{', '.join(cols)}")
            if len(cols) < 2:
                st.error("至少需要兩檔有資料的資產才能建立共變異數矩陣。")
                return
            if not _feasible_weight_cap(len(cols)):
                st.error(
                    f"每檔權重限制 **{WEIGHT_MIN:.0%}–{WEIGHT_MAX:.0%}** 時，需要 **{MIN_ASSETS_FOR_WEIGHT_CAP}–"
                    f"{MAX_ASSETS_FOR_WEIGHT_FLOOR}** 檔有資料的標的，權重才能加總為 100%。請調整側欄代號。"
                )
                return
            prices = prices[cols]
            daily_ret = prices.pct_change().dropna()
            mu_ann, cov_ann = ann_stats(daily_ret)
            corr = daily_ret.corr()

        rng = np.random.default_rng(42)
        with st.spinner(f"蒙地卡羅模擬 {N_MONTE_CARLO:,} 組投資組合…"):
            mc = monte_carlo_portfolios(mu_ann, cov_ann, rf, N_MONTE_CARLO, rng)

        with st.spinner("SciPy：最大夏普與最小波動…"):
            w_max_sharpe = optimize_max_sharpe(mu_ann, cov_ann, rf)
            w_min_vol = optimize_min_volatility(cov_ann)

        r_ms = portfolio_return(w_max_sharpe, mu_ann)
        v_ms = portfolio_volatility(w_max_sharpe, cov_ann)
        sr_ms = (r_ms - rf) / v_ms if v_ms > 1e-12 else np.nan

        r_mv = portfolio_return(w_min_vol, mu_ann)
        v_mv = portfolio_volatility(w_min_vol, cov_ann)
        sr_mv = (r_mv - rf) / v_mv if v_mv > 1e-12 else np.nan

    except Exception as e:
        st.error(str(e))
        return

    st.subheader("一、效率前緣散佈圖（蒙地卡羅 + 最佳化切點）")
    fig = px.scatter(
        mc,
        x="ann_volatility",
        y="ann_return",
        color="sharpe_ratio",
        color_continuous_scale="Viridis",
        opacity=0.35,
        labels={
            "ann_volatility": "Annualized volatility (σ)",
            "ann_return": "Annualized expected return (μ)",
            "sharpe_ratio": "Sharpe ratio",
        },
        title=(
            f"{N_MONTE_CARLO:,} 組隨機長倉組合（每檔權重 {WEIGHT_MIN:.0%}–{WEIGHT_MAX:.0%}；顏色 = 夏普比率）"
        ),
        width=None,
        height=520,
    )
    fig.add_trace(
        go.Scatter(
            x=[v_ms],
            y=[r_ms],
            mode="markers",
            marker=dict(symbol="star", size=22, color="gold", line=dict(width=1, color="white")),
            name="最大夏普（SciPy）⭐",
            hovertemplate="最大夏普<br>σ=%{x:.4f}<br>μ=%{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[v_mv],
            y=[r_mv],
            mode="markers",
            marker=dict(symbol="star", size=22, color="cyan", line=dict(width=1, color="white")),
            name="最小波動（SciPy）⭐",
            hovertemplate="最小波動<br>σ=%{x:.4f}<br>μ=%{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    st.plotly_chart(fig, width="stretch")

    st.subheader("二、最佳權重分配（圓餅圖 + 明細表）")
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("**最大夏普投資組合** " f"(Sharpe ≈ {sr_ms:.3f})")
        df_ms = pd.DataFrame({"Asset": cols, "Weight %": w_max_sharpe * 100.0}).sort_values(
            "Weight %", ascending=False
        )
        fig_p1 = px.pie(
            df_ms,
            names="Asset",
            values="Weight %",
            hole=0.35,
            title="權重 — 最大夏普",
        )
        fig_p1.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_p1, width="stretch")
        df_ms["Weight %"] = df_ms["Weight %"].round(2)
        st.dataframe(df_ms, width="stretch", hide_index=True)

    with c_right:
        st.markdown("**最小波動投資組合** " f"(Sharpe ≈ {sr_mv:.3f})")
        df_mv = pd.DataFrame({"Asset": cols, "Weight %": w_min_vol * 100.0}).sort_values(
            "Weight %", ascending=False
        )
        fig_p2 = px.pie(
            df_mv,
            names="Asset",
            values="Weight %",
            hole=0.35,
            title="權重 — 最小波動",
        )
        fig_p2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_p2, width="stretch")
        df_mv["Weight %"] = df_mv["Weight %"].round(2)
        st.dataframe(df_mv, width="stretch", hide_index=True)

    st.subheader("三、歷史相關係數熱力圖（日報酬）")
    fig_h = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="日報酬相關係數矩陣",
    )
    fig_h.update_layout(height=480)
    st.plotly_chart(fig_h, width="stretch")

    with st.expander("方法說明（英文）"):
        st.markdown(
            f"""
- **Returns:** simple daily returns; annualized mean `× 252`, covariance `× 252`.
- **Long-only with bounds:** each `w_i ∈ [{WEIGHT_MIN}, {WEIGHT_MAX}]`, `∑w = 1`. This forces diversification: every name has at least **{WEIGHT_MIN:.0%}**, and no name exceeds **{WEIGHT_MAX:.0%}**.
- **Max Sharpe:** `scipy.optimize.minimize` (**trust-constr** + `Bounds` + `LinearConstraint`; SLSQP fallback).
- **Min variance:** minimize `w'Σw` under the same constraints (same solvers).
- **Monte Carlo:** Dirichlet rejection sampling with the **same** per-asset cap as SciPy (when `n × cap = 1` the cloud is the unique equal-weight portfolio).
            """
        )


if __name__ == "__main__":
    main()
