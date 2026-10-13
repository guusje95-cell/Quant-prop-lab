"""Gen39 (config/crypto_gen39_protocol.json): market-neutral XS reversal/momentum/trend on OKX perps, BTC/ETH funding
contrarian (Deribit), hourly shock reversal. Daily decisions at 00:00 UTC, execution = mean(open, close) of the 00:00 bar.
Intraday worst per day from the hourly path (hour lows/highs, all coins' extremes within an hour simultaneous)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import deribit as DB, okx as OK  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import cft_e2 as E, crypto_zoo as Z  # noqa: E402

PROTO = "config/crypto_gen39_protocol.json"
COST = 7.5; SQ = np.sqrt(365)
PER = {"DEV": ("2020-01-01", "2022-06-30"), "VAL": ("2022-07-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-12")}


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


# ---------------------------------------------------------------- hourly panel
files = sorted(OK.RAW.glob("*-USDT-SWAP_1H.parquet"))
H = {f.name.split("-")[0]: pd.read_parquet(f) for f in files}
idx = pd.date_range(min(d.index.min() for d in H.values()), "2026-10-12 23:00", freq="h")
P = {k: pd.DataFrame({c: H[c][k] for c in H}).reindex(idx) for k in ("open", "high", "low", "close", "volQuote")}
coins = list(H)
day = idx.floor("D")
first_bar = P["open"].index.hour == 0
EXEC = ((P["open"] + P["close"]) / 2)[first_bar]                     # exec price of day d
EXEC.index = EXEC.index.floor("D")
DCLOSE = P["close"][P["close"].index.hour == 23]; DCLOSE.index = DCLOSE.index.floor("D")
DVOL = P["volQuote"].groupby(day).sum(min_count=1)
days = EXEC.index
hist = DCLOSE.notna().cumsum() >= 60
liq = DVOL.rolling(30, min_periods=20).median() >= 20e6
UNIV = (hist & liq).shift(1).fillna(False)                           # known at decision time (00:00 of day d)
for k in ("BTC", "ETH"):
    UNIV[k] = DCLOSE[k].notna().shift(1).fillna(False)
R = (EXEC.shift(-1) / EXEC - 1)                                      # exec d -> exec d+1, earned by weights of day d


def intraday_path(W):
    """Worst/best intraday equity change (vs 00:00 equity) per day for daily weights W (index days)."""
    Wh = W.reindex(day).set_axis(idx).fillna(0)
    ex = EXEC.reindex(day).set_axis(idx)
    lo = (P["low"] / ex - 1).fillna(0); hi = (P["high"] / ex - 1).fillna(0); cl = (P["close"] / ex - 1).fillna(0)
    worst_h = (Wh.clip(lower=0) * lo + Wh.clip(upper=0) * hi).sum(axis=1)
    best_h = (Wh.clip(lower=0) * hi + Wh.clip(upper=0) * lo).sum(axis=1)
    return worst_h.groupby(day).min(), best_h.groupby(day).max()


def run(W, cmult=1.0, path=True):
    W = W.reindex(days).fillna(0)
    cost = W.diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4
    gross = (W * R.fillna(0)).sum(axis=1)
    d = pd.DataFrame({"gross": gross, "net": gross - cost, "cost": cost, "gexp": W.abs().sum(axis=1)})
    if path:
        w_, b_ = intraday_path(W)
        d["worst"] = w_.reindex(days).fillna(0) - cost; d["best"] = b_.reindex(days).fillna(0) - cost
    return d.loc["2020-01-01":"2026-10-11"]


def xs_book(score, univ, q=0.2):
    s = score.where(univ)
    rk = s.rank(axis=1, pct=True)
    n_long = (rk <= q).sum(axis=1).replace(0, np.nan); n_short = (rk > 1 - q).sum(axis=1).replace(0, np.nan)
    w = (rk <= q).astype(float).div(n_long, axis=0) * 0.5 - (rk > 1 - q).astype(float).div(n_short, axis=0) * 0.5
    ok = univ.sum(axis=1) >= 10
    return w.where(ok, 0.0).fillna(0)


lr = np.log(DCLOSE)
S = {}
# H1: previous-day return (close d-1 vs close d-2) -> reversal: long losers => score = return (rank low = long)
S["H1_XS_REVERSAL_1D"] = lambda U: xs_book(lr.diff(1).shift(1), U)
S["H2_XS_REVERSAL_3D"] = lambda U: xs_book(lr.diff(3).shift(1), U)
mom = (lr.shift(1) - lr.shift(28)).shift(1)
S["H3_XS_MOMENTUM_28D"] = lambda U: -xs_book(mom, U).where(pd.Series(days.dayofweek == 0, index=days), np.nan).ffill().fillna(0)
e2 = pd.DataFrame({c: (lambda s: 0.5 * (sum(Z.short_breakout(s, n, k) for n, k in E.BO) / len(E.BO)) + 0.5 * (sum(Z.tsmom(s, n) for n in E.TM) / len(E.TM)))(DCLOSE[c].dropna()) for c in coins}).reindex(days)
S["H4_XS_TREND_E2"] = lambda U: -xs_book(e2.shift(1), U)


def h5(U):
    w = pd.DataFrame(0.0, index=days, columns=coins)
    for c, inst in (("BTC", "BTC-PERPETUAL"), ("ETH", "ETH-PERPETUAL")):
        f = DB.load(inst)["interest_8h"].resample("D").mean()
        m7 = f.rolling(7).mean(); z = (m7 - m7.rolling(365, min_periods=180).mean()) / m7.rolling(365, min_periods=180).std()
        sig = pd.Series(np.where(z > 1.5, -1.0, np.where(z < -1.5, 1.0, 0.0)), index=z.index).shift(1).reindex(days).fillna(0)
        vol = lr[c].diff().rolling(30, min_periods=20).std().shift(1) * SQ
        w[c] = sig * (0.4 / vol).clip(upper=1.0) / 2
    return w.fillna(0)


S["H5_BTCETH_FUNDING_CONTRARIAN"] = h5


def h6_daily(cmult=1.0):
    """Hourly shock reversal on BTC/ETH aggregated to daily net returns (own hourly engine)."""
    out = []
    for c in ("BTC", "ETH"):
        cl = P["close"][c]; op = P["open"][c]
        r = np.log(cl).diff(); sg = r.rolling(720, min_periods=500).std()
        trig = pd.Series(np.where(r < -3 * sg, 1.0, np.where(r > 3 * sg, -1.0, 0.0)), index=idx)
        pos = trig.replace(0, np.nan).ffill(limit=11).fillna(0).shift(1).fillna(0)   # enter next hour, hold 12h
        hr = (op.shift(-1) / op - 1).fillna(0)                                          # open-to-open
        size = (0.4 / (sg * np.sqrt(24 * 365))).clip(upper=1.0).shift(1).fillna(0) / 2
        w = pos * size
        cost = w.diff().abs().fillna(0) * COST * cmult / 1e4
        out.append((w * hr - cost).groupby(day).sum())
    d = pd.concat(out, axis=1).sum(axis=1)
    return pd.DataFrame({"net": d, "gross": d, "cost": 0.0, "worst": d.clip(upper=0) * 1.5, "best": d.clip(lower=0) * 1.5}).loc["2020-01-01":"2026-10-11"]


# ---------------------------------------------------------------- evaluation
vol_ok = DVOL.mean().sort_values(ascending=False)
TOP20 = list(vol_ok.index[:20])
U_rest = UNIV.copy(); U_rest[TOP20] = False
out = {"n_coins": len(coins), "coins": coins, "univ_size_by_year": UNIV.sum(axis=1).groupby(days.year).mean().round(1).to_dict(), "hyp": {}}
series = {}
rng = np.random.default_rng(39); pv = {}
for name, fn in list(S.items()) + [("H6_HOURLY_SHOCK_REVERSAL", None)]:
    if fn is None:
        d = h6_daily(); d2 = h6_daily(2.0)
        rest = None
    else:
        W = fn(UNIV); d = run(W); d2 = run(W, 2.0, path=False)
        rest = run(fn(U_rest), path=False) if name.startswith("H") and not name.startswith("H5") else None
    k = 0.10 / (d["net"].loc[slice(*PER["DEV"])].std() * SQ)
    x = d["net"] * k
    st = {p: round(sh(x.loc[a:z]), 3) for p, (a, z) in PER.items()}
    st["ALL"] = round(sh(x), 3); st["TEST_2x"] = round(sh(d2["net"].loc[slice(*PER["TEST"])]), 3)
    st["gross_ALL"] = round(sh(d["gross"]), 3)
    m = (1 + x).resample("ME").prod() - 1
    st["pos_months"] = round(float((m > 0).mean()), 3); st["worst_month"] = round(float(m.min()), 4)
    st["worst_day_at10vol"] = round(float((d["worst"] * k).min()), 4) if "worst" in d else None
    st["turnover_cost_pa_at10vol"] = round(float((d["cost"] * k).mean() * 365), 4)
    st["replication_rest_sharpe"] = round(sh(rest["net"]), 3) if rest is not None else None
    xv = x.dropna().to_numpy(); bi = T.stationary_bootstrap_indices(len(xv), 5000, 10.0, rng)
    pv[name] = float(np.mean((xv - xv.mean())[bi].mean(axis=1) >= xv.mean()))
    st["p_raw"] = round(pv[name], 4)
    out["hyp"][name] = st; series[name] = d * k
    print(name, st, flush=True)
order = sorted(pv, key=pv.get); run_ = 0.0
for i, kk in enumerate(order):
    run_ = max(run_, min(1.0, (len(order) - i) * pv[kk])); out["hyp"][kk]["p_holm"] = round(run_, 4)
for kk, st in out["hyp"].items():
    repl = st["replication_rest_sharpe"]
    st["ACCEPTED"] = bool(st["DEV"] >= 0.8 and st["VAL"] >= 0.5 and st["TEST"] >= 0.5 and st["TEST_2x"] >= 0.3 and st["p_holm"] < 0.05
                          and (repl is None or repl >= 0.3))
    F.append({"kind": "holdout_evaluation", "hypothesis_id": f"GEN39_{kk}", "protocol": PROTO, "result": st})
out["accepted"] = [k for k, v in out["hyp"].items() if v["ACCEPTED"]]
(ROOT / "results/crypto_gen39_xs_hourly.json").write_text(json.dumps(out, indent=1, default=str))
pd.to_pickle(series, ROOT / "results/crypto_gen39_series.pkl")
print("ACCEPTED", out["accepted"])
