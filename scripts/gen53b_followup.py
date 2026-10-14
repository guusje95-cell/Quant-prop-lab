"""Gen53 follow-up: H2 tranching rerun (offset fix) and the prop check of H5 (BTC leads) on the hourly replay."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
import gen52_extra_check as X
from qpl.lab import propfirms as PF, strategies as S
cs = S.CStarTrend(); base_sig = cs.signal(G.CR, cs.defaults())
s5 = base_sig.copy(); alts = [c for c in s5.columns if c != "BTC"]; s5[alts] = s5[alts].where(base_sig["BTC"] > 0, 0.0, axis=0)
rows = []
for tag, sg in (("C* base", base_sig), ("H5 BTC leads", s5)):
    w, d = G.backtest(sg, 30, 0.0)
    for fn, f0 in G.FIRMS.items():
        t = G.prop_eval(d.loc[G.TEST[0]:G.TEST[1]], f0, 1.0, 0.4)
        hc = X.hourly(w, 1.0, 0, 0, f0.daily_loss); hf = X.hourly(w, 0.4, 0, 0, f0.daily_loss)
        a = PF.attempts(hc, f0, 1.0); p = PF.pipeline(hc, f0, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
        r = {"strategy": tag, "firm": fn, "TEST_pass": t["pass"], "TEST_net": t["net"], "TEST_p_profit": t["p_profit"],
             "HOURLY_pass": a["P_pass"], "HOURLY_net": p["net_mean"], "HOURLY_p50": p["net_p50"], "HOURLY_p_profit": p["P_profit"]}
        rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen53_h5_prop.csv", index=False)
