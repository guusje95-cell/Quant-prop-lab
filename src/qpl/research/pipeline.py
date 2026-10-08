"""Standard research pipeline: backtest -> USD accounting -> split metrics -> registry."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from ..backtesting import accounting as A
from ..backtesting import engine as E
from ..data import loaders
from ..instruments import Instrument, get
from ..statistics import metrics as M
from ..strategies import index_intraday as SI

# Strict chronological separation (development data: Dukascopy CFD proxies)
SPLITS = {
    "train": ("2013-01-01", "2018-12-31"),
    "validation": ("2019-01-01", "2020-12-31"),
    "oos": ("2021-01-01", "2023-09-11"),
}
DEV_SPLITS = ("train", "validation")   # the only periods allowed during design/selection
FINAL_TEST = ("2025-03-21", "2026-04-15")  # real CME futures (TopstepX) - untouched until frozen

TF_MIN = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "5min": 5, "15min": 15, "1h": 60}


@lru_cache(maxsize=32)
def context(source: str, symbol: str, tf: str) -> pd.DataFrame:
    df = loaders.load(source, symbol, tf)
    return SI.build_context(df, TF_MIN[tf])


def trading_days(ctx: pd.DataFrame) -> pd.DatetimeIndex:
    v = ctx[ctx["valid_day"] & ctx["rth"]]
    return pd.DatetimeIndex(sorted(v["date"].unique()))


def backtest(strategy: str, ctx: pd.DataFrame, prm: dict, inst: Instrument, slip_ticks: float = 0.0) -> pd.DataFrame:
    """Frictionless engine run; slippage/commission are applied in usd()."""
    fn = SI.STRATEGIES[strategy]
    orders = fn(ctx, prm)
    sess = SI.cme_session(ctx) if SI.SESSION_KIND.get(strategy) == "cme" else SI.rth_session(ctx)
    tr = E.run(ctx, orders, sess, tick=inst.tick_size, slip_ticks=slip_ticks)
    tr["day"] = pd.DatetimeIndex(ctx["cme_date"].to_numpy()[tr["exit_i"].to_numpy()])
    return tr


# Reference prices for deployment-normalized accounting: the futures settlement level at the
# start of the untouched final-test window (2025-03-21), fixed ex-ante. Historical point P&L is
# rescaled to this price level so that fixed tick costs carry today's relative weight.
REF_PRICE = {"ES": 5700.0, "MES": 5700.0, "NQ": 19900.0, "MNQ": 19900.0, "YM": 42300.0, "MYM": 42300.0,
             "GC": 3000.0, "MGC": 3000.0}


def normalize(tr: pd.DataFrame, ref: float) -> pd.DataFrame:
    """Rescale point quantities to a reference price level (percentage-return preserving)."""
    t = tr.copy()
    f = ref / t["entry_px"].to_numpy()
    for c in ("pnl_pts", "mae_pts", "mfe_pts", "risk_pts"):
        t[c] = t[c].to_numpy() * f
    return t


def usd(tr: pd.DataFrame, inst: Instrument, contracts: int | None = 1, risk_usd: float | None = None,
        cost_mult: float = 1.0, slip_mult: float = 1.0, max_contracts: int = 50,
        norm: bool = True) -> pd.DataFrame:
    """norm=True: deployment-normalized (primary). norm=False: historical price level (stress)."""
    if norm and inst.symbol in REF_PRICE:
        tr = normalize(tr, REF_PRICE[inst.symbol])
    q = A.size_trades(tr, inst, risk_usd=risk_usd, contracts=contracts, max_contracts=max_contracts)
    return A.to_usd(tr, inst, q, cost_mult=cost_mult, slip_mult=slip_mult)


def split_metrics(tr_usd: pd.DataFrame, days: pd.DatetimeIndex, splits=SPLITS, capital: float = 50_000) -> dict:
    out = {}
    dly = A.daily_pnl(tr_usd, days)
    for name, (a, b) in splits.items():
        m = (days >= a) & (days <= b)
        d = dly.loc[m]
        t = tr_usd[(tr_usd["day"] >= a) & (tr_usd["day"] <= b)]
        if len(d) == 0:
            continue
        out[name] = M.summarize(d["pnl"], t, capital)
    return out


def daily(tr_usd: pd.DataFrame, days: pd.DatetimeIndex, a: str | None = None, b: str | None = None) -> pd.DataFrame:
    d = A.daily_pnl(tr_usd, days)
    if a:
        d = d.loc[a:]
    if b:
        d = d.loc[:b]
    return d


def proxy_for(symbol: str) -> tuple[str, str]:
    inst = get(symbol)
    return "dukascopy", inst.proxy
