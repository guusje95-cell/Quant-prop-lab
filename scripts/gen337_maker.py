"""Gen337 (config/gen337_protocol.json): limit-order execution of v8.6 on Bybit. Writes results/gen337.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen327_bybit_reality.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("tgtB = net.copy()")], str(_p), "exec"))      # net, r, fund_by, cost, ev_pnl, U, sharpe(), ACCT, B
from qpl.lab import extra_pack as X
pk = [c for c in U if c in B.coins()]
LO = pd.concat([B.panel("low", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in U if c not in pk], axis=1)
HI = pd.concat([B.panel("high", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["high"].rename(c) for c in U if c not in pk], axis=1)
for D in (LO, HI):
    D.index = pd.DatetimeIndex(D.index)
idx = net.index; LO = LO[~LO.index.duplicated()].reindex(idx)[U]; HI = HI[~HI.index.duplicated()].reindex(idx)[U]
prev = Hc.reindex(idx).shift(1)                                           # the previous hour's close (the backtest's entry price)
assert float((LO.stack() > HI.stack()).mean()) == 0.0


def executed(target, band_usd=1000.0, risk=2.0):
    usd = ACCT * risk; A = target.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1]); b = band_usd / usd
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b; ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    return pd.DataFrame(E, index=target.index, columns=target.columns)


E = executed(net); dE = E.diff().fillna(E)
base = (E * r).sum(axis=1) - (E * fund_by.reindex(idx)).sum(axis=1) - (dE.abs() * cost).sum(axis=1) / 1e4 + ev_pnl
out = {"baseline taker (Gen327 E) Sharpe D/T/H": sharpe(base)}
print(out, flush=True)
for th in (0.0, 2.0, 5.0):
    buy = (dE > 0) & (LO <= prev * (1 - th / 1e4)); sell = (dE < 0) & (HI >= prev * (1 + th / 1e4))
    filled = (buy | sell).astype(float); traded = dE.abs() > 0
    Ee = E - dE * (1 - filled)                                            # unfilled: still the old position during hour t
    c = (dE.abs() * (filled * 2.0 + (1 - filled) * cost)).sum(axis=1) / 1e4
    p = (Ee * r).sum(axis=1) - (Ee * fund_by.reindex(idx)).sum(axis=1) - c + ev_pnl
    k = f"maker, trade-through {th:.0f} bp"
    out[k] = {"sharpe D/T/H": sharpe(p), "fill rate (by notional)": round(float((dE.abs() * filled).sum().sum() / dE.abs().sum().sum()), 3),
              "fill rate (by order)": round(float(filled[traded].sum().sum() / traded.sum().sum()), 3),
              "cost per year 15%-vol units: taker vs this": [round(float((dE.abs() * cost).sum(axis=1).mean() / 1e4 * 24 * 365), 4), round(float(c.mean() * 24 * 365), 4)],
              "missed-move cost per year": round(float(((E - Ee) * r).sum(axis=1).mean() * 24 * 365), 4)}
    print(k, out[k], flush=True)
s0 = out["baseline taker (Gen327 E) Sharpe D/T/H"]; s2 = out["maker, trade-through 2 bp"]["sharpe D/T/H"]
out["adopt as execution plan (2 bp variant better in every period)"] = bool(all(a > b for a, b in zip(s2[1:], s0[1:])))
json.dump(out, open(ROOT / "results/gen337.json", "w"), indent=1)

# ---- Gen337b: limit valid 15 minutes (pack coins with 5-minute data), then market --------------------------------------
L15, H15, C15 = {}, {}, {}
for c in pk:
    k = B.k5(c); g = k.index.floor("h"); first = k[(k.index - g) < pd.Timedelta(minutes=15)]; gg = first.index.floor("h")
    L15[c] = first["low"].groupby(gg).min(); H15[c] = first["high"].groupby(gg).max(); C15[c] = first["close"].groupby(gg).last()
L15, H15, C15 = (pd.DataFrame(x).reindex(idx) for x in (L15, H15, C15))
buy = (dE > 0) & (LO <= prev * (1 - 2 / 1e4)); sell = (dE < 0) & (HI >= prev * (1 + 2 / 1e4))
buy[pk] = (dE[pk] > 0) & (L15 <= prev[pk] * (1 - 2 / 1e4)); sell[pk] = (dE[pk] < 0) & (H15 >= prev[pk] * (1 + 2 / 1e4))
filled = (buy | sell).astype(float)
Ee = E - dE * (1 - filled); Ee[pk] = E[pk]                                 # pack coins: unfilled orders are in from minute 15
late = (dE[pk] * (1 - filled[pk]) * (Hc.reindex(idx)[pk] / prev[pk] - Hc.reindex(idx)[pk] / C15)).fillna(0.0).sum(axis=1)
c = (dE.abs() * (filled * 2.0 + (1 - filled) * cost)).sum(axis=1) / 1e4
p = (Ee * r).sum(axis=1) - (Ee * fund_by.reindex(idx)).sum(axis=1) - c - late + ev_pnl
out["Gen337b limit 15 min then market (pack coins), 2 bp"] = {"sharpe D/T/H": sharpe(p), "fill rate (by notional)": round(float((dE.abs() * filled).sum().sum() / dE.abs().sum().sum()), 3)}
print(out["Gen337b limit 15 min then market (pack coins), 2 bp"], flush=True)
json.dump(out, open(ROOT / "results/gen337.json", "w"), indent=1)
