"""Gen38 (config/crypto_gen38_protocol.json): final candidate C* = E2 MAJ10 + O3 stable-liquidity overlay."""
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
from qpl.prop_simulation import cft_daily as CFT  # noqa: E402

PROTO = "config/crypto_gen38_protocol.json"
PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-08"),
       "FRESH": ("2026-05-24", "2026-10-08")}
D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":"2026-10-08"]; H, L = D["high"].reindex_like(MAJ), D["low"].reindex_like(MAJ)


def cmcap(a):
    return pd.read_csv(CM.SRC / f"{a}.csv", usecols=["time", "CapMrktCurUSD"], parse_dates=["time"]).set_index("time")["CapMrktCurUSD"]


stab = (cmcap("usdt").fillna(0) + cmcap("usdc").reindex(cmcap("usdt").index).fillna(0))
f3 = E.stable_overlay(stab, MAJ.index)


def strat(cols, overlay=True, cmult=1.0, fund=0.0, delay=0, drop=None):
    cols = [x for x in cols if x != drop]
    c, h, l = MAJ[cols], H[cols], L[cols]
    s = E.signals(c)
    if overlay:
        s = s.mul(f3, axis=0)
    w = weights(s, c, h, l)
    if delay:
        w = w.shift(delay).fillna(0)
    d = engine_daily(w, c, h, l, cmult)
    if fund:
        d["net"] = d["net"] - (w.shift(1).fillna(0) * fund * 3 / 1e4).sum(axis=1)
    d["gexp"] = w.shift(1).fillna(0).abs().sum(axis=1)
    return d.loc["2018-01-01":]


def full_stats(x, worst):
    x = x.dropna(); eq = (1 + x).cumprod()
    return {"net_sharpe": round(sh(x), 3), "cagr": round(float(eq.iloc[-1] ** (365 / len(x)) - 1), 4), "vol": round(float(x.std() * SQ), 4),
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "worst_day": round(float(worst.loc[x.index].min()), 4),
            "pf_days": round(float(x[x > 0].sum() / -x[x < 0].sum()), 3), "hit_days": round(float((x > 0).mean()), 3)}


ALL10 = list(MAJ.columns)
raw = strat(ALL10)
k15 = 0.15 / float(raw["net"].loc["2018":"2021"].std() * SQ)
C = raw * k15
out = {"scale_k_v015": k15, "Cstar_v015": {p: full_stats(C["net"].loc[a:z], C["worst"]) for p, (a, z) in PER.items()}}
out["Cstar_v015"]["ALL"] = full_stats(C["net"], C["worst"])
out["Cstar_v015"]["gross_sharpe_ALL"] = round(sh(C["gross"]), 3)
out["Cstar_v015"]["by_year_return"] = {int(y): round(float((1 + g).prod() - 1), 4) for y, g in C["net"].groupby(C["net"].index.year)}
out["Cstar_v015"]["by_year_sharpe"] = {int(y): round(sh(g), 2) for y, g in C["net"].groupby(C["net"].index.year)}
out["Cstar_v015"]["avg_gross_exposure"] = round(float((raw["gexp"] * k15).mean()), 3)
out["Cstar_v015"]["max_gross_exposure"] = round(float((raw["gexp"] * k15).max()), 3)
noov = strat(ALL10, overlay=False); kn = 0.15 / float(noov["net"].loc["2018":"2021"].std() * SQ); N0 = noov * kn
out["E2_MAJ10_noO3_v015"] = {p: full_stats(N0["net"].loc[a:z], N0["worst"]) for p, (a, z) in PER.items()}
out["E2_MAJ10_noO3_v015"]["ALL"] = full_stats(N0["net"], N0["worst"])
S = strat(ALL10, cmult=2.0, fund=1.0) * k15
out["stress_2x_cost_funding"] = {"ALL": full_stats(S["net"], S["worst"]), "TEST": full_stats(S["net"].loc["2024":], S["worst"])}
Dl = strat(ALL10, delay=1) * k15
out["delay_1d"] = {"ALL": full_stats(Dl["net"], Dl["worst"]), "TEST": full_stats(Dl["net"].loc["2024":], Dl["worst"])}
x = C["net"].to_numpy(); rng = np.random.default_rng(38)
bi = T.stationary_bootstrap_indices(len(x), 5000, 20.0, rng); bs = np.array([x[i].mean() / x[i].std() * SQ for i in bi])
out["bootstrap_sharpe_CI95"] = [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
out["DSR_N136"] = round(T.deflated_sharpe(x, 136), 4); out["NW_t"] = round(T.newey_west_t(x)[0], 2)
out["leave_one_coin_out_ALL_sharpe"] = {cn: round(sh(strat(ALL10, drop=cn)["net"]), 3) for cn in ALL10}
u = out["Cstar_v015"]
out["user_target"] = {"U1": u["ALL"]["net_sharpe"] >= 1.3, "U2": u["ALL"]["cagr"] >= 0.15,
                      "U3": u["TEST"]["net_sharpe"] >= 1.0 and u["TEST"]["cagr"] >= 0.10,
                      "U4": out["stress_2x_cost_funding"]["ALL"]["net_sharpe"] >= 1.0, "U5": out["DSR_N136"] >= 0.90}
out["TARGET_MET"] = all(out["user_target"].values())

# CFT two-speed pipeline: challenge C* (v 0.15), funded LIQUID2+O3 (v 0.06); unit scale on 2018-2022 as in gen34
def unit(d):
    return d[["net", "worst", "best"]] / float(d["net"].loc["2018":"2022"].std() * SQ)
uc_new, uf_new = unit(raw), unit(strat(["BTC", "ETH"]))
uc_old, uf_old = unit(noov), unit(strat(["BTC", "ETH"], overlay=False))
idx = uc_new.index
bidx = T.stationary_bootstrap_indices(len(idx), 1000, 20.0, np.random.default_rng(381))[:, :730]
pipe = {}
for tag, uc, uf in (("Cstar_two_speed", uc_new, uf_new), ("gen34_two_speed", uc_old, uf_old)):
    rc = tuple((uc * 0.15)[k].to_numpy() for k in ("net", "worst", "best")); rf = tuple((uf * 0.06)[k].to_numpy() for k in ("net", "worst", "best"))
    st = [i for i in range(0, len(idx), 5) if pd.Timestamp("2023-01-01") <= idx[i] <= pd.Timestamp("2024-10-08")]
    sa = [i for i in range(0, len(idx), 5) if idx[i] <= pd.Timestamp("2024-10-08")]
    pipe[tag] = {"TEST_starts": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, "1PHASE", 0.008) for s in st]),
                 "ALL_starts": CFT.summarize_pipeline([CFT.pipeline(*rc, *rf, s, "1PHASE", 0.008) for s in sa]),
                 "bootstrap": CFT.summarize_pipeline([CFT.pipeline(*(z[b] for z in rc), *(z[b] for z in rf), 0, "1PHASE", 0.008) for b in bidx])}
    st_ = [i for i in range(0, len(idx), 2) if pd.Timestamp("2023-01-01") <= idx[i] <= pd.Timestamp("2024-06-30")]
    pipe[tag]["challenge_attempt_TEST"] = CFT.summarize([CFT.simulate_start(rc[0], s, "1PHASE", mode="optimistic", max_days=548, lo=rc[1], hi=rc[2]) for s in st_])
out["CFT_pipeline_1PHASE"] = pipe
F.append({"kind": "holdout_evaluation", "hypothesis_id": "GEN38_CSTAR_E2_MAJ10_O3", "protocol": PROTO,
          "result": {"user_target": out["user_target"], "TARGET_MET": out["TARGET_MET"], "ALL": u["ALL"], "TEST": u["TEST"]}})
(ROOT / "results/crypto_gen38_final.json").write_text(json.dumps(out, indent=1, default=float))
C.to_pickle(ROOT / "results/crypto_gen38_Cstar_series.pkl")
print(json.dumps(out, indent=1, default=float))
