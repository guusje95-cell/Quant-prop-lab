"""Gen379 (config/gen379_protocol.json): diversifier basket. Writes results/gen379.json.   cd scripts && python gen379_basket.py <v86 dump>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s373 = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s373, "g373", "exec"), g)
CS, B, H0, END = g["CS"], g["B"], g["H0"], g["END"]
from qpl.lab.data import stablecoin_caps
ND = ROOT / "research_data/newdata"
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
K1C = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
base = H0[K1C].assign(**{"C*": g["cp"]}); K1 = unit(CS.portfolio_v5(base)[0]); REF = (shp(K1), per(K1))
idx = H0.index; days = pd.date_range("2019-06-01", END[:10], freq="D")
mkd = lambda w, c: CS._from_daily_weights(w.fillna(0.0), c, 5).reindex(idx).fillna(0.0)
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
def daily(s, how="last"):
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); s = getattr(s.groupby(level=0), how)()
    return s.reindex(days).ffill().shift(1)
P = {}
cap = stablecoin_caps(); cap = cap.where(cap > 0).loc["2019":]; gg = cap.pct_change().shift(2).reindex(days)          # Gen345 A, as registered
sig = (gg > 0.005).astype(float).rolling(3, min_periods=1).max(); P["mint shock"] = mkd(pd.DataFrame({"BTC": 0.5 * sig, "ETH": 0.5 * sig}), ["BTC", "ETH"])
# Gen346 A, as registered
def rdp(f):
    x = pd.read_parquet(f); x.index = pd.DatetimeIndex(x.index); return x[~x.index.duplicated()].sort_index()
pos = {}; Rh = {}
for c in ("BTC", "ETH"):
    cb = rdp(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"].reindex(idx); sp = rdp(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet")["close"].reindex(idx)
    pr = cb / sp - 1; zz = (pr - pr.rolling(720, min_periods=500).mean().shift(1)) / pr.rolling(720, min_periods=500).std().shift(1)
    s = np.where(zz > 2, 0.5, np.where(zz < -2, -0.5, 0.0)); o = np.zeros(len(s))
    for t in np.flatnonzero(s != 0):
        o[t + 1:min(t + 5, len(s))] = s[t]
    pos[c] = pd.Series(o, index=idx)
    k = B.k5(c).close.resample("1h").last().reindex(idx); Rh[c] = k.pct_change().fillna(0.0)
    f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); Rh[c + "_f"] = f.groupby(level=0).sum().reindex(idx).fillna(0.0)
P["Coinbase hourly premium"] = sum(pos[c] * Rh[c] - pos[c] * Rh[c + "_f"] - pos[c].diff().abs().fillna(0.0) * 5 / 1e4 for c in ("BTC", "ETH"))
# Gen376 N2, N3, N4, as registered
st = daily(pd.read_parquet(ND / "defillama_stablecoins.parquet")["stablecoin_usd"]); n2 = z(np.log(st).diff(30), 365)
P["stablecoin impulse"] = mkd(pd.DataFrame({"BTC": 0.125 * n2.clip(-2, 2) / 2, "ETH": 0.125 * n2.clip(-2, 2) / 2}), ["BTC", "ETH"])
n3 = z(daily(pd.read_parquet(ND / "bc_transaction-fees-usd.parquet")["transaction-fees-usd"]), 90)
P["fee pressure"] = mkd(pd.DataFrame({"BTC": -0.25 * n3.clip(-2, 2) / 2}), ["BTC"])
P["Bybit crowding"] = mkd(pd.DataFrame({c: -0.25 * z(daily(pd.read_parquet(ND / f"bybit_{c}_account_ratio_1d.parquet")["buyRatio"]), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")}), ["BTC", "ETH"])
# Gen374 crash 8h on the point-in-time top-60 (hourly), as registered
g4 = {"__file__": str(ROOT / "scripts/gen374_diversifiers_pit.py")}
s4 = open(ROOT / "scripts/gen374_diversifiers_pit.py").read().split("\nsh = lambda d, a, z")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s4, "g374", "exec"), g4)
U = g4["uni_pit"]; Uh = U.shift(1).reindex(g4["idx"].floor("D")).set_axis(g4["idx"]).fillna(False)
i4, n4, r8, sd8, uph = g4["idx"], g4["n"], g4["r8"], g4["sd8"], g4["uph"]; cn = g4["coins"]
bnd = np.flatnonzero(i4.hour % 8 == 7); R8 = r8.where(Uh).to_numpy(); SD8 = sd8.to_numpy(); uu = uph.to_numpy(); ev = []
for t in bnd:
    if uu[t]:
        ev += [(t, j) for j in np.flatnonzero(np.nan_to_num(R8[t]) < -3 * np.nan_to_num(SD8[t], nan=np.inf))]
ev.sort(); P8 = np.zeros((n4, len(cn))); ends = []
for t, j in ev:
    ends = [e for e in ends if e > t]
    if len(ends) >= 8 or t + 1 >= n4:
        continue
    P8[t + 1:min(t + 25, n4), j] = 0.1; ends.append(t + 24)
P["crash 8h pit"] = g4["pnl"](pd.DataFrame(P8, index=i4, columns=cn)).reindex(idx).fillna(0.0)
# selection
out = {"reference K1": [REF[0], REF[1]], "pool": {}}; kept = []
for nm, h in P.items():
    s = per(h); c = round(float(pd.concat([dd(h), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)
    pc = max([abs(float(pd.concat([dd(h), dd(P[k])], axis=1).loc["2022":END].corr().iloc[0, 1])) for k in kept], default=0.0)
    keep = bool(min(s) > 0 and abs(c) < 0.3 and pc < 0.7); out["pool"][nm] = {"2022 / 2023-24 / 2025-26": s, "corr K1": c, "max corr with kept": round(pc, 3), "kept": keep}
    if keep:
        kept.append(nm)
    print(nm, out["pool"][nm], flush=True)
Dk = pd.DataFrame({k: dd(P[k]) for k in kept}).loc["2022":END]; sdv = Dk.loc[:"2024"].std()
bh = sum(P[k] / sdv[k] for k in kept); bh = bh * 0.15 / (dd(bh.loc["2022":"2024"]).std() * np.sqrt(365))
b = unit(CS.portfolio_v5(base.assign(**{"diversifier basket": bh}))[0]); B1, k = shp(b), per(b)
out["basket"] = {"members": kept, "basket 2022 / 2023-24 / 2025-26": per(bh), "basket 2022-26": shp(bh), "corr K1": round(float(pd.concat([dd(bh), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
                 "K1 + basket": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
print(json.dumps(out["basket"]), flush=True)
bh.to_frame("basket").to_parquet(ROOT / "results/gen379_basket_hourly.parquet")
(ROOT / "results/gen379.json").write_text(json.dumps(out, indent=1)); print("DONE")
