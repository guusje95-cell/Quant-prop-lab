"""F-CX4 (research/v99/fcx4_protocol.json). Writes results/v99/fcx4.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import crypto_sleeves as CS
import futures_db as F
from qpl.lab import binance_pack as B
from qpl.live.futures_cx import book, daily

per = lambda b: [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
P = pd.read_parquet(ROOT / "results/book_sleeves_current.parquet"); cx = pd.read_parquet(ROOT / "results/v99/cx_sleeve_prefix.parquet")["CX"]
P["CX"] = cx.reindex(P.index).fillna(0.0)
px = B.panel("close", "1h", ["SOL", "XRP"]).loc[:"2026-09-30 23:00"]
w = CS.cstar_weights()[["SOL", "XRP"]]
w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
pos = w.reindex(px.index.floor("D")).set_axis(px.index).fillna(0.0)
fund = CS._funding_hourly(["SOL", "XRP"], px.index)


def legs(mult):
    out = 0.0
    for c, bp in (("SOL", 6.0), ("XRP", 2.5)):
        p = pos[c]; r = px[c].pct_change(fill_method=None).fillna(0.0)
        out = out + p * r - p * fund[c] - p.diff().abs().fillna(p.abs()) * bp * mult / 1e4
    return daily(out)


out = {"reference (with CX)": per(book(P)[0])}
for name, m in (("CX4 registered", 1.0), ("CX4 at 2x SOL / XRP costs", 2.0)):
    P2 = P.copy(); P2["CX"] = (cx.reindex(P.index).fillna(0.0) + legs(m).reindex(P.index).fillna(0.0))
    out[name] = per(book(P2)[0]); out[name + " sleeve"] = per(P2["CX"])
sl = legs(1.0); out["SOL+XRP legs alone by year"] = {str(y): round(float(sl[sl.index.year == y].mean() / sl[sl.index.year == y].std() * np.sqrt(365)), 2) for y in range(2020, 2027)}
out["corr legs vs CX (daily, 2021+)"] = round(float(pd.concat([sl, cx], axis=1).loc["2021":].dropna().corr().iloc[0, 1]), 3)
out["pass"] = bool(out["CX4 registered"][2] >= 1.464 and out["CX4 registered"][1] >= 1.600 and out["CX4 at 2x SOL / XRP costs"][2] >= 1.464)
print(json.dumps(out, indent=1)); (ROOT / "results/v99/fcx4.json").write_text(json.dumps(out, indent=1))
