"""Gen455 (config/gen455_protocol.json): alt kimchi ensemble on the point-in-time top-30 coins that have an Upbit KRW market. Writes results/gen455.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import pit_universe as PU
import ridge_live as RL
import alt_kimchi as AK
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
days = pd.date_range("2020-01-01", END); fx = RL.usdkrw(); MORE = ROOT / "research_data/more"
def zscore(c):
    base = c.replace("1000", "") if c.startswith("1000") else c
    f = MORE / f"upbit_KRW-{base}_1h.parquet"
    if not f.exists():
        return None
    up = pd.read_parquet(f)["close"]; up.index = pd.DatetimeIndex(up.index).as_unit("ns")
    if c in PU.PACK:
        from qpl.lab import binance_pack as B
        bn = B.k5(c).close.resample("1h").last()
    else:
        fr = PU.frame(c)
        if fr is None:
            return None
        bn = fr["c"]
    bn.index = pd.DatetimeIndex(bn.index).as_unit("ns")
    if c.startswith("1000"):
        bn = bn / 1000.0
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END + " 23:00"]
    kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    return ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
def sleeve(coins, mem=None):
    Z = {}
    for c in coins:
        z = zscore(c)
        if z is not None:
            Z[c] = z if mem is None else z.where(mem[c].reindex(days).fillna(False)) if c in mem else None
    Z = pd.DataFrame({k: v for k, v in Z.items() if v is not None})
    W = sum(pd.DataFrame(np.where(Z > t, 0.1, np.where(Z < -t, -0.1, 0.0)), index=Z.index, columns=Z.columns) for t in (0.75, 1.0, 1.25)) / 3
    P = W.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)            # row d held during d + 1
    return PU.pnl_from_hourly_positions(P, idx, 5.0), Z.shape[1]
chk, n16 = sleeve(AK.coins())
mem = PU.members(30)
need = json.loads(Path("/tmp/claude-0/-home-user-Quant-prop-lab/dbf5c253-045e-5e00-8af6-a520de3cf126/scratchpad/upbit_need.json").read_text())["both"]
s, n = sleeve(need, mem)
b = unit(CS.portfolio_v5(V7.assign(**{"alt kimchi": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "replication on the 16 pack altcoins (daily corr with the v9.7 sleeve)": round(float(dd(chk).corr(dd(V7["alt kimchi"]))), 3),
       "replication sleeve": per(chk), "current sleeve": per(V7["alt kimchi"]), "coins used": n, "sleeve point-in-time top-30": per(s),
       "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)}, "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen455.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
