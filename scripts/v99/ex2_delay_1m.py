"""EX-2 (protocol research/v99/ex2_protocol.json): 1-minute delay curve of the whole book, per sleeve, and the fast-book / trend-timer
scenarios. Minute opens from the Binance USDT-M monthly archives (local cache data/lab/binance_1m_open, see the protocol).
Writes results/v99/ex2_delay_1m.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
run, delay_pnl = g0["run"], g0["delay_pnl"]
DELAYS = (1, 2, 3, 5, 10, 15)
SC = {"now (all 15 min)": {}, "now + Weiss timer": {"Weiss expiry": 1},
      "fast book 3 min": {"Weiss expiry": 1, "*": 3}, "fast book 2 min": {"Weiss expiry": 1, "*": 2},
      "trend timer": {"Weiss expiry": 1, "trend 4h": 1}}


def px1(coins):
    out = {}
    for c in coins:
        fs = sorted((ROOT / "data/lab/binance_1m_open").glob(f"{c}_*.parquet"))
        if fs:
            s = pd.concat([pd.read_parquet(f)["open"] for f in fs]); out[c] = s[~s.index.duplicated()].sort_index()
    return pd.DataFrame(out)


def evaluate(pos, scale, net, base, D, full):
    P = px1(list(net.columns)); res = {"coins without 1-minute data": [c for c in net.columns if c not in P.columns], "base (CN net, fill at hh:00)": full(base)}
    netd = {d: D(delay_pnl(net, P, d)) for d in DELAYS}
    cost = lambda x: round(float(-x.loc["2022":"2026-09-30"].mean() * 365 * 100), 3)
    res["net book by delay"] = {f"{d} min": {"sharpe": full(base + netd[d]), "cost % of book a year": cost(netd[d])} for d in DELAYS}
    sl = {(n, d): D(delay_pnl(p * scale(n), P, d)) for n, p in pos.items() for d in DELAYS}
    res["cost by sleeve and delay (% of book a year)"] = {n: {f"{d} min": cost(sl[(n, d)]) for d in DELAYS} for n in pos}
    s15 = sum(sl[(n, 15)] for n in pos)
    for name, spec in SC.items():
        x = sum(sl[(n, spec.get(n, spec.get("*", 15)))] for n in pos) - s15 + netd[15]
        res[name] = full(base + x)
    return res


out = {}
g1 = run("cn1_crypto_netting.py", "book = ph.loc")
D1 = lambda s: s.groupby(s.index.floor("D")).sum().reindex(pd.date_range("2022-01-01", "2026-09-30")).fillna(0.0)
sh = lambda s: float(s.mean() / s.std() * np.sqrt(365))
full1 = lambda dd: [round(sh(dd), 3), [round(sh(dd.loc[a:b]), 3) for a, b in (("2022", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))]]
pos1 = {n: p.reindex(columns=g1["coins"]).fillna(0.0) for n, p in g1["POS"].items()}
out["crypto v9.8 (8 non-event sleeves)"] = evaluate(pos1, lambda n: g1["Wh"][n].values[:, None] * g1["mh"].values[:, None], g1["net"],
                                                    D1(g1["ph"].loc["2022":"2026-09-30"]) + D1(g1["sep"] - g1["netc"]), D1, full1)
(ROOT / "results/v99/ex2_delay_1m.json").write_text(json.dumps(out, indent=1))
g2 = run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
C = g2["C"]; D2 = lambda s: C.dd(s).reindex(pd.date_range("2021-06-01", "2026-09-30")).fillna(0.0)
pos2 = {n: p.reindex(columns=g2["coins"]).fillna(0.0) for n, p in g2["POS"].items()}
out["CFD bf2.8 (crypto-CFD sleeves)"] = evaluate(pos2, lambda n: (g2["Wh"][n] * g2["mh"]).values[:, None], g2["net"].reindex(columns=g2["coins"]).fillna(0.0),
                                                 D2(g2["book"] + (g2["sep"] - g2["netc"])), D2, C.full)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/ex2_delay_1m.json").write_text(json.dumps(out, indent=1))
