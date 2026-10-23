"""Gen331 (config/gen331_protocol.json): v8.6 on OKX prices, a one-hour execution delay, OKX vs Binance funding, and the CFD
route with measured MT5 swaps. Writes results/gen331.json."""
import glob
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import requests
_p = Path(__file__).resolve().parent / "gen327_bybit_reality.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("tgtB = net.copy()")], str(_p), "exec"))      # net, r, fund, fund_by, cost, ev_pnl, U, sharpe(), ACCT
OKX = ROOT / "data/raw/okx"; NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}
out = {}


def pnl(E, ret, fin, cost_bp):
    dE = E.diff().fillna(E)
    return (E * ret.reindex(E.index)).sum(axis=1) - (E * fin.reindex(E.index)).sum(axis=1) - (dE.abs() * cost_bp).sum(axis=1) / 1e4


# ---- A: OKX prices ------------------------------------------------------------------------------------------------------
ro = {}
for c in U:
    f = OKX / f"{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index)
        ro[c] = x.reindex(net.index).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=U)
okx_end = RO.dropna(how="all").index.max()
have = RO.notna()                                                            # hour-coin cells with an OKX return in both runs
E = net.loc[:okx_end].where(have.loc[:okx_end], 0.0)
pb = pnl(E, r.where(have, 0.0), fund, 5.0); po = pnl(E, RO.fillna(0.0), fund, 5.0)
END2 = str(okx_end.date())


def sh(p, a, z):
    d = p.groupby(p.index.floor("D")).sum().loc[a:z]; return round(float(d.mean() / d.std() * np.sqrt(365)), 3)


per = [("2022-01-01", END2), ("2022", "2022"), ("2023", "2024"), ("2025", END2)]
out["A coins without OKX data"] = sorted(set(U) - set(ro))
out["A share of position-hours with OKX data"] = round(float((net.abs() * have).sum().sum() / net.abs().sum().sum()), 4)
out["A Binance prices (same cells) Sharpe D/T/H"] = [sh(pb, a, z) for a, z in per]
out["A OKX prices Sharpe D/T/H"] = [sh(po, a, z) for a, z in per]
out["A hourly P&L correlation"] = round(float(pb.corr(po)), 4)
out["A daily P&L correlation"] = round(float(pb.groupby(pb.index.floor("D")).sum().corr(po.groupby(po.index.floor("D")).sum())), 4)
out["A annual return (15%-vol units) Binance vs OKX"] = [round(float(pb.mean() * 24 * 365), 4), round(float(po.mean() * 24 * 365), 4)]
out["A PASS"] = bool(out["A OKX prices Sharpe D/T/H"][0] >= 0.9 * out["A Binance prices (same cells) Sharpe D/T/H"][0] and out["A hourly P&L correlation"] >= 0.9)
print({k: v for k, v in out.items()}, flush=True)

# ---- A2: OKX funding (recent) ------------------------------------------------------------------------------------------
fo = {}
for c in ro:
    rows, after = [], ""
    for _ in range(4):
        try:
            d = requests.get(f"https://www.okx.com/api/v5/public/funding-rate-history?instId={NM.get(c, c)}-USDT-SWAP&limit=100{after}", timeout=20).json().get("data", [])
        except Exception:
            d = []
        if not d:
            break
        rows += d; after = f"&after={d[-1]['fundingTime']}"; time.sleep(0.12)
    if rows:
        s = pd.Series({pd.Timestamp(int(x["fundingTime"]), unit="ms"): float(x["realizedRate"] or x["fundingRate"]) for x in rows}).sort_index()
        s.index = s.index - pd.Timedelta(hours=1); fo[c] = s
if fo:
    FO = pd.DataFrame(fo).groupby(level=0).sum()
    a0 = FO.index.min(); z0 = min(FO.index.max(), fund.index.max())
    Fb = fund.loc[a0:z0, FO.columns]; Fo = FO.reindex(Fb.index).fillna(0.0)
    En = net.loc[a0:z0, FO.columns]
    cb = float((En * Fb).sum(axis=1).sum()); co = float((En * Fo).sum(axis=1).sum()); days = (z0 - a0).days
    out["A2 OKX funding window"] = [str(a0), str(z0), len(fo)]
    out["A2 funding paid by the book per year (15%-vol units): Binance vs OKX"] = [round(cb / days * 365, 4), round(co / days * 365, 4)]
    print("A2", out["A2 funding paid by the book per year (15%-vol units): Binance vs OKX"], flush=True)

# ---- B: one-hour delay ---------------------------------------------------------------------------------------------------
p0 = pnl(net, r, fund, 5.0) + ev_pnl; p1 = pnl(net.shift(1).fillna(0.0), r, fund, 5.0) + ev_pnl
out["B Binance, on time Sharpe D/T/H"] = sharpe(p0); out["B Binance, every target 1 h late Sharpe D/T/H"] = sharpe(p1)
print("B", out["B Binance, on time Sharpe D/T/H"], out["B Binance, every target 1 h late Sharpe D/T/H"], flush=True)

# ---- C: measured MT5 swaps -------------------------------------------------------------------------------------------------
spec = pd.read_csv(sorted(glob.glob(str(ROOT / "research_data/firm_specs/BrightFunded*20261021*.csv")))[-1], encoding="latin1")
spec = spec[spec.is_crypto == True].copy(); spec["coin"] = spec.symbol.str.split("/").str[0].replace({"XDG": "DOGE"})
k = spec.point * spec.contract_size / spec.notional_1lot_usd * 1e4
sl = pd.Series((spec.swap_long * k).values, index=spec.coin); ss = pd.Series((spec.swap_short * k).values, index=spec.coin)
sp = pd.Series(spec.spread_bp_median.values, index=spec.coin)
cfd = [c for c in U if c in sl.index]
out["C coins with a BrightFunded MT5 CFD"] = len(cfd)
out["C swap bp/day on these coins: median long / short"] = [round(float(sl[cfd].median()), 2), round(float(ss[cfd].median()), 2)]
out["C swap % per year, long side: BTC / ETH / median"] = [round(float(sl["BTC"] * 3.65), 1), round(float(sl["ETH"] * 3.65), 1), round(float(sl[cfd].median() * 3.65), 1)]
T = net.copy(); T[[c for c in U if c not in cfd]] = 0.0
cst = pd.Series({c: 3.25 + 0.5 * float(sp.get(c, 0.0)) if c in cfd else 0.0 for c in U})
zero = fund * 0.0
base = pnl(T, r, zero, cst) + ev_pnl
mid = T.index.hour == 0
Lw = T.clip(lower=0) * sl.reindex(U).fillna(0.0) / 1e4; Sw = (-T.clip(upper=0)) * ss.reindex(U).fillna(0.0) / 1e4
swap = (Lw + Sw).sum(axis=1).where(mid, 0.0)                                 # swap rates are negative = cost
out["C CFD route, swap-free Sharpe D/T/H"] = sharpe(base)
out["C CFD route, measured swaps Sharpe D/T/H"] = sharpe(base + swap)
out["C swap cost per year (15%-vol units, book return about 0.45)"] = round(float(-swap.mean() * 24 * 365), 3)
print("C", out["C CFD route, swap-free Sharpe D/T/H"], out["C CFD route, measured swaps Sharpe D/T/H"], out["C swap cost per year (15%-vol units, book return about 0.45)"], flush=True)
json.dump(out, open(ROOT / "results/gen331.json", "w"), indent=1, default=str)
