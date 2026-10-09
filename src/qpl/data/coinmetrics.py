"""Coin Metrics community data (coinmetrics/data @f1a36afb, CC BY-NC 4.0 - research only) + point-in-time crypto XS backtest
(same rules as config/v6_gen16_protocol.json)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data/raw/ext/coinmetrics-data/csv"
STABLE_WRAPPED = {"usdt", "usdc", "dai", "busd", "tusd", "pax", "husd", "usdk", "sai", "frax", "fdusd", "usde", "usdd", "eurc", "gusd", "paxg",
                  "xaut", "buidl", "renbtc", "wbtc", "hbtc", "wnxm", "pyusd", "usdp", "lusd", "usd1", "rlusd", "susde", "steth", "weth"}
COLS = ["time", "PriceUSD", "CapMrktCurUSD", "CapMVRVCur", "AdrActCnt", "volume_reported_spot_usd_1d"]


def load() -> dict[str, pd.DataFrame]:
    data = {}
    for f in sorted(SRC.glob("*.csv")):
        a = f.stem
        if "_" in a or a in STABLE_WRAPPED:
            continue
        d = pd.read_csv(f, usecols=lambda c: c in COLS)
        if "PriceUSD" not in d or d.PriceUSD.notna().sum() < 90:
            continue
        d["time"] = pd.to_datetime(d.time); data[a] = d.set_index("time")
    panel = {c: pd.DataFrame({a: d[c] for a, d in data.items() if c in d}) for c in COLS[1:]}
    px = panel["PriceUSD"].sort_index().loc["2013-01-01":"2026-05-24"]
    return {c: (v.reindex_like(px) if c != "PriceUSD" else px) for c, v in panel.items()}


class XSBacktester:
    def __init__(self, panel, top_n=30, min_hist=90, min_vol=1e6):
        self.px, self.cap, vol = panel["PriceUSD"], panel["CapMrktCurUSD"], panel["volume_reported_spot_usd_1d"]
        hist = self.px.notna().cumsum() >= min_hist
        vmed = vol.rolling(30, min_periods=10).median()
        self.reb = self.px.index[self.px.index.dayofweek == 2]
        self.uni = {}
        for t in self.reb:
            ok = hist.loc[t] & self.cap.loc[t].notna() & self.px.loc[t].notna()
            v = vmed.loc[t]; ok &= (v.isna() | (v >= min_vol))
            self.uni[t] = list(self.cap.loc[t][ok].sort_values(ascending=False).index[:top_n])

    def run(self, score: pd.DataFrame, cost_bps=30.0, every=1, min_n=9) -> pd.DataFrame:
        px = self.px; rows = []; w_old = pd.Series(dtype=float); w = pd.Series(dtype=float)
        for j, t in enumerate(self.reb):
            i = px.index.get_loc(t)
            if i + 8 >= len(px):
                break
            if j % every == 0:
                u = [a for a in self.uni[t] if a in score.columns and np.isfinite(score.loc[t, a])]
                if len(u) < min_n:
                    w = pd.Series(dtype=float)
                else:
                    s = score.loc[t, u].rank(pct=True)
                    lo, hi = s[s <= 1 / 3].index, s[s > 2 / 3].index
                    w = pd.concat([pd.Series(1 / len(hi), index=hi), pd.Series(-1 / len(lo), index=lo)])
            p1 = px.iloc[i + 1]
            pend = px.iloc[i + 1:i + 9].ffill().iloc[-1]
            r = (pend.reindex(w.index) / p1.reindex(w.index) - 1).fillna(0) if len(w) else pd.Series(dtype=float)
            idx = w.index.union(w_old.index)
            turn = (w.reindex(idx).fillna(0) - w_old.reindex(idx).fillna(0)).abs().sum()
            gross = float((w * r).sum()) if len(w) else 0.0
            rows.append({"t": px.index[i + 1], "gross": gross, "cost": turn * cost_bps / 1e4, "net": gross - turn * cost_bps / 1e4, "n": len(w), "turn": turn})
            # drift weights with returns so that holding without rebalance has realistic (small) turnover next time
            w_old = (w * (1 + r)).div((w * (1 + r)).abs().sum() / w.abs().sum()) if len(w) else w
            w = w_old.copy() if len(w) else w
        return pd.DataFrame(rows).set_index("t")


def sharpe_w(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(52)) if len(x) > 10 and x.std() > 0 else 0.0
