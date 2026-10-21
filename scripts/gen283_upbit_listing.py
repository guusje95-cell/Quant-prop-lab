"""Gen283 (config/gen283_protocol.json): short after Upbit listing, 30 days (vs v8.1). Writes results/gen283.json."""
import json
import glob
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END; X = L.ROOT / "research_data/binance_extra"; PACK = set(B.coins())
legs = []; ev = []
for f in sorted(glob.glob(str(L.ROOT / "research_data/more/upbit_KRW-*_1h.parquet"))):
    c = f.split("KRW-")[1].replace("_1h.parquet", ""); t0 = pd.DatetimeIndex(pd.read_parquet(f).index).min()
    if t0 <= pd.Timestamp("2020-01-10") or t0 > pd.Timestamp(END):
        continue
    perp = c if c in PACK else ("1000" + c if (X / f"1000{c}USDT_1h.parquet").exists() else c)
    if perp in PACK:
        h = B.k5(perp).close.resample("1h").last().loc[:END + " 23:00"]; cost = 5e-4
        fu = B.funding(perp).copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(h.index).fillna(0.0)
    elif (X / f"{perp}USDT_1h.parquet").exists():
        h = pd.read_parquet(X / f"{perp}USDT_1h.parquet")["close"]; h.index = pd.DatetimeIndex(h.index); h = h[~h.index.duplicated()].loc[:END + " 23:00"]
        cost = 10e-4; fu = pd.Series(0.0, index=h.index)
    else:
        continue
    a = t0.floor("D") + pd.Timedelta(days=1); b = a + pd.Timedelta(days=30)
    pos = pd.Series(np.where((h.index >= a) & (h.index < b), -0.1, 0.0), index=h.index)
    r = h.pct_change(fill_method=None).fillna(0.0)
    legs.append(pos * r - pos * fu - pos.diff().abs().fillna(0.0) * cost); ev.append({"coin": c, "perp": perp, "short from": str(a.date()),
                                                                                   "30d coin return %": round(float((h.asof(b) / h.asof(a) - 1) * 100), 1) if a > h.index[0] else None})
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "events": ev}
L.judge("short after Upbit listing", pd.concat(legs, axis=1).fillna(0.0).sum(axis=1), out)
json.dump(out, open(L.ROOT / "results/gen283.json", "w"), indent=1)
