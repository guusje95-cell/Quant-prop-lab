"""Gen47: pre-registered test of two intraday momentum papers (config/gen47_intraday_momentum_protocol.json)."""
import json, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, analysis as A
from qpl.lab.strategies_papers import IntradayMomentumGao, NoiseAreaMomentum

src = D.list_sources(); rows = []
for tf, costs in (("15-min", (1.0, 0.3, 2.0)), ("5-min, 2020-23", (1.0,))):
    for sym in ("US500", "US100"):
        b = src[f"{sym} CFD, Dukascopy ({tf})"]()
        for cls in (IntradayMomentumGao, NoiseAreaMomentum):
            st = cls(); sig = st.signal(b, st.defaults())
            for cost in costs:
                cfg = EN.Config(cost_bps=cost); r = EN.run(b, EN.size(b, sig, cfg, "raw"), cfg)
                d = EN.to_daily(r["bars"], b.freq)["net"]; d = d[d.index >= d.index[0] + pd.Timedelta(days=21)]
                d = d[d.index.dayofweek < 5]
                S = A.summary(d, 252); a, z = A.split_stats(d, 252, pd.Timestamp("2018-09-01"))
                rows.append({"strategy": cls.__name__, "asset": sym, "bars": tf, "cost_bp": cost, "sharpe": round(S["Sharpe"], 2),
                             "cagr": round(S["CAGR"], 4), "vol": round(S["Volatility"], 3), "max_dd": round(S["Max drawdown"], 3),
                             "pos_months": round(S["Positive months"], 2), "sharpe_first_half": round(a.get("Sharpe", float("nan")), 2) if a else None,
                             "sharpe_second_half": round(z.get("Sharpe", float("nan")), 2) if z else None,
                             "dsr_16": round(A.dsr(d, 252, 16), 3), "years": round(S["Years"], 1),
                             "trades": int(len(EN.trades(r["held"], b.close)))})
                print(rows[-1], flush=True)
out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen47_intraday_momentum.csv", index=False)
print(out.to_string())
