"""Gen242 (config/gen242_protocol.json): QQQ closing-cross imbalance -> NQ 15:51-16:00. Needs research_data/databento_extra/qqq_imbalance.parquet.
Writes results/gen242.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
f = ROOT / "research_data/databento_extra/qqq_imbalance.parquet"
if not f.exists():
    sys.exit("qqq_imbalance not downloaded yet (get_databento_buy_cheap.bat)")
import futures_db as F
w = {"__file__": str(ROOT / "scripts/gen148_r1_windows.py")}; exec(open(ROOT / "scripts/gen148_r1_windows.py").read().split("\ndef snaps(")[0], w)
load, I = w["load"], w["I"]
m = pd.read_parquet(f)
tcol = "ts_recv" if "ts_recv" in m else "ts_event"
m["t"] = pd.to_datetime(m[tcol], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
if "auction_type" in m:
    at = m.auction_type.astype(str)
    m = m[at.isin(["C", "c"]) | (at == "67")]                  # closing cross
m = m[(m.t.dt.strftime("%H:%M") >= "15:50") & (m.t.dt.strftime("%H:%M") < "16:00")].sort_values("t")
m["day"] = m.t.dt.normalize(); first = m.groupby("day").first()
side = first.side.astype(str).str.upper().map({"B": 1.0, "A": -1.0, "S": -1.0}).fillna(0.0)
px = pd.to_numeric(first.get("ref_price"), errors="coerce")
px = px.where(px < 1e5, px / 1e9)                                # fixed-point prices (1e-9) if not converted
qty = pd.to_numeric(first.get("total_imbalance_qty"), errors="coerce")
dollar = (qty * px).abs()
info = {"days with a closing imbalance": int(len(first)), "first day": str(first.index.min().date()), "last day": str(first.index.max().date()),
        "share buy side": round(float((side > 0).mean()), 2)}
B = load("NQ"); B = B[B.index.weekday < 5]; t = B.index.strftime("%H:%M"); day = B.index.normalize()
a = B[t == "15:51"].groupby(day[t == "15:51"]).agg(a=("open", "first"), ai=("instrument_id", "first"))
z = B[t < "16:00"].groupby(day[t < "16:00"]).agg(z=("close", "last"), zi=("instrument_id", "last"))
x = a.join(z, how="inner"); x = x[x.ai == x.zi]; x["r"] = x.z / x.a - 1; x["cost"] = 2 * F.cost_frac("NQ", x.a)
x["side"] = side.reindex(x.index).fillna(0.0); x["dollar"] = dollar.reindex(x.index)
x["med"] = x.dollar.rolling(20, min_periods=10).median().shift(1)
SPL, sh = I["SPL"], I["sharpe"]; res = {}
for name, thr in (("median", True), ("all", False)):
    s = x.side.where(x.dollar > x.med, 0.0) if thr else x.side
    p = (0.5 * (s * x.r - s.abs() * x.cost)).fillna(0.0)
    p = p.loc["2018-06-01":]
    res[name] = {"2018-20 / 21-23 / 24-26": [round(sh(p, a_, b_), 3) for a_, b_ in SPL], "sel": round(sh(p, "2018-06-01", "2023-12-31"), 3),
                 "gross 2018-26": round(sh((0.5 * s * x.r).fillna(0.0).loc["2018-06-01":], "2018-06-01", "2026-09-30"), 3), "days traded": int((s != 0).sum())}
    print(name, res[name], flush=True)
ch = max(res, key=lambda k: res[k]["sel"]); v = res[ch]["2018-20 / 21-23 / 24-26"]
out = {"data": info, "variants": res, "chosen": ch, "pass": bool(v[0] > 0 and v[1] >= 0.3 and v[2] >= 0.3)}
print(json.dumps(out)); json.dump(out, open(ROOT / "results/gen242.json", "w"), indent=1)
