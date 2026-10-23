"""Gen339 (config/gen339_protocol.json): band size, cost-aware band, rebalance-to-edge, and per-sleeve cost decomposition.
Writes results/gen339.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen327_bybit_reality.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("tgtB = net.copy()")], str(_p), "exec"))      # net, r, fund_by, cost, ev_pnl, U, sharpe(), ACCT, B, daily, Wh, mh
pk = [c for c in U if c in B.coins()]
LO = pd.concat([B.panel("low", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in U if c not in pk], axis=1)
HI = pd.concat([B.panel("high", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["high"].rename(c) for c in U if c not in pk], axis=1)
idx = net.index
LO = LO[~LO.index.duplicated()].set_axis(pd.DatetimeIndex(LO[~LO.index.duplicated()].index)).reindex(idx)[U]
HI = HI[~HI.index.duplicated()].set_axis(pd.DatetimeIndex(HI[~HI.index.duplicated()].index)).reindex(idx)[U]
prev = Hc.reindex(idx).shift(1); R = r.reindex(idx); FB = fund_by.reindex(idx)


def execute(T, band_usd, edge=False, band_vec=None, risk=2.0):
    usd = ACCT * risk; A = T.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1])
    b = (band_vec if band_vec is not None else np.full(A.shape[1], band_usd)) / usd
    for i in range(len(A)):
        d = A[i] - cur; out_ = np.abs(d) >= b; zero = (A[i] == 0) & (cur != 0)
        if edge:
            new = np.where(out_, A[i] - np.sign(d) * b, cur)
        else:
            new = np.where(out_, A[i], cur)
        cur = np.where(zero, 0.0, new); E[i] = cur
    return pd.DataFrame(E, index=T.index, columns=T.columns)


def pnl_taker(E):
    dE = E.diff().fillna(E)
    return (E * R).sum(axis=1) - (E * FB).sum(axis=1) - (dE.abs() * cost).sum(axis=1) / 1e4 + ev_pnl


def pnl_maker(E, th=2.0):
    dE = E.diff().fillna(E)
    filled = (((dE > 0) & (LO <= prev * (1 - th / 1e4))) | ((dE < 0) & (HI >= prev * (1 + th / 1e4)))).astype(float)
    Ee = E - dE * (1 - filled); c = (dE.abs() * (filled * 2.0 + (1 - filled) * cost)).sum(axis=1) / 1e4
    return (Ee * R).sum(axis=1) - (Ee * FB).sum(axis=1) - c + ev_pnl


cv = cost.reindex(U).to_numpy(); cav = 1000.0 * cv / np.median(cv)
V = {"band $1,000 (current)": dict(band_usd=1000), "band $500": dict(band_usd=500), "band $2,000": dict(band_usd=2000), "band $4,000": dict(band_usd=4000),
     "cost-aware band": dict(band_usd=1000, band_vec=cav), "to band edge $1,000": dict(band_usd=1000, edge=True), "to band edge $2,000": dict(band_usd=2000, edge=True)}
out = {}
for k, kw in V.items():
    E = execute(net, **kw); dE = E.diff().fillna(E)
    out[k] = {"taker D/T/H": sharpe(pnl_taker(E)), "maker D/T/H": sharpe(pnl_maker(E)),
              "orders per day": round(float(((dE.abs() * ACCT * 2.0) > 1.0).groupby(dE.index.floor("D")).sum().sum(axis=1).mean()), 1),
              "tracking: corr of positions with target": round(float(np.corrcoef(E.to_numpy().ravel(), net.to_numpy().ravel())[0, 1]), 4)}
    print(k, out[k], flush=True)
b0 = out["band $1,000 (current)"]
for k in V:
    if k != "band $1,000 (current)":
        out[k]["adopt (every period up under both models)"] = bool(all(a > c for a, c in zip(out[k]["taker D/T/H"][1:], b0["taker D/T/H"][1:])) and
                                                                   all(a > c for a, c in zip(out[k]["maker D/T/H"][1:], b0["maker D/T/H"][1:])))
# per-sleeve gross turnover cost (before netting) at the median Bybit cost
med = float(np.median(cv)); dec = {}
tot_gross = 0.0
for s, w in daily.items():
    wd = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    held = wd.reindex(idx.floor("D")).set_axis(idx).reindex(columns=U).fillna(0.0).mul(Wh[s] * mh, axis=0) * 0.902
    c_s = float((held.diff().abs().sum(axis=1) * med / 1e4).mean() * 24 * 365); g_s = float((held * R).sum(axis=1).mean() * 24 * 365)
    dec[s] = {"turnover cost per year": round(c_s, 4), "gross P&L per year": round(g_s, 4), "cost / gross": round(c_s / g_s, 3) if g_s else None}; tot_gross += c_s
E0 = execute(net, 1000)
netc = float((E0.diff().abs().sum(axis=1) * med / 1e4).mean() * 24 * 365)
out["per-sleeve turnover cost (15%-vol units per year, median cost)"] = dec
out["netting: sum of sleeve costs vs netted + band cost"] = [round(tot_gross, 4), round(netc, 4)]
print(json.dumps(dec), out["netting: sum of sleeve costs vs netted + band cost"], flush=True)
json.dump(out, open(ROOT / "results/gen339.json", "w"), indent=1)
