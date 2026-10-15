"""Gen63 checks for I5 (dip-buy): neighbours, 2x costs, overlap with the cascade sleeve, and the pre-registered final check
(does adding it raise the 2022-26 Sharpe of the equal-risk crypto portfolio?). Also the same final check for the near-misses I3/I6
(descriptive only). Writes results/gen63_check.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = (ROOT / "scripts/gen63_crypto.py").read_text()
g = {"__file__": str(ROOT / "scripts/gen63_crypto.py"), "__name__": "g63"}
exec(compile(src.split("# ---------------- I1:")[0], "g63", "exec"), g)
P, R, listed, pnl_w = g["P"], g["R"], g["listed"], g["pnl_w"]
import crypto_sleeves as CS

sh = lambda x, a, b: x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(365)


def dip(k=2.5, ma=100, hold=3, cap=3, cost=5):
    sd30 = R.rolling(30).std().shift(1); m = P.rolling(ma).mean()
    sig = (R < -k * sd30) & (P > m) & listed
    w = pd.DataFrame(0.0, index=P.index, columns=P.columns); active = {}
    for d in P.index:
        active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
        for c in sig.columns[sig.loc[d].fillna(False).to_numpy()]:
            if c not in active and len(active) < cap:
                active[c] = hold
        for c in active:
            w.at[d, c] = 0.2
    return pnl_w(w, cost / 1e4)


rows = []
for nm, kw in (("base k2.5 MA100 hold3", {}), ("2x costs", {"cost": 10}), ("k=2.0", {"k": 2.0}), ("k=3.0", {"k": 3.0}), ("MA50", {"ma": 50}),
               ("MA200", {"ma": 200}), ("hold 2", {"hold": 2}), ("hold 5", {"hold": 5}), ("max 5 open", {"cap": 5})):
    x = dip(**kw)
    rows.append({"variant": nm, "DEV": sh(x, "2020", "2022"), "TEST": sh(x, "2023", "2024"), "HOLD": sh(x, "2025", "2026"), "2023+": sh(x, "2023", "2026"),
                 "2022": (1 + x.loc["2022"]).prod() - 1})
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen63_check.csv", index=False)

H = CS.all_sleeves(); D = H.groupby(H.index.floor("D")).sum()
base = D[["C*", "premium carry", "cascade"]]
cands = {"I5 dip-buy": dip(), "I3 squeeze (near-miss)": None, "I6 4h trend (near-miss)": None}
F, B, C = g["F"], g["B"], g["C"]
fund3 = F.groupby(level=0).mean().reindex(P.index)
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].resample("1D").last() for c in C}).reindex(P.index)
sig3 = (fund3 < -0.0001) & (P / P.shift(3) - 1 > 0) & (oi / oi.shift(3) - 1 > 0) & listed
w3 = pd.DataFrame(0.0, index=P.index, columns=C); active = {}
for d in P.index:
    active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
    for c in sig3.columns[sig3.loc[d].fillna(False).to_numpy()]:
        if c not in active and len(active) < 5:
            active[c] = 3
    for c in active:
        w3.at[d, c] = 0.1
g["I3"] = pnl_w(w3)
fn_src = src[src.index("def trend4h"):src.index("i6 = pd.concat")]
exec(compile(fn_src, "i6", "exec"), g)
g["i6"] = pd.concat([g["trend4h"](c) for c in ("BTC", "ETH", "SOL")], axis=1).fillna(0).mean(axis=1)
cands["I3 squeeze (near-miss)"] = g["I3"]; cands["I6 4h trend (near-miss)"] = g["i6"]
print("corr I5 vs cascade:", round(pd.concat([cands["I5 dip-buy"], base["cascade"]], axis=1).loc["2022":].corr().iloc[0, 1], 2))


def port(df):
    z = df.loc["2022-01-01":"2026-09-30"].fillna(0.0)
    z = z / (z.std() * np.sqrt(365)) * 0.10
    x = z.mean(axis=1); x = x * 0.15 / (x.std() * np.sqrt(365))
    m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return {"Sharpe 2022-26": x.mean() / x.std() * np.sqrt(365), "Sharpe 2023+": sh(x, "2023", "2026"), "Positive months": (m > 0).mean(),
            "Max DD": (eq / eq.cummax() - 1).min(), "2022": (1 + x.loc["2022"]).prod() - 1}


print("current 3 sleeves:", {k: round(v, 3) for k, v in port(base).items()})
for nm, s in cands.items():
    print(f"+ {nm}:", {k: round(v, 3) for k, v in port(pd.concat([base, s.rename(nm)], axis=1)).items()})
print("+ I5 + I6:", {k: round(v, 3) for k, v in port(pd.concat([base, cands["I5 dip-buy"].rename("a"), cands["I6 4h trend (near-miss)"].rename("b")], axis=1)).items()})
