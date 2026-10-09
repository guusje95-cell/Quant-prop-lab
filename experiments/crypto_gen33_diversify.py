"""Gen33 (config/crypto_gen33_protocol.json): BTC/ETH extra return streams (long/short E2, ETH/BTC relative trend)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen32_improve.py").read_text().split("rng = np.random.default_rng(32)")[0]
G = {"__name__": "g32", "__file__": str(ROOT / "experiments/crypto_gen32_improve.py")}
exec(compile(src, "g32", "exec"), G)
E, Z, SK, F, T = G["E"], G["Z"], G["SK"], G["F"], G["T"]
weights, engine_daily, period_stats, paired_p, sh, PER, SQ = (G[k] for k in ("weights", "engine_daily", "period_stats", "paired_p", "sh", "PER", "SQ"))
PROTO = "config/crypto_gen33_protocol.json"


def e2_ls(s):
    s = s.dropna()
    bo = sum(Z.short_breakout(s, n, k) for n, k in E.BO) / len(E.BO)
    tm = sum(Z.tsmom(s, n) for n in E.TM) / len(E.TM)
    return 0.5 * bo + 0.5 * tm


D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":"2026-10-08"]
c, h, l = (D[k].reindex_like(MAJ)[["BTC", "ETH"]] for k in ("close", "high", "low"))
B0 = engine_daily(weights(E.signals(c), c, h, l), c, h, l)
sig1 = pd.DataFrame({a: e2_ls(c[a]) for a in c.columns}).reindex_like(c).fillna(0)
C1 = engine_daily(weights(sig1, c, h, l), c, h, l)
ratio = (c["ETH"] / c["BTC"]).dropna()
sr = e2_ls(ratio).reindex(c.index).fillna(0)
rv = np.log(ratio).diff().rolling(30, min_periods=20).std().reindex(c.index) * SQ
x = (sr * (0.40 / rv).clip(upper=1.0) / 2).where(c.notna().all(axis=1).cumsum() >= 200, 0).fillna(0)
C2 = engine_daily(pd.DataFrame({"BTC": -x, "ETH": x}), c, h, l)


def scaled(d, ref, per=("2018-01-01", "2021-12-31")):
    k = ref["net"].loc[per[0]:per[1]].std() / d["net"].loc[per[0]:per[1]].std()
    return d * k


def combo(a, b):
    bs = scaled(b, a)
    d = pd.DataFrame({"net": a["net"] + bs["net"], "gross": a["gross"] + bs["gross"], "cost": a["cost"] + bs["cost"],
                      "worst": a["worst"] + bs["worst"], "best": a["best"] + bs["best"]})
    return d, float(bs["net"].std() / b["net"].std()) if b["net"].std() > 0 else 0.0


C3, k3 = combo(B0, C2)
C1s = scaled(C1, B0); C4, k4 = combo(C1s, C2)
rng = np.random.default_rng(33)
out = {"B0": period_stats(B0), "standalone": {}, "cands": {}}
for n, d in (("C1_E2_LS", C1), ("C2_ETHBTC_RELTREND", C2)):
    st = period_stats(d); j = pd.concat([d["net"], B0["net"]], axis=1).loc["2018":].dropna()
    st["corr_with_B0"] = round(float(j.corr().iloc[0, 1]), 3)
    st["worst_days"] = {str(k.date()): round(float(v), 4) for k, v in d["worst"].loc["2018":].nsmallest(4).items()}
    out["standalone"][n] = st
pv = {}
for n, d in (("C1_E2_LS", C1), ("C2_ETHBTC_RELTREND", C2), ("C3_B0_PLUS_C2", C3), ("C4_C1_PLUS_C2", C4)):
    k = B0["net"].loc["2018":].std() / d["net"].loc["2018":].std(); dd = d * k      # equal 2018-2026 vol
    st, bs = period_stats(dd), period_stats(B0)
    pv[n] = paired_p(dd, B0, rng)
    out["cands"][n] = {"stats": st, "beats_each_period": bool(all(st[p] > bs[p] for p in PER)),
                       "tail_ok": bool(st["tail_ratio"] <= bs["tail_ratio"] * 1.10), "p_raw": round(pv[n], 4)}
order = sorted(pv, key=pv.get); run = 0.0
for i, kk in enumerate(order):
    run = max(run, min(1.0, (len(order) - i) * pv[kk])); out["cands"][kk]["p_holm"] = round(run, 4)
for kk, m in out["cands"].items():
    m["ACCEPTED"] = bool(m["beats_each_period"] and m["tail_ok"] and m["p_holm"] < 0.05)
    F.append({"kind": "dev_evaluation", "hypothesis_id": f"GEN33_{kk}", "protocol": PROTO, "result": m})
out["C2_scale_in_C3"] = k3
(ROOT / "results/crypto_gen33_diversify.json").write_text(json.dumps(out, indent=1, default=float))
pd.to_pickle({"B0": B0, "C1": C1, "C2": C2, "C3": C3, "C4": C4}, ROOT / "results/crypto_gen33_series.pkl")
print(json.dumps(out, indent=1, default=float))
