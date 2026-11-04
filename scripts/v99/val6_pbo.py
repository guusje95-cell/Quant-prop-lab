"""VAL-6 (research/v99/val6_protocol.json). Writes results/v99/val6_pbo.json."""
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
rng = np.random.default_rng(23)
dd = lambda h: h.groupby(h.index.floor("D")).sum()


def family(H, weiss_scale, n=600):
    cols = list(H.columns); orig = CS.v5_weights
    CS.v5_weights = lambda D, sleeves, weiss_scale_=0.5: orig(D, sleeves, weiss_scale=weiss_scale)
    try:
        fam = {"FULL": dd(CS.portfolio_v5(H)[0].loc["2022":"2026-09-30"])}
        seen = set()
        while len(fam) < n + 1:
            k = int(rng.integers(3, len(cols))); sub = tuple(sorted(rng.choice(cols, size=k, replace=False)))
            if sub in seen:
                continue
            seen.add(sub); fam[" + ".join(sub)] = dd(CS.portfolio_v5(H[list(sub)])[0].loc["2022":"2026-09-30"])
    finally:
        CS.v5_weights = orig
    return pd.DataFrame(fam).fillna(0.0)


def pbo(M: pd.DataFrame) -> dict:
    X = M.to_numpy(); T, nb = X.shape; S = 16; blocks = np.array_split(np.arange(T), S); combos = list(itertools.combinations(range(S), S // 2))
    pick = [combos[i] for i in rng.choice(len(combos), size=2000, replace=False)]
    srf = lambda A: A.mean(0) / A.std(0, ddof=1) * np.sqrt(365)
    lg, isb, oob, med, full_oos_rank = [], [], [], [], []
    for c in pick:
        tr = np.concatenate([blocks[i] for i in c]); te = np.concatenate([blocks[i] for i in range(S) if i not in c])
        a, b = srf(X[tr]), srf(X[te]); j = int(np.argmax(a)); rk = (b < b[j]).sum() + 0.5 * ((b == b[j]).sum() - 1); w = (rk + 1) / (nb + 1)
        lg.append(np.log(w / (1 - w))); isb.append(a[j]); oob.append(b[j]); med.append(np.median(b)); full_oos_rank.append(float((b < b[0]).mean()))
    full = srf(X)
    return {"books": nb, "PBO": round(float(np.mean(np.array(lg) <= 0)), 3), "IS winner: mean IS / OOS Sharpe": [round(float(np.mean(isb)), 2), round(float(np.mean(oob)), 2)],
            "OOS median of the family": round(float(np.mean(med)), 2), "full book: mean OOS percentile in the family": round(float(np.mean(full_oos_rank)), 3),
            "full book: full-sample Sharpe / rank": [round(float(full[0]), 3), int((full > full[0]).sum()) + 1]}


import r48_stress as R
Ev = R.per_event(); idx = R.idx; H9 = R.V8.copy()
for k, L in Ev.items():
    H9[R.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx))
out = {"v9.9 (13 sleeves, uncapped events)": pbo(family(H9, 0.5))}
import c1_cfd_port as C, c3_ensembles as E, cfd_book as CB
from qpl.live import cfd_extra as X
CB.measured_costs()
BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); bidx = BH.index
Rr = CB.hourly_returns(bidx[-1]).reindex(bidx).fillna(0.0); S2 = X.sleeves(pd.date_range("2021-01-01", bidx[-1], freq="h"))
b27 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(bidx).fillna(0.0) for k, v in S2.items()})
b28 = b27.assign(**{"trend 4h": E.trend(Rr, (15, 20, 30)), "alt kimchi": E.altk(Rr, (0.75, 1.0, 1.25))})
out["bf2.8 (12 sleeves, Weiss full)"] = pbo(family(b28, 1.0))
print(json.dumps(out, indent=1)); (ROOT / "results/v99/val6_pbo.json").write_text(json.dumps(out, indent=1))
