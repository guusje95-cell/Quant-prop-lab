"""Strategy scorecard: every strategy on its OWN natural data set (the market it was designed for), with one row of
statistics each and its prop-firm outcome. Setups are defaults, not tuned; edit SETUPS to change them.

A setup lists data sources in order of preference (built-in names in the cloud, `Downloaded: ...` names on a PC after
`python -m qpl.lab.setup_data`), so the same scorecard works in both places. Strategies without a setup (your own
plug-ins) are run on whatever data is selected in the sidebar."""
from __future__ import annotations

import numpy as np
import pandas as pd

from qpl.lab import analysis as A, data as D, engine as EN, propfirms as PF

CRYPTO = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK"]
CRYPTO_SRC = ["Binance spot majors (daily, 2017+)", "Downloaded: crypto_majors_1d"]
METALS_ENERGY = ["GOLD", "SILVER", "PLAT", "PALLAD", "COPPER", "CRUDE_W", "HEATOIL", "GASOILINE", "GAS_US"]

SETUPS = {
    "C* trend + breakout (E2)": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01",
                                     market="crypto 10 majors, daily"),
    "C* + BTC leads (Gen53)": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01",
                                    market="crypto 10 majors, daily", params={"btc_leads": True}, strategy="C* trend + breakout (E2)"),
    "Buy & hold (benchmark)": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01", market="crypto 10 majors, daily"),
    "Moving-average crossover": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01", market="crypto 10 majors, daily"),
    "Donchian channel breakout (turtle)": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01", market="crypto 10 majors, daily"),
    "Time-series momentum": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01", market="crypto 10 majors, daily"),
    "RSI mean reversion": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79, start="2018-01-01", market="crypto 10 majors, daily"),
    "Paper: Kalman pairs (DTW + cointegration)": dict(sources=["Futures daily, 250 markets (pysystemtrade, to 2024-03)", "Downloaded: futures_daily"],
                                                      symbols=METALS_ENERGY, tf="1d", cost=2.0, lev=1.0, start="2008-01-01", market="US metals + energy futures, daily"),
    "Paper: MaxAI Q-learning (intraday, money flow)": dict(sources=["US100 CFD, Dukascopy (5-min, 2020-23)", "Downloaded: index_cfd_M5"], symbols=["US100"],
                                                           tf="5m", cost=0.3, lev=1.0, start=None, market="Nasdaq-100 CFD, 5-min"),
    "Paper: Market intraday momentum (Gao et al. 2018)": dict(sources=["US500 CFD, Dukascopy (15-min)", "Downloaded: index_cfd_M15"], symbols=["US500"],
                                                              tf="15m", cost=1.0, lev=1.0, start=None, market="S&P 500 CFD, 15-min"),
    "Paper: Beat the Market noise-area breakout (Zarattini et al. 2024)": dict(sources=["US100 CFD, Dukascopy (15-min)", "Downloaded: index_cfd_M15"],
                                                                              symbols=["US100"], tf="15m", cost=1.0, lev=1.0, start=None,
                                                                              market="Nasdaq-100 CFD, 15-min"),
    "Paper: Catching Crypto Trends ensemble (Zarattini et al. 2025)": dict(sources=CRYPTO_SRC, symbols=CRYPTO, tf="1d", cost=7.5, lev=0.79,
                                                                           start="2018-01-01", market="crypto 10 majors, daily"),
    "Paper: Commodity curve slope dynamics (Bianchi et al. 2023)": dict(sources=["Commodity futures curve, 3 contracts (daily, to 2024-03)"],
                                                                        symbols=[], tf="1d", cost=8.0, lev=1.0, start="2000-01-01",
                                                                        market="~28 commodity futures curves, daily"),
    "Paper: Overnight returns of stock indexes (Liu & Tse 2017)": dict(sources=["US500 CFD, Dukascopy (15-min)", "Downloaded: index_cfd_M15"],
                                                                       symbols=["US500"], tf="15m", cost=1.0, lev=1.0, start=None,
                                                                       market="S&P 500 CFD, 15-min"),
    "Paper: TS momentum + realized semivariance (Liu et al. 2023)": dict(
        sources=["Dukascopy 13 CFDs: indices, gold, silver, Brent, FX (hourly, 2013-23)", "Downloaded: dukascopy13_1h"],
        symbols=["US500", "US100", "US30", "DE40", "XAUUSD", "XAGUSD", "BRENT", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"],
        tf="1h", cost=2.0, lev=0.25, start="2013-06-01", market="13 CFDs (indices, metals, oil, FX), hourly"),
    "Paper: Volatility-managed portfolio (Moreira & Muir 2017)": dict(sources=["Futures daily, 250 markets (pysystemtrade, to 2024-03)", "Downloaded: futures_daily"],
                                                                      symbols=["SP500"], tf="1d", cost=1.0, lev=1.0, start="1991-01-01",
                                                                      market="S&P 500 futures, daily"),
    "Paper: Long around the European open (Bondarenko & Muravyev 2021)": dict(sources=["US500 CFD, Dukascopy (15-min)", "Downloaded: index_cfd_M15"],
                                                                               symbols=["US500"], tf="15m", cost=1.0, lev=1.0, start=None,
                                                                               market="S&P 500 CFD, 15-min"),
    "Paper: Commodity momentum along the curve (de Groot et al. 2014)": dict(sources=["Commodity futures curve, 3 contracts (daily, to 2024-03)"],
                                                                             symbols=[], tf="1d", cost=8.0, lev=0.5, start="2000-01-01",
                                                                             market="~28 commodity futures curves, daily"),
}


def resolve(setup: dict, sources: dict):
    for s in setup["sources"]:
        if s in sources:
            return s
    return None


def run(strategy_cls, bars, setup: dict) -> dict:
    """Backtest with the setup's costs / leverage; returns daily results (after warm-up) and the held positions."""
    st = strategy_cls(); p = {**st.defaults(), **setup.get("params", {})}
    cfg = EN.Config(cost_bps=setup["cost"], leverage=setup["lev"])
    sig = st.signal(bars, p)
    r = EN.run(bars, EN.size(bars, sig, cfg, st.sizing), cfg)
    daily = EN.to_daily(r["bars"], bars.freq)
    held = r["held"]
    active = held.abs().sum(axis=1) > 0
    first = held.index[active.to_numpy()][0] if active.any() else held.index[0]
    t0 = max(pd.Timestamp(setup["start"]), first.floor("D")) if setup.get("start") else first.floor("D")
    if bars.freq != "1d":
        daily = daily[daily.index.dayofweek < 5]
    return {"daily": daily.loc[t0:], "held": held.loc[t0:], "close": bars.close.loc[t0:]}


def stats(out: dict, n_trials: int) -> dict:
    d = out["daily"]["net"]
    ppy = D.periods_per_year(d.index, "1d")
    S = A.summary(d, ppy)
    tr = EN.trades(out["held"], out["close"])
    wins = tr[tr.pnl_contribution > 0]; loss = tr[tr.pnl_contribution <= 0]
    m = (1 + d).resample("ME").prod() - 1
    return {"From": d.index[0].date(), "To": d.index[-1].date(), "Years": S.get("Years"), "Sharpe": S.get("Sharpe"), "CAGR": S.get("CAGR"),
            "Volatility": S.get("Volatility"), "Max drawdown": S.get("Max drawdown"), "Calmar": S.get("Calmar"), "Sortino": S.get("Sortino"),
            "Positive months": S.get("Positive months"), "Avg month": float(m.mean()), "Worst month": S.get("Worst month"),
            "Best month": S.get("Best month"), "Worst day (intraday)": float(out["daily"]["worst"].min()),
            "Trades / year": len(tr) / max(S.get("Years") or 1, 1e-9),
            "Win rate": len(wins) / len(tr) if len(tr) else np.nan,
            "Profit factor": wins.pnl_contribution.sum() / -loss.pnl_contribution.sum() if len(loss) and loss.pnl_contribution.sum() < 0 else np.nan,
            "Prob. Sharpe > 0": A.psr(d, ppy), f"Deflated Sharpe ({n_trials} trials)": A.dsr(d, ppy, n_trials)}


def prop(out: dict, firm: PF.Firm, budget: int, accounts: int, scale_c: float, scale_f: float, horizon_days: int) -> dict:
    d = out["daily"]
    a = PF.attempts(d, firm, scale_c)
    p = PF.pipeline(d, firm, budget, accounts, scale_c, scale_f, horizon_days=horizon_days)
    if p.get("n", 0) < 50:                               # too little data for the horizon: bootstrap the daily results instead
        p = PF.pipeline(d, firm, budget, accounts, scale_c, scale_f, horizon_days=horizon_days, method="bootstrap", n_boot=300)
        p["method"] = "bootstrap"
    else:
        p["method"] = "historical"
    return {"Pass per attempt": a["P_pass"], "Fail: daily loss": a["P_fail_daily"], "Fail: max loss": a["P_fail_max"],
            "Median days to pass": a["median_days_to_pass"], f"Funded within {budget} buys": p.get("P_funded"),
            "Challenges bought (avg)": p.get("bought"), "Fees (avg)": p.get("fees"), "Payouts (avg)": p.get("paid"),
            "Net (avg)": p.get("net_mean"), "Net (typical)": p.get("net_p50"), "Net (unlucky 10%)": p.get("net_p10"),
            "Net (lucky 10%)": p.get("net_p90"), "Net per month (avg)": p.get("net_per_month"), "Chance of profit": p.get("P_profit"),
            "Prop paths": f"{p.get('n', 0)} ({p.get('method')})"}
