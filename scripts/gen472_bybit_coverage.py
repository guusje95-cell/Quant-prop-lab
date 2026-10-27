"""Gen472 (descriptive): share of the v9.8 event short that was tradable on Bybit (HyroTrader's exchange) at the time: a Bybit
USDT perp of the same base (1000x / 10000x prefixes matched) launched before that hour (research_data/bybit_listings/instruments.json,
all statuses; Bybit closure dates are not known, so a coin Bybit already delisted counts as tradable: an upper bound). Writes results/gen472.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
END = "2026-09-30"; BY = ROOT / "research_data/bybit_listings"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
norm = lambda b: re.sub(r"^1[0]+", "", b)
LAUNCH = {}                                                            # base -> first Bybit launch (instruments.json, all statuses)
for x in json.loads((BY / "instruments.json").read_text()):
    if x["symbol"].endswith("USDT") and x["launchTime"] > 0:
        bb = norm(x["symbol"][:-4]); t = pd.to_datetime(x["launchTime"], unit="ms"); LAUNCH[bb] = min(t, LAUNCH.get(bb, t))
KEEP = {}
def mask(P, CF):
    P = P.copy()
    for n in P.columns:
        b = norm(n[4:] if n.startswith("spo_") else n); t0 = LAUNCH.get(b)
        m = (P.index - pd.Timedelta(hours=1) >= t0) if t0 is not None else np.zeros(len(P), bool)   # closure dates unknown: upper bound
        KEEP[n] = pd.Series(m, index=P.index)
        P[n] = P[n].where(m, 0.0)
    return P
full = {}
def grab(P, CF):
    full["P"] = P.copy(); return P
s8, _, _ = EL.pnl(idx, pre_cap=grab); P = full["P"]
b8 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s8}))[0])
sb, _, _ = EL.pnl(idx, pre_cap=mask); bb = unit(CS.portfolio_v5(V7.assign(**{"listing short": sb}))[0])
K = pd.DataFrame(KEEP).reindex(columns=P.columns).fillna(False)
g = P.abs(); share = {y: round(float(g.loc[y].where(K.loc[y]).sum().sum() / max(g.loc[y].sum().sum(), 1e-12)), 3) for y in ("2022", "2023", "2024", "2025", "2026")}
out = {"gross share on Bybit-tradable coins by year": share, "v9.8 (Binance universe)": {"sleeve": per(s8), "book": [shp(b8), per(b8)]},
       "v9.8 with the event short restricted to Bybit-tradable coins": {"sleeve": per(sb), "book": [shp(bb), per(bb)]}}
(ROOT / "results/gen472.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
