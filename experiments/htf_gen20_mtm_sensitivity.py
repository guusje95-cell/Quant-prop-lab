"""Sensitivity (no decisions changed): gen20 DEV Sharpe with daily mark-to-market instead of exit-day booking."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl import instruments as INS
from qpl.htf import core as H
DUKA = ["US500", "US100", "US30", "DE40", "XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "BRENT"]
out = {}
for strat in ("A1_SR1", "A3_SR3", "A2_BO"):
    for fam in ("PW", "PM"):
        series = []
        for s in DUKA:
            d = pd.read_parquet(f"data/processed/dukascopy/{s}_D1.parquet")[["open", "high", "low", "close"]]
            c = INS.SPOT_COST_PRICE_UNITS[s]; cf = lambda p, c=c: c
            ev = [e for e in H.detect_events(d, H.htf_frame(d, "fx"), fam) if e.strategy == strat]
            t = H.simulate(d, ev, cf, hold=5)
            m = H.daily_mtm(d, t, cf) if len(t) else pd.Series(0.0, index=d.index)
            m.index = m.index.tz_convert("UTC").normalize().tz_localize(None)
            series.append(m.groupby(level=0).sum())
        p = pd.concat(series, axis=1).fillna(0).sum(axis=1).loc["2008":"2016"]
        ann = len(p) / ((p.index[-1] - p.index[0]).days / 365.25)
        out[f"{strat}_{fam}"] = round(float(p.mean() / p.std() * np.sqrt(ann)), 3)
print(json.dumps(out, indent=1))
