"""Historical record of the frozen F9_SLEEVE_RP spec (config/f9_spec.json). Descriptive: 1975-2013 clean, 2014+ CONTAMINATED."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import panel as PB
from qpl.data import futures_panel as FP
from qpl.research import factory as F, v6
from qpl.statistics import tests as T
from qpl.strategies import f9, futures_factors as FF
ROOT = Path(__file__).resolve().parents[1]
PER = v6.protocol("v6_futures_protocol.json")["periods"]
P = FP.build(); U, _ = FP.universe(P)
ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
W = f9.weights(ret, cost, cy)
d = f9.pnl(ret, cost, W)
bench = PB.run(ret, FF.long_rp(ret), cost)["net"]
out = {"periods": {}}
for k in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT"):
    m = v6.metrics(d.assign(n=0), bench, *PER[k], f9.pnl(ret, cost, W, cost_mult=2.0).assign(n=0))
    x = d["net"].loc[PER[k][0]:PER[k][1]].to_numpy()
    lo, hi, p0 = T.bootstrap_ci(x, T.sharpe, n_boot=1000, block=20)
    m["sharpe_ci95"] = [lo * np.sqrt(256 / 252), hi * np.sqrt(256 / 252)]
    m["net_sharpe_3x_cost"] = PB.stats(f9.pnl(ret, cost, W, cost_mult=3.0)["net"].loc[PER[k][0]:PER[k][1]])["sharpe"]
    m["clean"] = k in ("DISCOVERY", "VALIDATION")
    out["periods"][k] = m
# sensitivity (all periods; descriptive): sleeve mix and buffer
sens = {}
sig = PB.sigma(ret)
Ws = [PB.run(ret, s, cost, sig=sig, return_weights=True)[1] for s in f9.sleeve_signals(ret, cy).values()]
for mix in (0.3, 0.5, 0.7):
    Wm = mix * Ws[0] + (1 - mix) * Ws[1]
    for b in (0.0, 0.05, 0.2):
        dd = f9.pnl(ret, cost, f9.buffer_weights(Wm, b) if b else Wm)
        sens[f"trend{mix}_b{b}"] = {k: round(PB.stats(dd["net"].loc[PER[k][0]:PER[k][1]])["sharpe"], 2) for k in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT")}
out["sensitivity"] = sens
# drawdown episodes and worst months
eq = d["net"].cumsum(); ddown = eq - eq.cummax()
out["worst_drawdowns"] = []
x = ddown.copy()
for _ in range(5):
    tmin = x.idxmin(); depth = float(x.min())
    start = eq.loc[:tmin].idxmax(); rec = eq.loc[tmin:][eq.loc[tmin:] >= eq.loc[start]].index
    end = rec[0] if len(rec) else None
    out["worst_drawdowns"].append({"start": str(start.date()), "trough": str(tmin.date()), "recovered": str(end.date()) if end is not None else "not yet", "depth": depth})
    x.loc[start:(end or x.index[-1])] = 0
mo = d["net"].resample("ME").sum()
out["worst_months"] = {str(k.date()): round(float(v), 4) for k, v in mo.nsmallest(5).items()}
out["share_months_positive"] = float((mo > 0).mean())
out["by_year"] = {int(y): round(float(v), 4) for y, v in d["net"].groupby(d.index.year).sum().loc[1980:].items()}
out["exposure"] = {"mean_gross_notional_2014_2024": float(d["gross_lev"].loc["2014":].mean()), "mean_gross_notional_1990_2004": float(d["gross_lev"].loc["1990":"2004"].mean())}
d.to_parquet(ROOT / "results/v6_f9_pnl.parquet")
(ROOT / "results/v6_f9_record.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "hypothesis_id": "F9_SLEEVE_RP", "stage": "historical_record", "result_file": "results/v6_f9_record.json", "note": "2014+ contaminated"})
for k, m in out["periods"].items():
    print(k, {kk: (round(m[kk], 3) if isinstance(m[kk], float) else m[kk]) for kk in ("sharpe", "gross_sharpe", "ann_ret", "ann_vol", "max_dd", "cvar5", "skew", "residual_sharpe", "beta", "cost_ann", "turnover_ann", "net_sharpe_2x_cost", "net_sharpe_3x_cost", "sharpe_ci95")})
print(pd.DataFrame(sens).T)
print(out["worst_drawdowns"], out["worst_months"], out["share_months_positive"], out["exposure"])
