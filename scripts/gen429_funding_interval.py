"""Gen429 (config/gen429_protocol.json): fade the crowded side after Binance shortens a perp's funding interval. Writes results/gen429.json."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, _ = LL.pnl(idx); V6 = V.assign(**{"listing short": ls}); v96 = unit(CS.portfolio_v5(V6)[0])
TF = set(json.load(open(ROOT / "config/tradfi_perps.json"))["symbols"]); EV = []; DATA = {}
for f in sorted(glob.glob(str(LL.PIT / "*_funding.parquet"))):
    s = Path(f).name[:-len("_funding.parquet")]
    if s[:-4] in TF or not (LL.PIT / f"{s}_1h.parquet").exists():
        continue
    d = pd.read_parquet(f).sort_values("time").reset_index(drop=True); d["time"] = pd.to_datetime(d["time"]); h = d["funding_interval_hours"].astype(float)
    k = pd.read_parquet(LL.PIT / f"{s}_1h.parquet")["close"].astype(float); k.index = pd.DatetimeIndex(k.index)
    if len(k) == 0:
        continue
    DATA[s] = (k, pd.Series(d["last_funding_rate"].to_numpy(), index=d["time"].dt.floor("h")).groupby(level=0).last())
    for i in d.index[(h < h.shift(1)).fillna(False)]:
        t = d.loc[i, "time"]
        if t < k.index.min() + pd.Timedelta(days=30):
            continue
        side = -np.sign(d.loc[max(0, i - 2):i, "last_funding_rate"].sum())
        if side != 0:
            EV.append((s, t.ceil("h"), side))
def sleeve(H):
    P = {}
    for s, t, side in sorted(EV, key=lambda e: e[1]):
        k, _ = DATA[s]; n = s[:-4]
        cc = k.loc[t:t + pd.Timedelta(days=H)]
        if len(cc) == 0:
            continue
        ref = cc.iloc[0]; adverse = cc[(cc / ref - 1) * side <= -0.30].index
        last = adverse[0] if len(adverse) else t + pd.Timedelta(days=H) - pd.Timedelta(hours=1)
        dec = pd.Series(0.05 * side, index=k.loc[t:last].index); p = dec.copy(); p.index = p.index + pd.Timedelta(hours=1)   # listing_live timing
        p = p.reindex(idx).fillna(0.0)
        alive = k.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(); p = p.where(alive, 0.0)
        cur = P.get(n, pd.Series(0.0, index=idx))
        P[n] = cur.where(cur != 0, p)                                  # one position per coin: an open position is kept
    Pdf = pd.DataFrame(P); g = Pdf.abs().sum(axis=1); Pdf = Pdf.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx)
    for n in Pdf.columns:
        k, f = DATA[n + "USDT"]; p = Pdf[n]
        r = (k / k.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
    return out, g
REF_R = (3.161, [2.775, 3.919, 2.576])
out = {"reference v9.6 (research)": REF_R, "reference v9.6 (live timing)": [shp(v96), per(v96)], "events": len(EV),
       "events long / short": [int(sum(e[2] > 0 for e in EV)), int(sum(e[2] < 0 for e in EV))], "trials": {}}
for k, H in (("A hold 7 days", 7), ("B hold 3 days", 3)):
    s, g = sleeve(H); b = unit(CS.portfolio_v5(V6.assign(**{"funding-interval fade": s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "by year": {str(y): shp(s, str(y), str(y)) for y in range(2023, 2027)}, "corr listing short": round(float(dd(s).corr(dd(ls))), 2),
                        "book": r, "pass": bool(r[0] >= REF_R[0] + 0.05 and all(r[1][i] >= REF_R[1][i] for i in range(3)))}
    print(k, out["trials"][k], flush=True)
(ROOT / "results/gen429.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("events", "events long / short")}))
