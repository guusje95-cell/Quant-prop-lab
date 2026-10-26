"""Gen462 (config/gen462_protocol.json): long-short C* on the point-in-time top-10. Writes results/gen462.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
from qpl.lab import strategies as ST
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
orig_signal = ST.CStarTrend.signal
def make(mode):
    def sig(self, bars, p):
        q = dict(p); q["long_only"] = False; btc = q.pop("btc_leads", False); q["btc_leads"] = False
        s = orig_signal(self, bars, q)
        if mode == "B" and "BTC" in s.columns:
            alts = [c for c in s.columns if c != "BTC"]
            s[alts] = s[alts].where((s["BTC"] > 0).to_numpy()[:, None] | (s[alts] < 0), 0.0)
        return s
    return sig
chk_w = CS.cstar_pit_weights(); chk = CS.breadth_pnl(chk_w, list(chk_w.columns), 7.5).reindex(idx).fillna(0.0)
out = {"reference v9.7": [REF[0], REF[1]], "check long-only rebuild max |diff|": float((chk - V7["C*"]).abs().max()), "current C*": per(V7["C*"]), "trials": {}}
for k, mode in (("A C* long-short", "A"), ("B C* long-short, BTC leads the longs only", "B")):
    ST.CStarTrend.signal = make(mode)
    w = CS.cstar_pit_weights(); s = CS.breadth_pnl(w, list(w.columns), 7.5).reindex(idx).fillna(0.0)
    ST.CStarTrend.signal = orig_signal
    b = unit(CS.portfolio_v5(V7.assign(**{"C*": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book": r,
                        "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen462.json").write_text(json.dumps(out, indent=1)); print("check", out["check long-only rebuild max |diff|"])
