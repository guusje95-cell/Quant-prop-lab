"""Gen375 (config/gen375_protocol.json): A prop settings for K1, B factors on an established-coin point-in-time universe.
Writes results/gen375.json.   cd scripts && python gen375_research.py <v86 dump parquet>"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
exec(open(ROOT / "scripts/gen326_wide_carry.py").read().split("\nimport os\nREF")[0])      # S, H, P, QV, mon-inputs, r, F, coins (TradFi excluded)
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"; HY = PF.PRESETS["HyroTrader Two-Step $200k"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a, z: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
shift_to = lambda h, tg: h - (dd(h).mean() - tg * dd(h).std() / np.sqrt(365)) / 24
K1 = pd.read_parquet(ROOT / "results/gen373_book_hourly.parquet")["book"]


def prop(h, a, z, rc=2.0, rf=1.5, st=0.5):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * rc, st * HY.daily_loss), HY, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * rf, st * HY.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}


out = {"reference K1": {"Sharpe": [shp(K1, "2022", END), per(K1)]}}
# ---- A: prop settings
A = {}
for rc in (1.5, 2.0, 2.5):
    for rf in (1.0, 1.5, 2.0):
        for st in (0.4, 0.5, 0.6):
            A[f"{rc}/{rf}/{st}"] = prop(K1, "2022-01-01", "2024-12-31 23:00", rc, rf, st)
cur = A["2.0/1.5/0.5"]
ok = {k: v for k, v in A.items() if v["P_profit"] >= 0.95 and v["p10"] >= 0.9 * cur["p10"]}
best = max(ok, key=lambda k: ok[k]["net"]); adopt = best != "2.0/1.5/0.5" and ok[best]["net"] >= cur["net"] + 5000
ch = best if adopt else "2.0/1.5/0.5"; rc, rf, st = map(float, ch.split("/"))
pl = shift_to(K1.loc["2025":], 1.37)
out["A prop settings"] = {"grid 2022-24 (challenge/funded/stop)": A, "best eligible": best, "adopted": adopt, "setting": ch,
                          "chosen 2025-26 (holdout)": prop(K1, "2025-01-01", END + " 23:00", rc, rf, st), "current 2025-26": prop(K1, "2025-01-01", END + " 23:00"),
                          "chosen at planning 1.37": prop(pl, "2025-01-01", END + " 23:00", rc, rf, st), "current at planning 1.37": prop(pl, "2025-01-01", END + " 23:00")}
print(json.dumps({k: v for k, v in out["A prop settings"].items() if k != "grid 2022-24 (challenge/funded/stop)"}), flush=True)
# ---- B: factors on an established-coin point-in-time universe
listed365 = P.notna().cumsum() >= 365; live = P.notna() & P.ffill().notna()
mon30 = QV.rolling(30, min_periods=20).sum().where(listed365 & live)
uni = mon30.rank(axis=1, ascending=False).le(30)
fund_d = F.groupby(F.index.floor("D")).sum().reindex(P.index).rolling(7).mean()
ret28 = P / P.shift(28) - 1
iv = (1 / P.pct_change(fill_method=None).rolling(30).std())


def xs(score):                                         # long the top third of `score`, short the bottom third, inverse-vol legs, 7 tranches
    rk = score.where(uni).rank(axis=1, pct=True); v = iv.where(uni)
    wl, ws = v.where(rk > 2 / 3, 0.0), v.where(rk <= 1 / 3, 0.0)
    w = CS._hold(wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0), 7, True)
    wd = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    held = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0).where(H.ffill().notna(), 0.0)
    turn = wd.fillna(0.0).diff().abs().sum(axis=1).reindex(H.index.floor("D")).set_axis(H.index).where(H.index.hour == 0, 0.0)
    return ((held * r).sum(axis=1) - (held * F).sum(axis=1) - turn.fillna(0.0) * 5 / 1e4).loc[:END + " 23:00"]


H0 = pd.read_parquet(DUMP).drop(columns="port").loc[:END + " 23:00"]
cp = None
k1cols = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
# K1 sleeves: the point-in-time C* is rebuilt exactly as in Gen373
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}; s373 = open(ROOT / "scripts/gen373_honest_cstar.py").read()
s373 = s373.split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s373, "g373", "exec"), g); cpit = g["cp"]
base = H0[k1cols].assign(**{"C*": cpit})
b0 = unit(CS.portfolio_v5(base)[0]); out["K1 rebuilt (check)"] = [shp(b0, "2022", END), per(b0)]
REF = (shp(b0, "2022", END), per(b0))
B = {}
for nm, sc in (("B1 premium carry", -prem), ("B2 funding carry", -fund_d), ("B3 momentum 28d", ret28)):
    h = xs(sc).reindex(H0.index).fillna(0.0)
    b = unit(CS.portfolio_v5(base.assign(**{nm: h}))[0]); B1, k = shp(b, "2022", END), per(b)
    B[nm] = {"sleeve 2022 / 2023-24 / 2025-26": per(h), "corr with K1 (daily)": round(float(pd.concat([dd(h), dd(b0)], axis=1).loc["2022":].corr().iloc[0, 1]), 3),
             "K1 + sleeve": [B1, k], "pass": bool(B1 >= REF[0] + 0.05 and all(k[i] >= REF[1][i] for i in range(3)))}
    if B[nm]["pass"]:
        B[nm]["HyroTrader 2022-24 / 2025-26"] = [prop(b, "2022-01-01", "2024-12-31 23:00"), prop(b, "2025-01-01", END + " 23:00")]
    print(nm, B[nm], flush=True)
out["B factors (universe: top-30 by volume among coins listed >= 365 days)"] = B
out["B universe mean size"] = round(float(uni.sum(axis=1).loc["2022":].mean()), 1)
(ROOT / "results/gen375.json").write_text(json.dumps(out, indent=1)); print("DONE")
