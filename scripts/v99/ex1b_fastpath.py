"""EX-1b (protocol research/v99/ex1b_protocol.json): per-sleeve fill delays (fast path for the clock-timed sleeves).
Writes results/v99/ex1b_fastpath.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
run, px5, delay_pnl = g0["run"], g0["px5"], g0["delay_pnl"]
SC = {"now": {}, "fast path": {"Weiss expiry": 5, "trend 4h": 5, "trend 4h ens CFD": 5},
      "fast path + ridge": {"Weiss expiry": 5, "trend 4h": 5, "trend 4h ens CFD": 5, "ridge ML": 5}, "all 5 min": "all5"}


def scen(pos, scale, P, D, base, full, net, net15):
    out = {}
    cache = {}
    for n, p in pos.items():
        for d in (5, 15):
            cache[(n, d)] = D(delay_pnl(p * scale(n), P, d))
    s15 = sum(cache[(n, 15)] for n in pos)
    out["netting check: per-sleeve sum at 15 min vs net, cost % a year"] = [round(float(-s15.loc["2022":"2026-09-30"].mean() * 365 * 100), 3),
                                                                             round(float(-net15.loc["2022":"2026-09-30"].mean() * 365 * 100), 3)]
    for name, spec in SC.items():
        x = sum(cache[(n, 5 if (spec == "all5" or (isinstance(spec, dict) and n in spec)) else 15)] for n in pos)
        x = x - s15 + net15                                   # apply the scenario as a change to the NET 15-minute result
        out[name] = full(base + x)
    return out


res = {}
g1 = run("cn1_crypto_netting.py", "book = ph.loc")
D1 = lambda s: s.groupby(s.index.floor("D")).sum().reindex(pd.date_range("2022-01-01", "2026-09-30")).fillna(0.0)
sh = lambda s: float(s.mean() / s.std() * np.sqrt(365))
full1 = lambda dd: [round(sh(dd), 3), [round(sh(dd.loc[a:b]), 3) for a, b in (("2022", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))]]
base1 = D1(g1["ph"].loc["2022":"2026-09-30"]) + D1(g1["sep"] - g1["netc"]); P1 = px5(g1["coins"])
pos1 = {n: p.reindex(columns=g1["coins"]).fillna(0.0) for n, p in g1["POS"].items()}
res["crypto v9.8 (8 non-event sleeves)"] = scen(pos1, lambda n: g1["Wh"][n].values[:, None] * g1["mh"].values[:, None], P1, D1, base1, full1,
                                                g1["net"], D1(delay_pnl(g1["net"], P1, 15)))
g2 = run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
C = g2["C"]; D2 = lambda s: C.dd(s).reindex(pd.date_range("2021-06-01", "2026-09-30")).fillna(0.0)
net2 = g2["net"].reindex(columns=g2["coins"]).fillna(0.0); P2 = px5(g2["coins"])
pos2 = {n: p.reindex(columns=g2["coins"]).fillna(0.0) for n, p in g2["POS"].items()}
res["CFD bf2.8 (crypto-CFD sleeves)"] = scen(pos2, lambda n: (g2["Wh"][n] * g2["mh"]).values[:, None], P2, D2, D2(g2["book"] + (g2["sep"] - g2["netc"])),
                                             C.full, net2, D2(delay_pnl(net2, P2, 15)))
print(json.dumps(res, indent=1)); (ROOT / "results/v99/ex1b_fastpath.json").write_text(json.dumps(res, indent=1))
