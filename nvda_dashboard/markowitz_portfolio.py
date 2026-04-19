"""
Markowitz efficient frontier & portfolio optimization (multi-page app module).
Do not call st.set_page_config here — the entrypoint app.py sets it.
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
from scipy.optimize import minimize

warnings.filterwarnings("ignore", category=FutureWarning)

TRADING_DAYS = 252
N_MONTE_CARLO = 10_000


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
    x0 = np.ones(n) / n
    bounds = tuple((0.0, 1.0) for _ in range(n))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    res = minimize(
        neg_sharpe,
        x0,
        args=(mu, cov, rf),
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    if not res.success:
        st.warning(f"Max-Sharpe optimizer: {res.message}")
    w = np.clip(res.x, 0.0, 1.0)
    s = w.sum()
    return w / s if s > 0 else x0


def optimize_min_volatility(cov: np.ndarray) -> np.ndarray:
    n = cov.shape[0]
    x0 = np.ones(n) / n
    bounds = tuple((0.0, 1.0) for _ in range(n))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    def obj(w: np.ndarray) -> float:
        return portfolio_volatility(w, cov) ** 2

    res = minimize(
        obj,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    if not res.success:
        st.warning(f"Min-vol optimizer: {res.message}")
    w = np.clip(res.x, 0.0, 1.0)
    s = w.sum()
    return w / s if s > 0 else x0


def monte_carlo_portfolios(
    mu: np.ndarray,
    cov: np.ndarray,
    rf: float,
    n_sims: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    n = len(mu)
    W = rng.dirichlet(np.ones(n), size=n_sims)
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
    st.title("Markowitz efficient frontier & portfolio optimization")
    st.caption(
        "Mean–variance optimization with Monte Carlo sampling and SciPy constrained solvers. "
        "For education and research only — not investment advice."
    )

    default_end = date.today()
    default_start = default_end - timedelta(days=365 * 5)
    defaults = ["NVDA", "AAPL", "MSFT", "TLT", "GLD", "", "", "", "", ""]

    with st.sidebar:
        st.header("Inputs")
        tickers_in: list[str] = []
        for i in range(10):
            lab = f"Ticker {i + 1}"
            v = st.text_input(lab, value=defaults[i], key=f"mk_t{i}")
            tickers_in.append(v)

        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("Start date", value=default_start, key="mk_start")
        with c2:
            end_d = st.date_input("End date", value=default_end, key="mk_end")

        rf = st.number_input(
            "Risk-free rate (annual, decimal)",
            min_value=0.0,
            max_value=0.5,
            value=0.02,
            step=0.005,
            format="%.4f",
            help="e.g. 0.02 = 2%",
            key="mk_rf",
        )

        run = st.button("Run optimization", type="primary", width="stretch", key="mk_run")

    tickers = _parse_tickers(tickers_in)
    if not tickers:
        st.info("Enter at least one ticker in the sidebar.")
        return

    if start_d >= end_d:
        st.error("Start date must be before end date.")
        return

    if not run:
        st.info("Set tickers and dates, then click **Run optimization**.")
        return

    try:
        with st.spinner("Downloading prices and building returns…"):
            prices = fetch_adj_close(tickers, start_d, end_d)
            cols = [c for c in tickers if c in prices.columns]
            if len(cols) < len(tickers):
                missing = set(tickers) - set(cols)
                st.warning(f"No data for: {', '.join(sorted(missing))}. Using: {', '.join(cols)}")
            if len(cols) < 2:
                st.error("Need at least two assets with data to build a covariance matrix.")
                return
            prices = prices[cols]
            daily_ret = prices.pct_change().dropna()
            mu_ann, cov_ann = ann_stats(daily_ret)
            corr = daily_ret.corr()

        rng = np.random.default_rng(42)
        with st.spinner(f"Monte Carlo: {N_MONTE_CARLO:,} portfolios…"):
            mc = monte_carlo_portfolios(mu_ann, cov_ann, rf, N_MONTE_CARLO, rng)

        with st.spinner("SciPy: max Sharpe & min volatility…"):
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

    st.subheader("1. Efficient frontier (Monte Carlo + optima)")
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
        title=f"{N_MONTE_CARLO:,} random long-only portfolios (color = Sharpe)",
        width=None,
        height=520,
    )
    fig.add_trace(
        go.Scatter(
            x=[v_ms],
            y=[r_ms],
            mode="markers",
            marker=dict(symbol="star", size=22, color="gold", line=dict(width=1, color="white")),
            name="Max Sharpe (SciPy)",
            hovertemplate="Max Sharpe<br>σ=%{x:.4f}<br>μ=%{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[v_mv],
            y=[r_mv],
            mode="markers",
            marker=dict(symbol="star", size=22, color="cyan", line=dict(width=1, color="white")),
            name="Min volatility (SciPy)",
            hovertemplate="Min vol<br>σ=%{x:.4f}<br>μ=%{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    st.plotly_chart(fig, width="stretch")

    st.subheader("2. Optimal weights (pie charts + tables)")
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("**Max-Sharpe portfolio** " f"(Sharpe ≈ {sr_ms:.3f})")
        df_ms = pd.DataFrame({"Asset": cols, "Weight %": w_max_sharpe * 100.0}).sort_values(
            "Weight %", ascending=False
        )
        fig_p1 = px.pie(
            df_ms,
            names="Asset",
            values="Weight %",
            hole=0.35,
            title="Weights — max Sharpe",
        )
        fig_p1.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_p1, width="stretch")
        df_ms["Weight %"] = df_ms["Weight %"].round(2)
        st.dataframe(df_ms, width="stretch", hide_index=True)

    with c_right:
        st.markdown("**Min-volatility portfolio** " f"(Sharpe ≈ {sr_mv:.3f})")
        df_mv = pd.DataFrame({"Asset": cols, "Weight %": w_min_vol * 100.0}).sort_values(
            "Weight %", ascending=False
        )
        fig_p2 = px.pie(
            df_mv,
            names="Asset",
            values="Weight %",
            hole=0.35,
            title="Weights — min volatility",
        )
        fig_p2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_p2, width="stretch")
        df_mv["Weight %"] = df_mv["Weight %"].round(2)
        st.dataframe(df_mv, width="stretch", hide_index=True)

    st.subheader("3. Historical correlation heatmap (daily returns)")
    fig_h = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation matrix of daily returns",
    )
    fig_h.update_layout(height=480)
    st.plotly_chart(fig_h, width="stretch")

    with st.expander("Methodology"):
        st.markdown(
            """
- **Returns:** simple daily returns; annualized mean `× 252`, covariance `× 252`.
- **Long-only:** weights ∈ [0,1], sum to 1.
- **Max Sharpe:** maximize `(μ'w − rf) / √(w'Σw)` via `scipy.optimize.minimize` (SLSQP).
- **Min variance:** minimize `w'Σw` under the same constraints.
- **Monte Carlo:** Dirichlet samples → uniform random weights on the simplex.
            """
        )


main()
