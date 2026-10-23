"""Gen335 / Gen336 (config/gen335_protocol.json): parameter-plateau luck audit and neighbourhood ensembles in v8.6.
Writes results/gen335.json and results/gen336.json."""
import itertools
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import alt_kimchi as AK
END = L.END; B = L.B
H6, RIDGE, ALTK = L.H6, L.RIDGE, L.ALTK
base_cols = pd.concat([H6, RIDGE] + ALTK, axis=1).fillna(0.0)
assert abs(L.sh(CS.portfolio_v5(base_cols)[0], "2022-01-01", END) - L.REF[0]) < 1e-9


def book_with(name, s):
    H = base_cols.copy(); H[name] = s.reindex(H.index).fillna(0.0)
    b = CS.portfolio_v5(H)[0]
    return [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()


def ssh(s):
    d = s.loc["2022-01-01":END + " 23:00"]; d = d.groupby(d.index.floor("D")).sum(); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)


pc20 = lambda lk, hd: CS._from_daily_weights(CS.premium_weights(lk, hd, invvol=True, tranched=True), B.coins(), 5).loc[:END + " 23:00"]
pc60 = lambda lk, hd: CS.premium_carry_breadth(w=CS.premium_breadth_weights(look=lk, hold=hd, invvol=True, tranched=True)).loc[:END + " 23:00"]
t4 = lambda n: CS.trend4h(n_in=n, n_out=max(2, n // 2)).loc[:END + " 23:00"]
cas = lambda k, hd: CS.cascade(hold=hd, k=k, limit=0.005, through=0.001).loc[:END + " 23:00"]
dlv = lambda th, hd: CS._from_daily_weights(CS.delev_bounce_weights(th=th, hold=hd), ["BTC", "ETH"], 5).loc[:END + " 23:00"]
akz = lambda th: L.perp(AK.weights(END + " 23:00", th=th))
GRIDS = {"premium carry": (pc20, list(itertools.product((3, 5, 7, 10, 14), (3, 5, 7, 10, 14))), (7, 7)),
         "premium carry 60": (pc60, list(itertools.product((3, 5, 7, 10, 14), (3, 5, 7, 10, 14))), (7, 7)),
         "trend 4h": (t4, [(n,) for n in (10, 15, 20, 30, 40)], (20,)),
         "cascade limit strict": (cas, list(itertools.product((2.5, 3.0, 3.5), (6, 12, 24))), (3.0, 12)),
         "delev bounce": (dlv, list(itertools.product((0.07, 0.10, 0.13), (1, 2, 3))), (0.10, 2)),
         "alt kimchi": (akz, [(t,) for t in (0.75, 1.0, 1.25)], (1.0,))}
NEIGH = {"premium carry": list(itertools.product((5, 7, 10), (5, 7, 10))), "premium carry 60": list(itertools.product((5, 7, 10), (5, 7, 10))),
         "trend 4h": [(15,), (20,), (30,)], "cascade limit strict": list(itertools.product((2.5, 3.0, 3.5), (6, 12, 24))),
         "delev bounce": list(itertools.product((0.07, 0.10, 0.13), (1, 2, 3))), "alt kimchi": [(0.75,), (1.0,), (1.25,)]}
out5, cache = {"reference v8.6": [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist()}, {}
for nm, (fn, grid, chosen) in GRIDS.items():
    rows = []
    for g in grid:
        s = fn(*g); cache[(nm, g)] = s
        rows.append({"params": list(g), "sleeve 2022-26": ssh(s), "v8.6 D/T/H": book_with(nm, s)})
        print(nm, rows[-1], flush=True)
    bk = np.array([x["v8.6 D/T/H"][0] for x in rows]); sl = np.array([x["sleeve 2022-26"] for x in rows])
    ci = grid.index(chosen)
    out5[nm] = {"grid": rows, "chosen": list(chosen), "chosen v8.6": float(bk[ci]),
                "percentile of chosen in grid (v8.6 Sharpe)": round(float((bk < bk[ci]).mean()), 2),
                "grid median v8.6 / chosen - reference": round(float(np.median(bk) - bk[ci]), 3),
                "worst grid point v8.6": float(bk.min()), "share of grid points with v8.6 >= 3.0": round(float((bk >= 3.0).mean()), 2),
                "sleeve: chosen / grid median": [float(sl[ci]), float(np.median(sl))]}
    print(nm, {k: v for k, v in out5[nm].items() if k != "grid"}, flush=True)
json.dump(out5, open(L.ROOT / "results/gen335.json", "w"), indent=1)

out6 = {"reference v8.6": out5["reference v8.6"]}; ens = {}


def judge(label, H):
    b = CS.portfolio_v5(H)[0]; k = [round(L.sh(b, "2022-01-01", END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist()
    ref = out6["reference v8.6"]
    strict = all(a >= c for a, c in zip(k[1:], ref[1:])) and k[0] >= ref[0] + 0.05
    robust = all(a >= c - 0.03 for a, c in zip(k, ref))
    out6[label] = {"v8.6 D/T/H": k, "strict pass": bool(strict), "robustness swap (every period within -0.03)": bool(robust)}
    print(label, out6[label], flush=True)


for nm, nb in NEIGH.items():
    s = sum(cache[(nm, g)] if (nm, g) in cache else GRIDS[nm][0](*g) for g in nb) / len(nb); ens[nm] = s
    H = base_cols.copy(); H[nm] = s.reindex(H.index).fillna(0.0); judge(f"ensemble {nm}", H)
H = base_cols.copy()
for nm, s in ens.items():
    H[nm] = s.reindex(H.index).fillna(0.0)
judge("all six ensembles", H)
json.dump(out6, open(L.ROOT / "results/gen336.json", "w"), indent=1)
