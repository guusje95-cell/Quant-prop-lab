"""Gen457 (config/gen457_protocol.json): Tron stablecoin impulse as basket members. Writes results/gen457.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import basket_live as BL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
bk0, _ = BL.basket(idx); r0 = unit(CS.portfolio_v5(V7.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
ld = lambda ch: BL.daily(pd.read_parquet(ROOT / f"research_data/newdata/defillama_stablecoins_{ch}.parquet")["stablecoin_usd"].where(lambda s: s > 0))
tr, eth = np.log(ld("tron")), np.log(ld("ethereum"))
zz = lambda x: BL.z(x.diff(30), 365)
SIG = {"A Tron share impulse": zz(tr - eth), "B Tron impulse": zz(tr)}
mk = lambda z: (lambda: pd.DataFrame({"BTC": 0.125 * z.clip(-2, 2) / 2, "ETH": 0.125 * z.clip(-2, 2) / 2}).fillna(0.0))
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.7": [REF[0], REF[1]], "reference rebuilt basket": [REF2[0], REF2[1]], "trials": {}}
base = list(BL.MEMBERS)
for k, z in SIG.items():
    BL.BUILD[k] = mk(z); BL.MEMBERS = base + [k]; bk, _ = BL.basket(idx); BL.MEMBERS = base
    m = CS._from_daily_weights(mk(z)().reindex(BL.DAYS).fillna(0.0), ["BTC", "ETH"], 5).reindex(idx).fillna(0.0)
    b = unit(CS.portfolio_v5(V7.assign(**{"diversifier basket": bk}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"member": per(m), "by year": {str(y): shp(m, str(y), str(y)) for y in range(2022, 2027)}, "corr basket": round(float(dd(m).corr(dd(bk0))), 2),
                        "basket": per(bk), "book": r, "pass": bool(ok(r, REF) and ok(r, REF2))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen457.json").write_text(json.dumps(out, indent=1))
