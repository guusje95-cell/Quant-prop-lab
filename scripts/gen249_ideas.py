"""Gen249 (config/gen249_protocol.json): USDT premium, ETH-BTC Coinbase premium spread, Weiss on every Friday. Writes results/gen249.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import ridge_live as RL
END = "2026-09-30"
g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, CB, IDXbf, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
P1 = q["p1"]()
v = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], v)
H6, B = v["H6"], v["B"]
IDX1 = IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))
days = pd.date_range("2020-01-01", END)
D = RL.predictions(END); ridge_ref = D.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
perp = lambda w: CS._from_daily_weights(w, list(w.columns), 5).loc[:END + " 23:00"]
cfd = lambda w: sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDX1))
book = lambda cols: CS.portfolio_v5(pd.concat(cols, axis=1).fillna(0.0))[0]
hr_v7 = perp(ridge_ref).rename("ridge ML"); IS0 = (P6 + R1 + P1).rename("vol-managed indices"); hbr = hb.rename("ridge ML")
v7 = book([H6, hr_v7]); bf2 = book([HB0, IS0, hbr])
ref = {"v7": (sh(v7, "2022-01-01", END), per(v7, "2022-01-01")), "bf2": (sh(bf2, "2022-01-01", END), per(bf2, "2022-01-01"))}
out = {"reference": {k: [round(a, 3), np.round(b, 3).tolist()] for k, (a, b) in ref.items()}}; print(out, flush=True)
cst = H6["C*"].groupby(H6.index.floor("D")).sum()
corr_c = lambda h: round(float(pd.concat([cst, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2021":].corr().iloc[0, 1]), 3)


def strict(name, b):
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01"); B0, k0 = ref[name]
    return {"book": [round(B1, 3), np.round(k1, 3).tolist()], "strict": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}


def evaluate(name, w, d0):
    hp, hc = perp(w), cfd(w); sp, sc = per(hp, d0), per(hc, d0)
    r = {"sleeve perp D/T/H": np.round(sp, 3).tolist(), "corr C*": corr_c(hp), "sleeve CFD D/T/H": np.round(sc, 3).tolist(),
         "v7": strict("v7", book([H6, hr_v7, hp.rename(name)])), "bf2": strict("bf2", book([HB0, IS0, hbr, hc.rename(name)]))}
    r["pass v7"] = bool(sp[0] > 0 and sp[1] >= 0.8 and sp[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v7"]["strict"])
    r["pass bf2"] = bool(sc[0] > 0 and sc[1] >= 0.5 and sc[2] >= 0.3 and r["bf2"]["strict"])
    out[name] = r; print(name, json.dumps(r), flush=True)
    json.dump(out, open(ROOT / "results/gen249.json", "w"), indent=1)


# A: USDT premium
ut = pd.read_parquet(ROOT / "research_data/coinbase/USDT-USD_1h.parquet")["close"]; ut.index = pd.DatetimeIndex(ut.index)
p24 = (ut - 1).rolling(24, min_periods=20).mean(); z = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
zd = z[z.index.hour == 23]; zd.index = zd.index.floor("D"); zd = zd.reindex(days)
s = pd.Series(np.where(zd > 1, 0.25, np.where(zd < -1, -0.25, 0.0)), index=days)
evaluate("A USDT premium", pd.DataFrame({"BTC": s, "ETH": s}), "2021-06-01")
# B: ETH - BTC Coinbase premium spread
zc = RL.features(END).pivot(index="day", columns="coin", values="zc").reindex(days)
sp_ = zc["ETH"] - zc["BTC"]; zs = (sp_ - sp_.rolling(30, min_periods=20).mean()) / sp_.rolling(30, min_periods=20).std()
t = pd.Series(np.where(zs > 1, 0.25, np.where(zs < -1, -0.25, 0.0)), index=days)
evaluate("B ETH-BTC premium spread", pd.DataFrame({"BTC": -t, "ETH": t}), "2021-01-01")


# C: Weiss on every Friday (replaces the last-Friday sleeve)
def weiss_all(coins=("BTC", "ETH")):
    pnl_all, held = [], {}
    for coin in coins:
        k = B.k5(coin); h = k.close.resample("1h").last().loc[:END]; o = k.open
        pnl = pd.Series(0.0, index=h.index); held[coin] = pd.Series(0.0, index=h.index)
        for d in pd.date_range("2020-01-03", pd.Timestamp(END).normalize(), freq="W-FRI"):
            t7, t8, t9, t10 = (d + pd.Timedelta(hours=x) for x in (7, 8, 9, 10))
            if not all(t in o.index for t in (t7, t8)):
                continue
            pre = o[t8] / o[t7] - 1
            if pre == 0:
                continue
            side = -np.sign(pre); held[coin][[t for t in (t8, t9) if t in held[coin].index]] = side / len(coins)
            if t10 in o.index and t10 in pnl.index:
                pnl[t10] += side * (o[t9] / o[t8] - 1) - 5 / 1e4 + side * (o[t9] / o[t8]) * (o[t10] / o[t9] - 1) - 5 / 1e4
        pnl_all.append(pnl)
    return pd.concat(pnl_all, axis=1).fillna(0).mean(axis=1), pd.DataFrame(held).fillna(0.0)


wpnl, wpos = weiss_all()
_, mpos = CS.weiss_expiry(positions=True)                 # sanity: the CFD P&L recipe reproduces bf's own Weiss column
chk = CB.sleeve_pnl(mpos.reindex(columns=CB.CFD).fillna(0.0), CB.hourly_returns(pd.Timestamp(END + " 23:00"))).reindex(HB0.index).fillna(0.0)
print("Weiss CFD recipe check, max diff vs HB0:", float((chk - HB0["Weiss expiry"]).abs().max()), flush=True)
H6c = H6.copy(); H6c["Weiss expiry"] = wpnl.reindex(H6c.index).fillna(0.0)
HBc = HB0.copy(); HBc["Weiss expiry"] = CB.sleeve_pnl(wpos.reindex(columns=CB.CFD).fillna(0.0), CB.hourly_returns(pd.Timestamp(END + " 23:00"))).reindex(HBc.index).fillna(0.0)
mon = H6["Weiss expiry"]; fr = wpnl
C = {"every-Friday sleeve D/T/H": np.round(per(fr, "2020-01-01"), 3).tolist(), "last-Friday sleeve D/T/H": np.round(per(mon, "2020-01-01"), 3).tolist(),
     "v7": strict("v7", book([H6c, hr_v7])), "bf2": strict("bf2", book([HBc, IS0, hbr]))}
C["pass v7"], C["pass bf2"] = C["v7"]["strict"], C["bf2"]["strict"]
out["C Weiss every Friday"] = C; print("C", json.dumps(C), flush=True)
json.dump(out, open(ROOT / "results/gen249.json", "w"), indent=1)
