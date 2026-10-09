"""V6 statistical integrity for the futures survivors: CSCV PBO over the whole gen13 grid, DSR with honest trial
counts, block-bootstrap CIs per period, Holm at TEST stage, and minimum track-record length (MinTRL) for the
prospective validation that is now required."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as ss

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB  # noqa: E402
from qpl.data import futures_panel as FP  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import futures_factors as FF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v3pbo", ROOT / "experiments/v3_pbo.py")
PER = v6.protocol("v6_futures_protocol.json")["periods"]
P = FP.build(); U, utab = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
classes = utab.loc[U, "asset_class"]
SIG = PB.sigma(ret)
grid = {
    "F0": FF.ct1_transfer(ret), **{f"F0_{g}": FF.ct1_transfer(ret, (g,)) for g in ("t20", "t60", "t120", "d20", "d55")},
    "F1": FF.tsmom(ret), **{f"F1_L{L}": FF.tsmom(ret, (L,)) for L in (21, 63, 126, 252)},
    "F2": FF.ewmac(ret), **{f"F2_{f}": FF.ewmac(ret, ((f, s),)) for f, s in ((8, 32), (16, 64), (32, 128), (64, 256))},
    "F3": FF.carry(ret, cy, 21), "F3_s1": FF.carry(ret, cy, 1), "F3_s63": FF.carry(ret, cy, 63),
    "F4": FF.xs_momentum(ret, classes, 252), "F4_126": FF.xs_momentum(ret, classes, 126),
    "F5": FF.xs_value(ret, classes, 1260, 252), "F5_756": FF.xs_value(ret, classes, 756, 252),
    "F6": FF.xs_skew(ret, classes, 252), "F6_126": FF.xs_skew(ret, classes, 126),
}
pnl = pd.DataFrame({k: PB.run(ret, s, cost, sig=SIG)["net"] for k, s in grid.items()})
sl = pd.read_parquet(ROOT / "results/v6_sleeves_pnl.parquet")
pnl["F7"] = pd.read_parquet(ROOT / "results/v6_futures_gen13_pnl.parquet")["F7_COMBO"]
pnl["B0_sleeve_rp"] = sl["B0"]
out = {"n_configs_gen13_grid": len(grid) + 1}

# CSCV PBO on DISCOVERY+VALIDATION (where selection happened), S=16
mod = importlib.util.module_from_spec(spec)
src = (ROOT / "experiments/v3_pbo.py").read_text().split("def daily_matrix")[0]
exec(compile(src, "v3_pbo_head", "exec"), mod.__dict__)
dev = pnl.loc["1985-01-01":PER["VALIDATION"][1], list(grid) + ["F7"]].fillna(0.0)
out["PBO_dev_1985_2013"] = mod.cscv_pbo(dev.to_numpy(), S=16)

# trials: gen13 grid (26) + gen14 buffer/leverage grid (2 x 4 + 3) + gen15 (5) -> honest futures trial count
n_trials = len(grid) + 1 + 11 + 5
sr_daily = dev.mean() / dev.std()
var_sr = float(sr_daily.var())
out["n_trials_futures"] = n_trials
out["var_sr_daily_across_grid"] = var_sr
for k in ("F7", "F2", "F3", "F1", "F0", "B0_sleeve_rp"):
    x = pnl[k]
    row = {}
    for per in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT"):
        xx = x.loc[PER[per][0]:PER[per][1]].dropna().to_numpy()
        lo, hi, p0 = T.bootstrap_ci(xx, T.sharpe, n_boot=1000, block=20)
        row[per] = {"sharpe": PB.stats(pd.Series(xx))["sharpe"], "ci95": [lo * np.sqrt(256 / 252), hi * np.sqrt(256 / 252)], "P(sharpe<=0)": p0,
                    "PSR0": T.probabilistic_sharpe(xx)}
    full = x.loc["1985-01-01":].dropna().to_numpy()
    row["DSR_1985_2024"] = T.deflated_sharpe(full, n_trials, var_sr)
    post = x.loc[PER["TEST"][0]:].dropna().to_numpy()
    row["DSR_post2014"] = T.deflated_sharpe(post, n_trials, var_sr)
    out[k] = row
# Holm across families at TEST stage (single looks)
pv = {k: T.newey_west_t(pnl[k].loc[PER["TEST"][0]:PER["TEST"][1]].dropna().to_numpy(), lags=10)[1] for k in ("F0", "F1", "F2", "F3", "F7")}
out["TEST_nw_p"] = pv
out["TEST_holm"] = v6.holm(pv)
pv2 = {k: T.newey_west_t(pnl[k].loc[PER["HOLDOUT"][0]:PER["HOLDOUT"][1]].dropna().to_numpy(), lags=10)[1] for k in ("F0", "F1", "F2", "F3", "F7")}
out["HOLDOUT_nw_p"] = pv2
out["HOLDOUT_holm"] = v6.holm(pv2)


# MinTRL (Bailey & Lopez de Prado 2012): years of daily data needed to reject SR<=0 at 95% given true SR, skew, kurt
def min_trl_years(sr_ann, skew=0.0, kurt=3.0, conf=0.95, ppy=256):
    sr = sr_ann / np.sqrt(ppy)
    z = ss.norm.ppf(conf)
    n = 1 + (1 - skew * sr + (kurt - 1) / 4 * sr ** 2) * (z / sr) ** 2
    return float(n / ppy)


x = pnl["F7"].loc[PER["TEST"][0]:].dropna()
out["MinTRL_years"] = {f"SR{s}": round(min_trl_years(s, float(x.skew()), float(x.kurt() + 3)), 1) for s in (0.3, 0.5, 0.7, 1.0)}
(ROOT / "results/v6_futures_stats.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "stage": "v6_futures_stats", "result_file": "results/v6_futures_stats.json",
          "summary": {"PBO": out["PBO_dev_1985_2013"]["pbo"], "n_trials": n_trials, "MinTRL": out["MinTRL_years"]}})
print(json.dumps({k: out[k] for k in ("PBO_dev_1985_2013", "n_trials_futures", "TEST_holm", "HOLDOUT_holm", "HOLDOUT_nw_p", "MinTRL_years")}, indent=1))
for k in ("F7", "F2", "F3", "B0_sleeve_rp"):
    print(k, {p: (round(v["sharpe"], 2), [round(c, 2) for c in v["ci95"]]) for p, v in out[k].items() if isinstance(v, dict)},
          "DSR", round(out[k]["DSR_1985_2024"], 3), round(out[k]["DSR_post2014"], 3))
