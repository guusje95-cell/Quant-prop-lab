"""v9.9 R41 (diagnostic, no selection): parameter plateau of the three new event sleeves (Coinbase/Upbit R30 A, futures delisting R32 B,
Binance add R34): hold 3 / 7 / 14 / 30 days x stop 20 / 30 / 50%, the same setting for all three sleeves, v9.8 + the three sleeves vs
v9.8. Registered setting: Coinbase/Upbit and add 7 d / 30%, futures delisting 14 d / 30%. Writes results/v99/r41_plateau.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34


def short_sleeve(ev, idx, hold_d, stop, entry_lag_h=1):
    """R16 A style short, parameterised; ev = [(coin, T)] (T = first venue hour; entry at the close of the hour T + entry_lag_h)"""
    pnl = pd.Series(0.0, index=idx); last = {}
    for coin, T in sorted(ev, key=lambda e: e[1]):
        if coin in last and T - last[coin] < pd.Timedelta(days=7):
            continue
        cl, fu = EL._closes(coin)
        if cl is None:
            continue
        cl = cl.copy(); cl.index = cl.index + pd.Timedelta(hours=1); T = T.floor("h")
        if not ((cl.index > T - pd.Timedelta(hours=3)) & (cl.index <= T + pd.Timedelta(hours=1))).any():
            continue
        p = cl.loc[T + pd.Timedelta(hours=entry_lag_h):T + pd.Timedelta(hours=entry_lag_h + 24 * hold_d)]
        if len(p) < 2:
            continue
        hit = p[p >= p.iloc[0] * (1 + stop)].index
        if len(hit):
            p = p.loc[:hit[0]]
        r = p.pct_change().dropna(); x = pd.Series(-0.05, index=r.index)
        f = fu.reindex(r.index).fillna(0.0) if fu is not None and len(fu) else 0.0
        h = x * r - x * f; h.iloc[0] -= 0.05 * 1e-3; h.iloc[-1] -= 0.05 * 1e-3
        h.index = h.index.floor("h"); pnl = pnl.add(h.groupby(level=0).sum().reindex(idx).fillna(0.0), fill_value=0.0); last[coin] = T
    return pnl


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]])(unit(CS.portfolio_v5(H)[0]))
    VE = list(R16.events().items()) + list(R22.upbit_events().items())
    FE = [(c, t.ceil("h") - pd.Timedelta(hours=1)) for c, t in R32.events()["futures delisting"]]
    AE = list(R34.events().items())
    out = {"reference v9.8": book(V8), "grid (all three sleeves the same hold / stop)": {}}
    for hold in (3, 7, 14, 30):
        for stop in (0.2, 0.3, 0.5):
            H = V8.assign(**{"venue listing short": short_sleeve(VE, idx, hold, stop), "futures-delisting short": short_sleeve(FE, idx, hold, stop),
                             "binance add short": short_sleeve(AE, idx, hold, stop)})
            r = book(H); out["grid (all three sleeves the same hold / stop)"][f"{hold} d / {int(stop * 100)}%"] = r; print(hold, stop, r, flush=True)
    G = [v[0] for v in out["grid (all three sleeves the same hold / stop)"].values()]
    out["grid summary"] = {"min": min(G), "median": float(np.median(G)), "max": max(G), "cells >= v9.8 + 0.05": int(sum(g >= out["reference v9.8"][0] + 0.05 for g in G)), "cells": len(G)}
    print(out["grid summary"]); (ROOT / "results/v99/r41_plateau.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
