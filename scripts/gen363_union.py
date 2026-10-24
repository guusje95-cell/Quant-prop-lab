"""Gen363 (config/gen363_protocol.json). Writes results/gen363.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
coins, idx, n = SB.coins, SB.idx, SB.n
S = pd.read_parquet(SB.ROOT / "results/gen362_sleeves.parquet")


def nf_union(cap=5):
    ev = set()
    for j, c in enumerate(coins):
        for src in (SB.FUND_RAW.get(c), SB.BYB_RAW.get(c)):
            if src is None:
                continue
            f = src.dropna()
            for ts in f.index[f < -0.001]:
                t = idx.get_indexer([ts.floor("h")])[0]
                if t >= 0:
                    ev.add((t, j))
    ev = sorted(ev); P = np.zeros((n, len(coins))); ends = []
    for t, j in ev:
        if P[t, j] > 0:
            continue
        ends = [e for e in ends if e > t]
        if len(ends) >= cap:
            continue
        P[t:min(t + 24, n), j] = 0.1; ends.append(t + 24)
    return SB.daily(SB.pnl(pd.DataFrame(P, index=idx, columns=coins), maker=True)), len(ev)


def book(Dd):
    bk = (Dd / Dd.loc[:"2024"].std()).sum(axis=1); return bk * 0.15 / (bk.loc[:"2024"].std() * np.sqrt(365))


u, ne = nf_union(); S2 = S.copy(); S2["negative funding"] = u.reindex(S.index).fillna(0.0)
b0, b1 = book(S.fillna(0.0)), book(S2.fillna(0.0))
out = {"union events": ne, "2020-24 Binance only / union": [round(SB.sh(b0, "2020", "2024"), 3), round(SB.sh(b1, "2020", "2024"), 3)]}
use = SB.sh(b1, "2020", "2024") > SB.sh(b0, "2020", "2024"); bk = b1 if use else b0; out["chosen"] = "union" if use else "Binance only"
out["BOOK"] = SB.evaluate(bk)
v = SB.v86_daily().loc["2022":SB.END]; rho = float(pd.concat([v, bk], axis=1).loc["2022":SB.END].corr().iloc[0, 1])
sv, sb = 1.78, out["BOOK"]["EXPECTED LIVE (0.6 x 2020-26)"]; mix = lambda w: (sv + w * sb) / np.sqrt(1 + w * w + 2 * w * rho)
ws = np.arange(0, 2.01, 0.05); best = float(max(ws, key=mix))
out["mix with v8.6 (planning)"] = {"corr": round(rho, 3), "v8.6 alone": sv, "equal risk": round(mix(1.0), 3), "best weight": round(best, 2), "best": round(mix(best), 3)}
print(json.dumps(out, indent=0)); json.dump(out, open(SB.ROOT / "results/gen363.json", "w"), indent=1)
(S2 if use else S).to_parquet(SB.ROOT / "results/gen363_sleeves.parquet"); bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen363_book.parquet")
