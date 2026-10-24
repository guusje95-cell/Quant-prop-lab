"""Gen366 (config/gen366_protocol.json). Writes results/gen366.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
S3 = pd.read_parquet(SB.ROOT / "results/gen363_sleeves.parquet").fillna(0.0)
_g = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen364_reversal.py").read().split("\nT = {")[0], "g364", "exec"), _g)
_k = {"__file__": __file__}; exec(compile(open(SB.ROOT / "scripts/gen365_crash8h.py").read().split("\ndef book(")[0], "g365", "exec"), _k)
S5 = pd.concat([S3, SB.daily(_g["disc"]()).rename("daily premium discount"), SB.daily(_k["pos"]()).rename("crash 8h")], axis=1, sort=True).fillna(0.0).loc["2020-01-01":SB.END]
fit = S5.loc[:"2024"]; sd = fit.std(); sr = fit.mean() / sd * np.sqrt(365)


def scale(bk):
    return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


C = {"C0 3 sleeves equal risk": scale((S5[list(S3.columns)] / sd[list(S3.columns)]).sum(axis=1)),
     "C1 5 sleeves equal risk": scale((S5 / sd).sum(axis=1)),
     "C2 5 sleeves Sharpe-weighted": scale((S5 * (sr.clip(lower=0) / sd)).sum(axis=1))}
cov = fit.cov().to_numpy(); cov = 0.5 * cov + 0.5 * np.diag(np.diag(cov)); w = np.linalg.solve(cov, np.ones(len(sd))); w = np.clip(w, 0, None); w = w / w.sum()
C["C3 5 sleeves minimum variance"] = scale((S5 * w).sum(axis=1))
out = {"sleeve 2020-24 Sharpe": sr.round(3).to_dict(), "sleeve corr": S5.corr().round(2).to_dict()}
for k, bk in C.items():
    out[k] = SB.evaluate(bk); print(k, out[k]["Sharpe 2020-24 (decisions)"], out[k]["EXPECTED LIVE (0.6 x 2020-26)"], out[k]["Sharpe 2020-22 / 2023-24 / 2025-26"], flush=True)
best = max(C, key=lambda k: out[k]["Sharpe 2020-24 (decisions)"]); out["chosen"] = best; bk = C[best]
v = SB.v86_daily().loc["2022":SB.END]; rho = float(pd.concat([v, bk], axis=1, sort=True).loc["2022":SB.END].corr().iloc[0, 1]); sb = out[best]["EXPECTED LIVE (0.6 x 2020-26)"]
mix = lambda q: (1.78 + q * sb) / np.sqrt(1 + q * q + 2 * q * rho); bw = float(max(np.arange(0, 2.01, 0.05), key=mix))
out["mix with v8.6"] = {"corr": round(rho, 3), "best weight": round(bw, 2), "best": round(mix(bw), 3)}
print(json.dumps({"chosen": best, "book": out[best], "mix": out["mix with v8.6"]}, indent=0))
json.dump(out, open(SB.ROOT / "results/gen366.json", "w"), indent=1)
S5.to_parquet(SB.ROOT / "results/gen366_sleeves.parquet"); bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen366_book.parquet")
