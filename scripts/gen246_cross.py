"""Gen246 (config/gen246_protocol.json): (A) ridge + VIX / US500 features in v7 and bf2, (B) P6 on DE40/UK100/JP225 in bf2.
Writes results/gen246.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import ridge_live as RL
END = "2026-09-30"
# ---- bf2 pieces (Gen234) and v6 sleeves (Gen109)
g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, CB, IDXbf, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
P1 = q["p1"](); hourly = q["hourly"]
v = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], v)
H6 = v["H6"]
IDX1 = IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))
ridge_ref = RL.predictions(END).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
perp = lambda w: CS._from_daily_weights(w, ["BTC", "ETH"], 5).loc[:END + " 23:00"]
cfd = lambda w: sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDX1))
book = lambda cols: CS.portfolio_v5(pd.concat(cols, axis=1).fillna(0.0))[0]
v7 = book([H6, perp(ridge_ref).rename("ridge ML")]); IS0 = (P6 + R1 + P1).rename("vol-managed indices")
bf2 = book([HB0, IS0, hb.rename("ridge ML")])
ref = {"v7": (sh(v7, "2022-01-01", END), per(v7, "2022-01-01")), "bf2": (sh(bf2, "2022-01-01", END), per(bf2, "2022-01-01"))}
print("reference", {k: (round(a, 3), np.round(b, 3).tolist()) for k, (a, b) in ref.items()}, flush=True)
out = {"reference": {k: [round(a, 3), np.round(b, 3).tolist()] for k, (a, b) in ref.items()}}


def strict(name, b):
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01"); B0, k0 = ref[name]
    return {"book": [round(B1, 3), np.round(k1, 3).tolist()], "strict": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}


# ---- A: ridge+ (VIX change, US500 day return)
D = RL.features(END); days = pd.DatetimeIndex(sorted(D["day"].unique()))
vix = pd.read_parquet(ROOT / "research_data/more2/vix_VIX.parquet")["close"]; vix.index = pd.DatetimeIndex(vix.index).normalize()
vix1 = (vix / vix.shift(1) - 1).reindex(days).fillna(0.0)
us = hourly("US500")["close"]; usd = us.groupby(us.index.floor("D")).last(); spx1 = (usd / usd.shift(1) - 1).reindex(days).fillna(0.0)
D["vix1"] = D["day"].map(vix1); D["spx1"] = D["day"].map(spx1)
feats = [x for x in D.columns if x not in ("day", "target", "coin")]
pred = pd.Series(np.nan, index=D.index)
for m in pd.date_range("2021-01-01", END, freq="MS"):
    tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
    te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
    mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
    Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
    mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
    pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
D["p"] = pred; wp = D.pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
hp, hc = perp(wp), cfd(wp)
sp, sc = per(hp, "2021-01-01"), per(hc, "2021-01-01")
A = {"sleeve perp D/T/H": np.round(sp, 3).tolist(), "sleeve CFD D/T/H": np.round(sc, 3).tolist(),
     "v7": strict("v7", book([H6, hp.rename("ridge ML")])), "bf2": strict("bf2", book([HB0, IS0, hc.rename("ridge ML")]))}
A["pass v7"] = bool(sp[0] > 0 and sp[1] >= 0.8 and sp[2] >= 0.5 and A["v7"]["strict"])
A["pass bf2"] = bool(sc[0] > 0 and sc[1] >= 0.5 and sc[2] >= 0.3 and A["bf2"]["strict"])
out["A ridge+"] = A; print("A", json.dumps(A), flush=True)

# ---- B: P6 on DE40 / UK100 / JP225 (2/3 scale, 2 bp)
legs = []
for s in ("DE40", "UK100", "JP225"):
    x = hourly(s)["close"].reindex(IDXbf).ffill(limit=72); r = x.pct_change().fillna(0.0)
    dret = r.groupby(r.index.floor("D")).sum(); vol = dret.rolling(20).std() * np.sqrt(252)
    wh = (2 / 3 * 0.5 * (0.15 / vol).clip(upper=2.0)).shift(1).reindex(IDXbf.floor("D")).set_axis(IDXbf).fillna(0.0)
    legs.append(wh * r - wh.diff().abs().fillna(0.0) * 2e-4)
P6i = sum(legs); pl = per(P6i, "2020-01-01")
Bres = {"leg D/T/H": np.round(pl, 3).tolist(), "bf2": strict("bf2", book([HB0, (IS0 + P6i).rename("vol-managed indices"), hb.rename("ridge ML")]))}
Bres["pass"] = bool(pl[0] > 0 and pl[1] >= 0.5 and pl[2] >= 0.3 and Bres["bf2"]["strict"])
out["B P6 international"] = Bres; print("B", json.dumps(Bres), flush=True)
json.dump(out, open(ROOT / "results/gen246.json", "w"), indent=1)
