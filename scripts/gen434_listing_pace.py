"""Gen434 (config/gen434_protocol.json): the pace of new perp listings as a froth signal. Writes results/gen434.json."""
import glob
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
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0])
TF = set(json.load(open(ROOT / "config/tradfi_perps.json"))["symbols"]); first = []
for f in glob.glob(str(LL.PIT / "*_1h.parquet")):
    if f.endswith("premium_1h.parquet"):
        continue
    s = Path(f).name[:-len("_1h.parquet")]
    if s not in TF:
        first.append(pd.read_parquet(f, columns=["close"]).index.min())
fd = pd.Series(1.0, index=pd.DatetimeIndex(first).floor("D")).groupby(level=0).sum().reindex(BL.DAYS).fillna(0.0)
fd[fd.index < pd.Timestamp("2020-02-01")] = np.nan                       # archive start: the first bars are not listings
L = np.log1p(fd.rolling(30, min_periods=30).sum())
z = ((L - L.rolling(365, min_periods=250).mean()) / L.rolling(365, min_periods=250).std()).shift(1)   # day d value used from row d + 1 (BL convention)
def member():
    w = -0.125 * z.clip(-2, 2) / 2; return pd.DataFrame({"BTC": w, "ETH": w}).fillna(0.0)
bk0, _ = BL.basket(idx); r0 = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk0}))[0]); REF2 = (shp(r0), per(r0))
base = list(BL.MEMBERS); BL.BUILD["listing pace"] = member; BL.MEMBERS = base + ["listing pace"]; bk, _ = BL.basket(idx); BL.MEMBERS = base
bA = unit(CS.portfolio_v5(V6.assign(**{"diversifier basket": bk}))[0]); rA = [shp(bA), per(bA)]
mA = CS._from_daily_weights(member().reindex(BL.DAYS).fillna(0.0), ["BTC", "ETH"], 5).reindex(idx).fillna(0.0)
wB = -0.15 * z.clip(-2, 2) / 2; WB = pd.DataFrame({c: wB for c in ("SOL", "XRP", "BNB", "DOGE")}).fillna(0.0)
sB = CS._from_daily_weights(WB.reindex(BL.DAYS).fillna(0.0), list(WB.columns), 5).reindex(idx).fillna(0.0)
bB = unit(CS.portfolio_v5(V6.assign(**{"listing-pace alt short": sB}))[0]); rB = [shp(bB), per(bB)]
REF_R = (3.161, [2.775, 3.919, 2.576])
ok = lambda r, R: r[0] >= R[0] + 0.05 and all(r[1][i] >= R[1][i] for i in range(3))
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing)": [shp(v96), per(v96)], "reference rebuilt basket": [REF2[0], REF2[1]],
       "listings per year": {str(k): int(v) for k, v in fd.groupby(fd.index.year).sum().items()},
       "A basket member (BTC/ETH)": {"member": per(mA), "basket": per(bk), "book": rA, "pass": bool(ok(rA, REF_R) and ok(rA, REF2))},
       "B alt sleeve": {"sleeve": per(sB), "book": rB, "pass": bool(ok(rB, REF_R))}}
(ROOT / "results/gen434.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
