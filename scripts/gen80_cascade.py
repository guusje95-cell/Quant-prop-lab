"""Gen80 cascade part (config/gen80_protocol.json): strict-limit cascade on 20 pack + 40 extra coins, frozen rule; registered
variant max 5 open. Hourly bars for the extra coins from research_data/binance_extra (close/low/high, quote volume, open-interest
value) - the same fields the pack version builds from 5-minute data. Writes results/gen80_cascade.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, B, H6, B0, k0, per, sh = (g[k] for k in ("CS", "B", "H6", "B0", "k0", "per", "sh"))
import gen57_cascade_hourly as CH
EX = ROOT / "research_data/binance_extra"
XS = sorted(p.stem.replace("USDT_1h", "") for p in EX.glob("*USDT_1h.parquet"))
for c in XS:
    k = pd.read_parquet(EX / f"{c}USDT_1h.parquet")
    k.index = pd.DatetimeIndex(k.index)
    oi = pd.read_parquet(EX / f"{c}USDT_oi_1h.parquet")["oi_value"].astype(float); oi.index = pd.DatetimeIndex(oi.index)
    CH.CACHE[c] = pd.DataFrame({"c": k.close.astype(float), "lo": k.low.astype(float), "hi": k.high.astype(float),
                                "v": k.quote_volume.astype(float), "oi": oi.reindex(k.index)})
H5 = H6.drop(columns=["delev bounce"]); rows = []
base = CS.cascade(limit=0.005, through=0.001)
for name, kw in (("cascade 20 coins (current)", {}), ("cascade 20 + extra, max 3 open", {"coins": B.coins() + XS}),
                 ("cascade 20 + extra, max 5 open", {"coins": B.coins() + XS, "max_open": 5})):
    s = base if not kw else CS.cascade(limit=0.005, through=0.001, **kw)
    r = {"test": name, "DEV/TEST/HOLD": np.round(per(s, "2020-01-01"), 3).tolist(), "2023-26": round(sh(s, "2023-01-01", "2026-09-30"), 3)}
    for bk, H in (("v5", H5), ("v6", H6)):
        H1 = H.copy(); H1["cascade limit strict"] = s.reindex(H.index).fillna(0.0); b = CS.portfolio_v5(H1)[0]
        r[f"{bk} 2022-26"] = round(sh(b, "2022-01-01", "2026-09-30"), 3); r[f"{bk} D/T/H"] = np.round(per(b, "2022-01-01"), 3).tolist()
    rows.append(r); print(r, flush=True)
ref = rows[0]
for r in rows[1:]:
    r["pass Gen80 rule"] = bool(r["2023-26"] >= ref["2023-26"] and r["DEV/TEST/HOLD"][2] >= ref["DEV/TEST/HOLD"][2] and r["v5 2022-26"] > ref["v5 2022-26"])
    r["pass strict book rule (v6)"] = bool(r["v6 2022-26"] > ref["v6 2022-26"] and r["v6 D/T/H"][1] >= ref["v6 D/T/H"][1] and r["v6 D/T/H"][2] >= ref["v6 D/T/H"][2])
    print(r["test"], r["pass Gen80 rule"], r["pass strict book rule (v6)"])
pd.DataFrame(rows).to_csv(ROOT / "results/gen80_cascade.csv", index=False)
