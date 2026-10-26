"""Gen421 (config/gen421_protocol.json): COIN-M positioning members for the diversifier basket. Writes results/gen421.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import basket_live as BL
from qpl.lab import binance_pack as B
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95))
CM = {c: pd.read_parquet(ROOT / f"research_data/binance_cm/{c}USD_PERP_metrics.parquet") for c in ("BTC", "ETH")}
def coinm_lev():
    return pd.DataFrame({c: -0.125 * BL.z(np.log(BL.daily(CM[c]["sum_open_interest"].where(lambda s: s > 0), "mean")).diff(7), 90).clip(-2, 2) / 2 for c in ("BTC", "ETH")})
def taker_div():
    out = {}
    for c in ("BTC", "ETH"):
        cm = np.log(CM[c]["sum_taker_long_short_vol_ratio"].where(lambda s: s > 0)); um = np.log(B.metrics(c)["sum_taker_long_short_vol_ratio"].where(lambda s: s > 0))
        out[c] = 0.125 * BL.z(BL.daily(cm, "mean") - BL.daily(um, "mean"), 90).clip(-2, 2) / 2
    return pd.DataFrame(out)
bk0, _ = BL.basket(V.index); r0 = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
out = {"reference v9.5": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]], "trials": {}}
base_members = list(BL.MEMBERS)
for k, fn in (("A COIN-M leverage build-up", coinm_lev), ("B COIN-M vs USDT-M taker divergence", taker_div)):
    BL.BUILD[k] = fn; BL.MEMBERS = base_members + [k]; bk, _ = BL.basket(V.index)
    mem = CS._from_daily_weights(fn().reindex(BL.DAYS).fillna(0.0), ["BTC", "ETH"], 5).reindex(V.index).fillna(0.0)
    b = unit(CS.portfolio_v5(V.assign(**{"diversifier basket": bk}))[0]); r = [shp(b), per(b)]
    ok = lambda R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
    out["trials"][k] = {"member": per(mem), "corr basket": round(float(mem.corr(bk0)), 2), "basket": per(bk), "book": r, "pass": bool(ok(REF) and ok(REF2))}
    print(k, out["trials"][k], flush=True)
BL.MEMBERS = base_members
(ROOT / "results/gen421.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
