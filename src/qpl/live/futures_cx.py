"""Futures book + CX (F-CX, 2026-11-03; user-approved SHADOW next to the futures paper run, which itself is unchanged).

CX = the C* BTC / ETH legs (crypto_sleeves.cstar_weights, row d decided at the close of d, held during d + 1) as a 16th sleeve of the
futures book. The research series (results/v99/cx_sleeve_prefix.parquet, up to 2026-09-30) is the real CME BTC / ETH front-month P&L
(Gen137 code, weekend-hold, CME micro costs + roll). The live CME BTC / ETH bars are NOT in the Databento top-up (that would cost
money), so the forward CX is a PROXY: the same positions on Binance BTC / ETH perps (v9.8 paper's live data, read-only), CME micro costs
per side, Binance funding as the stand-in for the CME basis (results/v99/cx_proxy_check.json compares both on 2020-26).

Day convention (as F-CXb): UTC calendar day, Saturday / Sunday P&L booked on the next Monday. Book: fbook rule (static 1/sd weights on
2010-22 over sleeves with a positive 2010-22 Sharpe, 10% vol target on the 60-day vol, cap 3x, lagged) over the 15 futures sleeves
(research series, then the frozen futures paper ledger) plus CX. Each futures paper day is written ONCE to
paper_trading/futcx/ledger_hourly.csv once its CX day is complete.

    python -m qpl.live.futures_cx           # one step (hub job 'futcx_paper', hourly)"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "paper_trading/futcx"
FUT = ROOT / "paper_trading/futures/ledger_hourly.csv"
V98 = ROOT / "paper_trading/v98"
PREFIX = ROOT / "results/v99/cx_sleeve_prefix.parquet"
RESEARCH_END = pd.Timestamp("2026-09-30")


def daily(h: pd.Series) -> pd.Series:
    """hourly P&L -> daily (UTC date; Saturday / Sunday booked on the next Monday)"""
    d = h.index.floor("D"); wd = d.weekday
    return h.groupby(d + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")).sum()


def cme_cost(coin: str, price):
    sys.path.insert(0, str(ROOT / "scripts"))
    import futures_db as F
    return F.cost_frac(coin, price)


def proxy_hourly(pos: pd.DataFrame, px: pd.DataFrame, fund: pd.DataFrame, cost=cme_cost) -> pd.Series:
    """positions (held during hour h) x Binance hourly returns of hour h - funding - turnover x CME micro cost per side"""
    out = []
    for c in ("BTC", "ETH"):
        p = pos[c].reindex(px.index).fillna(0.0); r = px[c].pct_change(fill_method=None).fillna(0.0)
        f = fund[c].reindex(px.index).fillna(0.0) if c in fund else 0.0
        out.append(p * r - p * f - p.diff().abs().fillna(p.abs()) * cost(c, px[c].ffill()))
    return sum(out)


def book(P: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """fbook rule; returns the book and the per-sleeve weights w_i x level_t"""
    P = P[P.index.weekday < 5].fillna(0.0); T = P.loc[:"2022-12-31"]
    w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna(), pd.DataFrame(np.outer(lvl.fillna(0.0), w), index=P.index, columns=P.columns)


def futures_sleeves() -> pd.DataFrame:
    H = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet").loc[:RESEARCH_END]
    if FUT.exists():
        L = pd.read_csv(FUT); L.index = pd.to_datetime(L["hour"]).dt.normalize()
        H = pd.concat([H, L[[c for c in H.columns if c in L]].astype(float).loc[L.index > RESEARCH_END]])
    return H


def _compute(cutoff: pd.Timestamp) -> dict:
    """child process (QPL_LIVE_PACK set): proxy CX per day for complete UTC days after the research end up to cutoff"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import crypto_sleeves as CS
    from qpl.lab import binance_pack as B
    px = B.panel("close", "1h", ["BTC", "ETH"]).loc[:cutoff - pd.Timedelta(hours=1)]
    w = CS.cstar_weights()[["BTC", "ETH"]]
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)      # row d held on d + 1
    pos = w.reindex(px.index.floor("D")).set_axis(px.index).fillna(0.0)
    h = proxy_hourly(pos, px, CS._funding_hourly(["BTC", "ETH"], px.index))
    h = h.loc[RESEARCH_END + pd.Timedelta(days=1):]
    last_full = cutoff.floor("D") - pd.Timedelta(days=1)                                     # complete UTC days only
    h = h.loc[:last_full + pd.Timedelta(hours=23)]
    d = daily(h)
    return {"cx": {str(k.date()): float(v) for k, v in d.items()}, "last_full_day": str(last_full.date())}


def step(log=print, cx_live: dict | None = None) -> dict:
    if not FUT.exists():
        return {"status": "waiting for the futures paper ledger (paper_trading/futures/ledger_hourly.csv)"}
    if cx_live is None:
        led = V98 / "ledger_hourly.csv"
        if not led.exists() or not (V98 / "data").exists():
            return {"status": "waiting for the v9.8 paper's live data (paper_trading/v98/data)"}
        cutoff = min(pd.Timestamp(pd.read_csv(led, usecols=["hour"])["hour"].max()) + pd.Timedelta(hours=1),
                     pd.Timestamp.now(tz="UTC").tz_localize(None).floor("h"))
        env = dict(os.environ, QPL_LIVE_PACK=str(V98 / "data"), QPL_CUTOFF=str(cutoff), QPL_END=str(cutoff - pd.Timedelta(hours=1)), PYTHONPATH=str(ROOT / "src"))
        r = subprocess.run([sys.executable, "-m", "qpl.live.futures_cx", "_compute", str(cutoff)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            return {"status": "failed", "stderr": r.stderr[-1500:]}
        cx_live = json.loads(r.stdout.strip().splitlines()[-1])
    last_full = pd.Timestamp(cx_live["last_full_day"])
    cx = pd.read_parquet(PREFIX)["CX"].loc[:RESEARCH_END]
    live = pd.Series({pd.Timestamp(k): v for k, v in cx_live["cx"].items()}, dtype=float)
    cx = pd.concat([cx, live[live.index > RESEARCH_END]])
    P = futures_sleeves(); P["CX"] = cx.reindex(P.index).fillna(0.0)
    b, W = book(P)
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / "ledger_hourly.csv"
    L = pd.read_csv(f) if f.exists() else pd.DataFrame(); have = set(L["hour"].astype(str)) if len(L) else set()
    now = pd.Timestamp.now(tz="UTC").tz_localize(None); rows = []
    for d in b.index[(b.index > RESEARCH_END) & (b.index <= last_full)]:
        hour = str(d + pd.Timedelta(hours=21))
        if hour in have:
            continue                                                                   # frozen: a day is written once
        lag = (now - (d + pd.Timedelta(days=1))).total_seconds() / 3600
        r = {"hour": hour, "port": float(b.loc[d])}
        for s in P.columns:
            r[s] = float(P.loc[d, s]); r["w " + s] = float(W.loc[d, s])
        r.update({"computed_at": str(now.floor("s")), "lag_h": round(lag, 1), "late": bool(lag > 30)})
        rows.append(r)
    if rows:
        L = pd.concat([L, pd.DataFrame(rows)], ignore_index=True); tmp = f.with_suffix(".tmp"); L.to_csv(tmp, index=False); tmp.replace(f)
    return {"appended": len(rows), "ledger_days": len(L), "last_full_cx_day": str(last_full.date())}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_compute":
        print(json.dumps(_compute(pd.Timestamp(sys.argv[2]))))
    else:
        print(json.dumps(step(), indent=1))
