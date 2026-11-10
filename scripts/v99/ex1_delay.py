"""EX-1 (protocol research/v99/ex1_protocol.json): Sharpe cost of filling the hourly net trades d minutes after the hour instead of at
hh:00. Positions exactly as CN-1 (crypto v9.8, 8 non-event sleeves) and CN-2 (CFD bf2.8 crypto sleeves); their code is run unchanged up
to the net position. Writes results/v99/ex1_delay.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DELAYS = (5, 10, 15, 30)


def run(script, cut):
    src = (ROOT / "scripts/v99" / script).read_text().split(cut)[0]
    g = {"__file__": str(ROOT / "scripts/v99" / script), "__name__": "x"}; exec(src, g); return g


def px5(coins):
    out = {}
    for c in coins:
        f = ROOT / f"research_data/binance/{c}USDT_5m.parquet"
        if f.exists():
            s = pd.read_parquet(f, columns=["close"])["close"]; s.index = s.index + pd.Timedelta(minutes=5)   # stamp = bar END
            out[c] = s[~s.index.duplicated()]
    return pd.DataFrame(out)


def delay_pnl(pos: pd.DataFrame, P: pd.DataFrame, d: int) -> pd.Series:
    cs = [c for c in pos.columns if c in P.columns]
    dp = pos[cs].diff().fillna(pos[cs])
    p0 = P[cs].reindex(pos.index); p1 = P[cs].reindex(pos.index + pd.Timedelta(minutes=d)).set_axis(pos.index)
    r = (p1 / p0 - 1).fillna(0.0)
    return -(dp * r).sum(axis=1)


def evaluate(name, g, pos_by_sleeve, net, base_daily, D, full, per_sleeve_scale):
    coins = list(net.columns); P = px5(coins)
    turn = net.diff().abs().fillna(net.abs())
    cov = float(turn[[c for c in coins if c in P.columns]].sum().sum() / turn.sum().sum())
    res = {"turnover share with 5-minute data": round(cov, 3), "coins without 5-minute data": [c for c in coins if c not in P.columns],
           "base (CN net)": full(base_daily)}
    for d in DELAYS:
        x = D(delay_pnl(net, P, d)); res[f"delay {d} min"] = full(base_daily + x)
        res[f"delay {d} min: cost, % of book a year"] = round(float(-x.loc["2022":"2026-09-30"].mean() * 365 * 100), 3)
    x15 = {n: D(delay_pnl(p * per_sleeve_scale(n), P, 15)) for n, p in pos_by_sleeve.items()}
    res["15 min cost by sleeve (% of book a year, + = cost)"] = {n: round(float(-v.loc["2022":"2026-09-30"].mean() * 365 * 100), 3) for n, v in x15.items()}
    return res


out = {}
g1 = run("cn1_crypto_netting.py", "book = ph.loc")
IX1 = g1["IX"]; coins1 = g1["coins"]
D1 = lambda s: s.groupby(s.index.floor("D")).sum().reindex(pd.date_range("2022-01-01", "2026-09-30")).fillna(0.0)
sh = lambda s: float(s.mean() / s.std() * np.sqrt(365))
def full1(dd):
    return [round(sh(dd), 3), [round(sh(dd.loc[a:b]), 3) for a, b in (("2022", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))]]
base1 = D1(g1["ph"].loc["2022":"2026-09-30"]) + D1(g1["sep"] - g1["netc"])
pos1 = {n: p.reindex(columns=coins1).fillna(0.0) for n, p in g1["POS"].items()}
out["crypto v9.8 (8 non-event sleeves)"] = evaluate("crypto", g1, pos1, g1["net"], base1, D1, full1, lambda n: g1["Wh"][n].values[:, None] * g1["mh"].values[:, None])

g2 = run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
C = g2["C"]; coins2 = g2["coins"]
D2 = lambda s: C.dd(s).reindex(pd.date_range("2021-06-01", "2026-09-30")).fillna(0.0)
base2 = D2(g2["book"] + (g2["sep"] - g2["netc"]))
full2 = lambda dd: C.full(dd)
pos2 = {n: p.reindex(columns=coins2).fillna(0.0) for n, p in g2["POS"].items()}
out["CFD bf2.8 (crypto-CFD sleeves)"] = evaluate("cfd", g2, pos2, g2["net"].reindex(columns=coins2).fillna(0.0), base2, D2, full2,
                                                 lambda n: (g2["Wh"][n] * g2["mh"]).values[:, None])
print(json.dumps(out, indent=1)); (ROOT / "results/v99/ex1_delay.json").write_text(json.dumps(out, indent=1))
