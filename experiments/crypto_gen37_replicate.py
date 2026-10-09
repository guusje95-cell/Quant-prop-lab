"""Gen37 (config/crypto_gen37_protocol.json): E2 on untouched U2 alts; O3 stable-liquidity overlay replication."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen32_improve.py").read_text().split("rng = np.random.default_rng(32)")[0]
G = {"__name__": "g32", "__file__": str(ROOT / "experiments/crypto_gen32_improve.py")}
exec(compile(src, "g32", "exec"), G)
E, SK, F, T = G["E"], G["SK"], G["F"], G["T"]
weights, engine_daily, sh, SQ = G["weights"], G["engine_daily"], G["sh"], G["SQ"]
from qpl.data import coinmetrics as CM  # noqa: E402

PROTO = "config/crypto_gen37_protocol.json"
PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-05-24")}
END = "2026-05-24"


def o3(index):
    def cmcap(a):
        d = pd.read_csv(CM.SRC / f"{a}.csv", usecols=["time", "CapMrktCurUSD"], parse_dates=["time"]).set_index("time")["CapMrktCurUSD"]
        return d.reindex(index).fillna(0)
    stab = cmcap("usdt") + cmcap("usdc")
    g = np.log(stab.replace(0, np.nan)).diff(30)
    return pd.Series(np.where(g > 0, 1.25, np.where(g <= 0, 0.75, 1.0)), index=index).shift(1).fillna(1.0)


# ---------------- U2 (close-only) engine
CMP = CM.load()
px = CMP["PriceUSD"].loc["2016-01-01":END].drop(columns=["avaxp", "avaxx"], errors="ignore")
cap = CMP["CapMrktCurUSD"].reindex_like(px)
hist = px.notna().cumsum() >= 200
rank = cap.where(hist & px.notna()).rank(axis=1, ascending=False)
member = (rank > 10) & (rank <= 30)
vol = np.log(px).diff().rolling(30, min_periods=20).std() * SQ
ret = px.pct_change(fill_method=None).fillna(0)
sigU = pd.DataFrame({a: E.signal_one(px[a]) for a in px.columns if px[a].notna().sum() > 250}).reindex_like(px).fillna(0)


def u2(sig, cmult=1.0):
    w = (sig * (0.40 / vol).clip(upper=1.0)).where(member, 0.0)
    w = w.div(member.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    wp = w.shift(1).fillna(0)
    cost = wp.diff().abs().sum(axis=1).fillna(0) * 15.0 * cmult / 1e4
    return pd.DataFrame({"net": (wp * ret).sum(axis=1) - cost}).loc["2018-01-01":END]


def pst(x):
    return {**{p: round(sh(x.loc[a:z]), 3) for p, (a, z) in PER.items()}, "ALL": round(sh(x), 3)}


out = {}
A1, A2 = u2(sigU), u2(sigU, 2.0)
eq = (1 + A1["net"]).cumprod()
out["A_E2_U2"] = {**pst(A1["net"]), "2x": round(sh(A2["net"]), 3), "cagr": round(float(eq.iloc[-1] ** (365 / len(eq)) - 1), 4),
                  "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "vol": round(float(A1["net"].std() * SQ), 4),
                  "by_year": {int(y): round(sh(g), 2) for y, g in A1["net"].groupby(A1["net"].index.year)}}
a = out["A_E2_U2"]
out["A_pass"] = bool(a["ALL"] >= 0.8 and all(a[p] >= 0.4 for p in PER) and a["2x"] >= 0.6)

# ---------------- O3 replication
fU = o3(px.index)
B_u2 = u2(sigU.mul(fU, axis=0))
D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":END]
alts = [k for k in MAJ.columns if k not in ("BTC", "ETH")]
c, h, l = MAJ[alts], D["high"].reindex_like(MAJ)[alts], D["low"].reindex_like(MAJ)[alts]
s8 = E.signals(c); f8 = o3(c.index)
A8 = engine_daily(weights(s8, c, h, l), c, h, l).loc["2018":END]
B8 = engine_daily(weights(s8.mul(f8, axis=0), c, h, l), c, h, l).loc["2018":END]
res = {}
diffs = []
for tag, base, mod in (("ALT8", A8["net"], B8["net"]), ("U2", A1["net"], B_u2["net"])):
    j = pd.concat([base, mod], axis=1).dropna(); b, m_ = j.iloc[:, 0], j.iloc[:, 1]
    m_ = m_ * (b.std() / m_.std())
    pb, pm = pst(b), pst(m_)
    res[tag] = {"base": pb, "with_O3": pm, "beats_each_period": bool(all(pm[p] > pb[p] for p in PER))}
    diffs.append(m_ - b)
dl = pd.concat(diffs, axis=1).mean(axis=1).dropna().to_numpy()
rng = np.random.default_rng(37); idx = T.stationary_bootstrap_indices(len(dl), 5000, 20.0, rng)
p = float(np.mean((dl - dl.mean())[idx].mean(axis=1) >= dl.mean()))
out["B_O3"] = {**res, "pooled_p": round(p, 4)}
out["B_pass"] = bool(res["ALT8"]["beats_each_period"] and res["U2"]["beats_each_period"] and p < 0.05)
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN37_REPLICATIONS", "protocol": PROTO,
          "result": {"A_pass": out["A_pass"], "B_pass": out["B_pass"], "A": {k: a[k] for k in ("ALL", "DEV", "VAL", "TEST", "2x")}, "B_p": p}})
(ROOT / "results/crypto_gen37_replicate.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
