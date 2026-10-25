"""Gen377 (config/gen377_protocol.json): K1 robustness, honest BrightFunded book, joint account plan. Writes results/gen377.json.
    cd scripts && python gen377_plan.py <v86 dump> <bf26 dump>"""
import json
import sys
from dataclasses import replace
from math import e
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
DUMP, BFD = sys.argv[1], sys.argv[2]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s373 = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s373, "g373", "exec"), g)
CS, PF, H0, END = g["CS"], g["PF"], g["H0"], g["END"]; to_daily_stop = g["to_daily_stop"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a="2022", z=END: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
K1C = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
base = H0[K1C].assign(**{"C*": g["cp"]}); K1 = unit(CS.portfolio_v5(base)[0])
out = {"K1": [shp(K1), per(K1)]}
# ---- 1. robustness
d = dd(K1).loc["2022":END]; T = len(d); sr = d.mean() / d.std(); g3, g4 = skew(d), kurtosis(d, fisher=False); gam = 0.5772156649
ds = {}
for N in (300, 1600):
    sr0 = np.sqrt(1.0 / T) * ((1 - gam) * norm.ppf(1 - 1 / N) + gam * norm.ppf(1 - 1 / (N * e)))
    ds[f"N={N}"] = {"SR0": round(float(sr0 * np.sqrt(365)), 3), "DSR": round(float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))), 4),
                    "planning Sharpe = SR - SR0": round(float((sr - sr0) * np.sqrt(365)), 3)}
rng = np.random.default_rng(7); x = d.to_numpy(); bs = []
for _ in range(2000):
    st = rng.integers(0, T - 20, size=T // 20 + 1); y = np.concatenate([x[s:s + 20] for s in st])[:T]; bs.append(y.mean() / y.std() * np.sqrt(365))
out["1 deflated Sharpe"] = ds; out["1 bootstrap 90% interval 2022-26"] = [round(float(np.percentile(bs, 5)), 2), round(float(np.percentile(bs, 95)), 2)]
out["1 leave one out"] = {s: [shp(b := unit(CS.portfolio_v5(base.drop(columns=s))[0])), per(b)] for s in K1C}
pl = {}
for n in (8, 12):
    w = g["own_size"]((g["dv"].where(g["elig"]).rank(axis=1, ascending=False) <= n)[g["mfirst"]].reindex(g["Dc"].index).ffill().fillna(False).astype(bool), n)
    c = g["hourly"](w).reindex(H0.index).fillna(0.0); b = unit(CS.portfolio_v5(base.assign(**{"C*": c}))[0]); pl[f"top-{n}"] = {"C* alone": per(c), "K1": [shp(b), per(b)]}
out["1 C* plateau"] = pl; print(json.dumps(out, indent=0), flush=True)
# ---- 2. honest BrightFunded book
BH = pd.read_parquet(BFD).drop(columns="port").loc[:END + " 23:00"]
bfk = unit(CS.portfolio_v5(BH.drop(columns=[c for c in ("premium carry", "premium carry BF") if c in BH]))[0])
bf26 = unit(CS.portfolio_v5(BH)[0])
out["2 BrightFunded"] = {"bf2.6 rebuilt (no cap)": [shp(bf26), per(bf26)], "honest bf (no carry)": [shp(bfk), per(bfk)],
                         "corr honest bf vs K1 (daily 2022-26)": round(float(pd.concat([dd(bfk), dd(K1)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3)}
print(json.dumps(out["2 BrightFunded"]), flush=True)
# ---- 3. joint account plan
P = PF.PRESETS; HY = P["HyroTrader Two-Step $200k"]
CFT = replace(P["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
BF = replace(P["BrightFunded Two-Step Classic $200k"], fee=P["BrightFunded Two-Step Classic $200k"].fee * 1.1)
MFP = replace(HY, name="MFP Signature 100k", account=100000, fee=696.0, targets=(0.10,), daily_loss=0.03, max_loss=0.06, max_type="static", min_days=0, payout_min=0)
ACC = [("1 HyroTrader $200k", HY, "k1", 2.0, 1.5, 0.5, 0), ("2 CFT $200k", CFT, "k1", 2.0, 1.5, 0.5, 0),
       ("3 BrightFunded $200k", BF, "bf", 2.0, 1.5, 0.5, -2), ("4 MyFundedPerps $100k", MFP, "k1", 1.0, 2.0, 0.4, 4)]
shift_to = lambda h, tg: h - (dd(h.loc["2022":]).mean() - tg * dd(h.loc["2022":]).std() / np.sqrt(365)) / 24
plan_k1 = ds["N=1600"]["planning Sharpe = SR - SR0"]; plan_bf = round(shp(bfk) - (shp(K1) - plan_k1), 3)
A, Z = "2025-01-01", END + " 23:00"
for lvl, ser in (("backtest", {"k1": K1, "bf": bfk}), ("planning (K1 %.2f, bf %.2f)" % (plan_k1, plan_bf), {"k1": unit(shift_to(K1, plan_k1)), "bf": unit(shift_to(bfk, plan_bf))})):
    frames = {}
    for nm, f, k, sc, sf, stp, reset in ACC:
        x = ser[k].loc[A:Z].copy(); x.index = x.index - pd.Timedelta(hours=reset)
        frames[nm] = (to_daily_stop(x * sc, stp * f.daily_loss), to_daily_stop(x * sf, stp * f.daily_loss))
    idx = pd.DatetimeIndex(sorted(set.intersection(*[set(v[0].index) for v in frames.values()])))
    paths, cal0 = PF._paths(pd.DataFrame(index=idx, data={"net": 0.0}), "bootstrap", 730, 1, 400, 20, 11)
    per_day = len(idx) / max(1, cal0[-1]); NET = {}
    for nm, f, k, sc, sf, stp, reset in ACC:
        ch, fd = frames[nm]; ch, fd = ch.reindex(idx).fillna(0.0), fd.reindex(idx).fillna(0.0)
        rc, loc, hic = PF._arrays(ch, 1.0); rf, lof, hif = PF._arrays(fd, 1.0); nets = []
        for _, xx in paths:
            cal = (np.arange(len(xx)) / per_day).astype(int)
            nets.append(PF._ledger(rc[xx], loc[xx], hic[xx], rf[xx], lof[xx], hif[xx], cal, 0, len(xx), f, 5)["net"])
        NET[nm] = np.array(nets)
    N = pd.DataFrame(NET); q = lambda v, p: round(float(np.percentile(v, p)))
    res = {"per account": {nm: {"mean": round(float(N[nm].mean())), "p10": q(N[nm], 10), "P_profit": round(float((N[nm] > 0).mean()), 3)} for nm in N},
           "stack": {}, "P(every account loses)": round(float((N < 0).all(axis=1).mean()), 3),
           "mean pairwise corr of outcomes": round(float(N.corr().values[np.triu_indices(len(N.columns), 1)].mean()), 3)}
    for k in range(1, len(N.columns) + 1):
        t = N.iloc[:, :k].sum(axis=1)
        res["stack"][" + ".join(c.split(" ")[1] for c in N.columns[:k])] = {"mean": round(float(t.mean())), "p10": q(t, 10), "p50": q(t, 50), "P_loss": round(float((t < 0).mean()), 3)}
    out[f"3 account plan, {lvl}"] = res; print(lvl, json.dumps(res), flush=True)
(ROOT / "results/gen377.json").write_text(json.dumps(out, indent=1)); print("DONE")
