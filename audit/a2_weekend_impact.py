"""Audit A2 (impact test, no pipeline change): rebuild the panel with weekend (Sunday-evening Globex) prints removed
before the per-date grouping, re-run F7 and the F9 sleeves, and compare Sharpe by period with the production panel."""
import sys, json
import pandas as pd, numpy as np
sys.path.insert(0, "src")
from qpl.data import futures_panel as FP
from qpl.backtesting import panel as PB
from qpl.strategies import futures_factors as FF, f9
from qpl.research import v6
PER = v6.protocol("v6_futures_protocol.json")["periods"]

def f7(P, U):
    ret, cost, cy = P["ret"][U], P["cost"][U], P["carry"][U]
    s = ((FF.ct1_transfer(ret).fillna(0) + FF.tsmom(ret).fillna(0) + FF.ewmac(ret).fillna(0) + FF.carry(ret, cy, 21).fillna(0)) / 4).where(ret.notna().cumsum() > 0)
    d = PB.run(ret, s, cost)["net"]
    d9 = f9.pnl(ret, cost, f9.weights(ret, cost, cy))["net"]
    return {k: {"F7": round(PB.stats(d.loc[a:z])["sharpe"], 3), "F9": round(PB.stats(d9.loc[a:z])["sharpe"], 3)} for k, (a, z) in ((k, PER[k]) for k in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT"))}

P0 = FP.build(); U, _ = FP.universe(P0)
base = f7(P0, U)
orig = pd.read_csv
def read_no_weekend(path, *a, **k):
    df = orig(path, *a, **k)
    if "DATETIME" in df and ("adjusted_prices" in str(path) or "multiple_prices" in str(path)):
        df = df[pd.to_datetime(df["DATETIME"]).dt.dayofweek < 5]
    return df
FP.pd.read_csv = read_no_weekend
FP.PROC = FP.ROOT / "data/processed/futures_panel_noweekend"
P1 = FP.build(force=True)
FP.pd.read_csv = orig
alt = f7(P1, U)
print(json.dumps({"production": base, "weekend_prints_removed": alt}, indent=1))
r0, r1 = P0["ret"][U], P1["ret"][U]
print("weekend rows in variant:", int((P1["ret"].index.dayofweek >= 5).sum()))
