"""v3 generation 9: FX / gold session-transition hypotheses (TRAIN + VALIDATION only)."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F
from qpl.strategies import v3_intraday  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
NAN = float("nan")
MK = {"6E": "EURUSD", "6B": "GBPUSD", "MGC": "XAUUSD"}
H11 = F.Hypothesis("V11_ASIAN_BREAKOUT", "session transition/breakout",
                   "A breakout of the Asian-session range at the London open (03:00 ET) continues into the London/NY morning.",
                   "Liquidity and information arrive with European participants; Asian ranges reflect low-liquidity price discovery.",
                   "TRAIN net Sharpe < 0.5 in all markets/variants.", "M15 FX/gold, 19:00-03:00 ET range",
                   "stop {opposite side, 0.5 range} x exit {08:00, 11:00}", "zero", "config/promotion_criteria.json")
H12 = F.Hypothesis("V12_ASIAN_REVERSION", "mean reversion/session",
                   "During the quiet Asian session, deviations of EUR/GBP/gold from the 19:00 ET price revert by 02:00 ET.",
                   "Thin, range-bound liquidity provision outside major sessions.", "TRAIN net Sharpe < 0.5.",
                   "M15 FX/gold", "k {1.0,1.5} (in 0.25 ATR units)", "zero", "config/promotion_criteria.json")
rows = []
for hyp, strat, grid in ((H11, "asian_breakout", [dict(stop_frac=s, exit_min=x) for s, x in itertools.product([NAN, 0.5], [480, 660])]),
                         (H12, "asian_reversion", [dict(k=k) for k in (1.0, 1.5)])):
    hyp.register()
    for fut, proxy in MK.items():
        for prm in grid:
            r = F.evaluate_variant(hyp, strat, fut, proxy, prm, session=(180, 660), stage="gen9_screen")
            tr, va = r["periods"]["train"], r["periods"]["validation"]
            rows.append(dict(hid=hyp.id, mkt=fut, prm=json.dumps(prm), tr_sh=tr["net"]["sharpe"], tr_gross=tr["gross_sharpe"],
                             tr_n=tr["net"].get("trades", 0), va_sh=va["net"]["sharpe"], va_gross=va["gross_sharpe"]))
df = pd.DataFrame(rows); df.to_csv(ROOT / "results" / "v3_gen9_fx.csv", index=False)
for hyp in (H11, H12):
    x = df[df.hid == hyp.id]
    F.decide(hyp, "REJECT" if x.tr_sh.max() < 0.5 else "EXPLORATORY",
             f"best TRAIN net {x.tr_sh.max():.2f}, median {x.tr_sh.median():.2f}; best gross {x.tr_gross.max():.2f}; validation median {x.va_sh.median():.2f}")
pd.set_option("display.width", 200)
print(df.round(2).to_string())
