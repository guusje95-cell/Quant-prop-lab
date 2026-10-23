"""Gen348b (config/gen348b_protocol.json): robustness of the premium-spike reversion. Writes results/gen348b.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, extra_pack as X
END = L.END; ROOT = L.ROOT
coins = CS._breadth_universe(); Hc = CS._breadth_close(coins).loc[:END + " 23:00"]; R = Hc.pct_change(fill_method=None).fillna(0.0); idx = Hc.index; n = len(idx)
pk = B.coins()
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in coins if c not in pk], axis=1).sort_index()[coins]
fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(idx).fillna(0.0)
Z = {}
for c in coins:
    p = (B.premium(c)["close"] if c in pk else X.premium(c)); p = p[~p.index.duplicated()]; p.index = pd.DatetimeIndex(p.index); p = p.reindex(idx)
    Z[c] = ((p - p.rolling(720, min_periods=500).mean().shift(1)) / p.rolling(720, min_periods=500).std().shift(1)).to_numpy()


def pos(th=3.0, hold=4, side=0):
    P = np.zeros((n, len(coins)))
    for j, c in enumerate(coins):
        z = np.nan_to_num(Z[c])
        for t in np.flatnonzero(np.abs(z) > th):
            s = -np.sign(z[t])
            if side and s != side:
                continue
            P[t + 1:min(t + 1 + hold, n), j] = 0.1 * s
    return pd.DataFrame(P, index=idx, columns=coins)


per = lambda h: [round(x, 3) for x in L.per(h.reindex(L.H6.index).fillna(0.0), "2020-01-01")]
by = pd.read_csv(ROOT / "research_data/bybit/instruments.csv"); by = by[by.coin.isin(coins)]; sym = dict(zip(by.coin, by.symbol))
spr = pd.read_csv(ROOT / "research_data/bybit/spreads.csv").set_index("symbol")["spread_bp_median"]
cost = pd.Series({c: 5.5 + 0.5 * float(spr.get(sym.get(c, ""), np.nan)) for c in coins}); cost = cost.fillna(5.5 + 0.5 * float(spr.median()))
fb = {}
for c in coins:
    f = ROOT / f"research_data/bybit/funding/{sym.get(c, '')}.parquet"
    if c in sym and f.exists():
        x = pd.read_parquet(f)["funding_rate"]; x.index = pd.DatetimeIndex(x.index) - pd.Timedelta(hours=1); fb[c] = x.groupby(level=0).sum()
FB = fund.copy()
for c, x in fb.items():
    st = x.index.min(); FB.loc[st:, c] = x.reindex(idx).loc[st:].fillna(0.0)


def pnl(P, cst=5.0, fin=None, ret=None):
    fin = fund if fin is None else fin; ret = R if ret is None else ret; d = P.diff().abs().fillna(0.0)
    c = (d * cst).sum(axis=1) if np.isscalar(cst) else (d * cst).sum(axis=1)
    return (P * ret).sum(axis=1) - (P * fin).sum(axis=1) - c / 1e4


P0 = pos(); out = {"base (Gen348 A)": per(pnl(P0))}
out["1 Bybit costs + funding"] = per(pnl(P0, cost, FB))
# 2 maker
LO = pd.concat([B.panel("low", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["low"].rename(c) for c in coins if c not in pk], axis=1)
HI = pd.concat([B.panel("high", "1h", pk)] + [pd.read_parquet(ROOT / f"research_data/binance_extra/{c}USDT_1h.parquet")["high"].rename(c) for c in coins if c not in pk], axis=1)
LO = LO[~LO.index.duplicated()]; HI = HI[~HI.index.duplicated()]; LO.index = pd.DatetimeIndex(LO.index); HI.index = pd.DatetimeIndex(HI.index)
LO, HI = LO.reindex(idx)[coins], HI.reindex(idx)[coins]; prev = Hc.shift(1)
dE = P0.diff().fillna(P0)
filled = (((dE > 0) & (LO <= prev * (1 - 2e-4))) | ((dE < 0) & (HI >= prev * (1 + 2e-4)))).astype(float)
Ee = P0 - dE * (1 - filled); cm = (dE.abs() * (filled * 2.0 + (1 - filled) * cost)).sum(axis=1) / 1e4
out["2 maker (Bybit fallback)"] = per((Ee * R).sum(axis=1) - (Ee * FB).sum(axis=1) - cm)
out["2 maker fill rate"] = round(float((dE.abs() * filled).sum().sum() / dE.abs().sum().sum()), 3)
out["3 shorts only / longs only"] = [per(pnl(pos(side=-1))), per(pnl(pos(side=1)))]
grid = {}
for th in (2.5, 3.0, 3.5):
    for hd in (2, 4, 6):
        grid[f"z {th} hold {hd}"] = per(pnl(pos(th, hd)))
out["4 neighbourhood"] = grid
G = np.array(list(grid.values())); out["4 neighbourhood median D/T/H"] = np.round(np.median(G, axis=0), 3).tolist()
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; ro = {}
for c in coins:
    f = ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); ro[c] = x.reindex(idx).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=coins); have = RO.notna()
Pm = P0.where(have, 0.0)
out["5 same cells Binance / OKX"] = [per(pnl(Pm)), per(pnl(Pm, ret=RO.fillna(0.0)))]
h = pnl(P0); d = h.groupby(h.index.floor("D")).sum()
out["6 by year"] = {str(y): round(float(g.mean() / g.std() * np.sqrt(365)), 2) for y, g in d.loc["2020":END].groupby(d.loc["2020":END].index.year)}
ev = (P0.diff().fillna(P0) != 0) & (P0 != 0)
out["7 entries per year / mean gross exposure"] = [round(float(ev.sum().sum() / 6.75), 0), round(float(P0.abs().sum(axis=1).mean()), 3)]
print(json.dumps(out, indent=0), flush=True)
json.dump(out, open(ROOT / "results/gen348b.json", "w"), indent=1)
