"""Gen342 (config/gen342_protocol.json): catalogue of earlier crypto sleeves, selection on 2020-24, orthogonal book judged on 2025-26.
Writes results/gen342.json and results/gen342_sleeves.parquet."""
import glob
import json
import sys
import types
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END; ROOT = L.ROOT; CAP = {}
_dump = json.dump; json.dump = lambda *a, **k: None                       # do not overwrite the old result files
_judge = L.judge


def cap(name, h, out, dev_start="2020-01-01", replace_ridge=False):
    CAP[name] = h.reindex(L.H6.index).fillna(0.0); out[name] = {"pass": False, "v7": [0.0, [0.0, 0.0, 0.0]]}; return out[name]


L.judge = cap
sys.modules["bf2lab"] = types.SimpleNamespace(judge=lambda *a, **k: None, cfd=lambda w: None, REF=(0.0, [0.0, 0.0, 0.0]))


def run(script, cut=None):
    src = open(ROOT / "scripts" / script).read()
    if cut:
        src = src.split(cut)[0]
    g = {"__file__": str(ROOT / "scripts" / script), "__name__": "x"}; exec(compile(src, script, "exec"), g); return g


for s, cut in (("gen261_volshare.py", None), ("gen265_attention.py", "# B: de-risk"), ("gen274_participation.py", None), ("gen279_bitfinex.py", None),
               ("gen312_kimchi_btceth.py", None), ("gen334_new_sleeves.py", None)):
    run(s, cut); print("captured", s, sorted(CAP)[-3:], flush=True)
g341 = run("gen341_orthogonal.py", "\nfor nm, h in ((")
for k, v in (("Gen341 A funding-settlement pressure", "A"), ("Gen341 B residual reversal", "Bs"), ("Gen341 C pump reversal", "C")):
    CAP[k] = g341[v].loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
CAP = {k: v for k, v in CAP.items() if "descriptive" not in k}
perp = lambda w, c=5: CS._from_daily_weights(w, list(w.columns), c).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
days = pd.date_range("2020-01-01", END)
# Gen249 A / B
import ridge_live as RL
ut = pd.read_parquet(ROOT / "research_data/coinbase/USDT-USD_1h.parquet")["close"]; ut.index = pd.DatetimeIndex(ut.index)
p24 = (ut - 1).rolling(24, min_periods=20).mean(); z = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
zd = z[z.index.hour == 23]; zd.index = zd.index.floor("D"); zd = zd.reindex(days)
s = pd.Series(np.where(zd > 1, 0.25, np.where(zd < -1, -0.25, 0.0)), index=days); CAP["Gen249 A USDT premium"] = perp(pd.DataFrame({"BTC": s, "ETH": s}))
zc = RL.features(END).pivot(index="day", columns="coin", values="zc").reindex(days)
sp_ = zc["ETH"] - zc["BTC"]; zs = (sp_ - sp_.rolling(30, min_periods=20).mean()) / sp_.rolling(30, min_periods=20).std()
t = pd.Series(np.where(zs > 1, 0.25, np.where(zs < -1, -0.25, 0.0)), index=days); CAP["Gen249 B ETH-BTC premium spread"] = perp(pd.DataFrame({"BTC": -t, "ETH": t}))
# Gen202 VM / BCX / R1X (7.5 bp as registered)
src = open(ROOT / "scripts/gen202_transfer_crypto.py").read(); g = {"CS": CS, "pd": pd, "np": np}
exec(src[src.index("COINS = "):src.index("\nout = {")], g)
for kind in ("VM", "BCX", "R1X"):
    CAP[f"Gen202 {kind}"] = perp(g["weights"](kind), 7.5)
# Gen187 oil timing
import futures_db as F
cl = (1 + F.daily("CL").r.fillna(0.0)).cumprod(); cl = cl[cl.index.weekday < 5]
so = cl / cl.shift(21) - 1; me = cl.index.to_series().groupby(cl.index.to_period("M")).max()
w = pd.DataFrame(0.0, index=pd.date_range("2020-01-01", "2026-10-01"), columns=["BTC", "ETH"])
for d in me:
    if d < w.index[0] or not np.isfinite(so.loc[d]) or so.loc[d] >= 0:
        continue
    w.loc[d:(d + pd.offsets.MonthEnd(1)).normalize() - pd.Timedelta(days=1)] = 0.5
CAP["Gen187 oil timing"] = perp(w, 7.5)
# Gen171 CC1 / CC2
c = {"__file__": str(ROOT / "scripts/gen161_vm_calendar.py")}; exec(open(ROOT / "scripts/gen161_vm_calendar.py").read().split("def sleeves(")[0], c); M = c["M"]
d171 = pd.date_range("2020-01-01", "2026-10-01")
for n, m in (("CC1 FOMC weeks", M["FC"]), ("CC2 calendar union", pd.concat(M.values(), axis=1).max(axis=1))):
    act = set(m[m > 0].index); w = pd.DataFrame(0.0, index=d171, columns=["BTC", "ETH"])
    for d in d171[1:]:
        if d in act:
            w.loc[d - pd.Timedelta(days=1)] = 0.5
    CAP[f"Gen171 {n}"] = perp(w, 7.5)
# Gen120 D1 / D2
src = open(ROOT / "scripts/gen120_deribit.py").read(); g = {"ROOT": ROOT, "pd": pd, "np": np, "glob": glob, "SMOKE": False, "sys": sys}
exec(src[src.index("def flow("):src.index("print(\"coverage")], g)
CAP["Gen120 D1 put-skew contrarian"] = perp(g["W1"]); CAP["Gen120 D2 call-minus-put flow"] = perp(g["W2"])
json.dump = _dump

S = pd.DataFrame(CAP); S.to_parquet(ROOT / "results/gen342_sleeves.parquet")
vd = L.V7.groupby(L.V7.index.floor("D")).sum()
D = S.groupby(S.index.floor("D")).sum().loc["2020-01-01":END]
out = {"catalogue": {}}


def shp(x, a, z):
    x = x.loc[a:z]; x = x[x.ne(0).cummax()] if (x != 0).any() else x
    return float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan


sel = []
for k in D.columns:
    x = D[k]; first = x.ne(0).idxmax()
    dev = shp(x, max(first, pd.Timestamp("2020-01-01")), "2022-12-31"); tst = shp(x, "2023-01-01", "2024-12-31"); hold = shp(x, "2025-01-01", END)
    c1 = float(pd.concat([x, vd], axis=1).loc["2022-01-01":"2024-12-31"].corr().iloc[0, 1]); c2 = float(pd.concat([x, vd], axis=1).loc["2025-01-01":END].corr().iloc[0, 1])
    ok = bool(dev > 0 and tst >= 0.5 and abs(c1) <= 0.25)
    out["catalogue"][k] = {"DEV / TEST": [round(dev, 2), round(tst, 2)], "corr v8.6 2022-24": round(c1, 3), "selected": ok,
                           "(HOLD, for the record) Sharpe / corr": [round(hold, 2), round(c2, 3)]}
    print(k, out["catalogue"][k], flush=True)
    if ok:
        sel.append(k)
out["selected"] = sel
if sel:
    sd = D[sel].loc[:"2024-12-31"].std(); Bk = (D[sel] / sd).sum(axis=1); Bk = Bk * 0.15 / (Bk.loc[:"2024-12-31"].std() * np.sqrt(365))
    bh = shp(Bk, "2025-01-01", END); bc = float(pd.concat([Bk, vd], axis=1).loc["2025-01-01":END].corr().iloc[0, 1])
    out["orthogonal book"] = {"Sharpe 2020-22 / 2023-24 / 2025-26": [round(shp(Bk, "2020-01-01", "2022-12-31"), 2), round(shp(Bk, "2023-01-01", "2024-12-31"), 2), round(bh, 2)],
                              "corr v8.6 2022-24 / 2025-26": [round(float(pd.concat([Bk, vd], axis=1).loc["2022":"2024"].corr().iloc[0, 1]), 3), round(bc, 3)],
                              "FOUND (HOLD >= 0.8 and |corr| <= 0.25)": bool(bh >= 0.8 and abs(bc) <= 0.25)}
    V = vd * 0.15 / (vd.loc["2022":"2024"].std() * np.sqrt(365)); mix = (V + Bk).dropna()
    out["v8.6 + book equal risk, Sharpe 2022-24 / 2025-26 (v8.6 alone)"] = [round(shp(mix, "2022-01-01", "2024-12-31"), 2), round(shp(mix, "2025-01-01", END), 2),
                                                                           round(shp(V, "2022-01-01", "2024-12-31"), 2), round(shp(V, "2025-01-01", END), 2)]
    Bk.to_frame("book").to_parquet(ROOT / "results/gen342_book.parquet")
print(json.dumps({k: v for k, v in out.items() if k != "catalogue"}, indent=1), flush=True)
_dump(out, open(ROOT / "results/gen342.json", "w"), indent=1)
