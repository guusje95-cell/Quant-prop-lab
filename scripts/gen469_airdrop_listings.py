"""Gen469 (config/gen469_protocol.json): Gen468 event short with airdrop-token listings (Launchpool / HODLer Airdrops / Megadrop)
sized x2. Writes results/gen469.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
END = "2026-09-30"; ANN = ROOT / "research_data/binance_announcements"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
AIR = {}
for c in (48, 49, 93):
    for a in json.loads((ANN / f"catalog_{c}.json").read_text())["articles"]:
        m = re.search(r"\(([A-Z0-9]{2,15})\) on Binance (Launchpool|HODLer Airdrops|Megadrop)", a["title"])
        if m:
            t = pd.to_datetime(a["releaseDate"], unit="ms"); AIR[m.group(1)] = min(t, AIR.get(m.group(1), t))
orig = EL.crowding; hits = []
def crowding(sym, t0):
    k = orig(sym, t0); e = (t0 + pd.Timedelta(hours=24)).ceil("D"); base = sym[:-4]
    for b in (base, base[4:] if base.startswith("1000") else None):
        if b in AIR and AIR[b] < e:
            hits.append((sym, str(e.date()))); return 2.0 * k
    return k
s8, _, _ = EL.pnl(idx); b8 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s8}))[0]); R8 = [shp(b8), per(b8)]
EL.crowding = crowding
s, _, _ = EL.pnl(idx); b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
yrs = pd.Series([h[1][:4] for h in hits]).value_counts().sort_index().to_dict()
out = {"reference v9.8 candidate": R8, "reference v9.7": [3.012, [2.495, 3.784, 2.509]], "airdrop announcements": len(AIR), "listing events sized x2": len(hits),
       "by entry year": yrs, "sleeve": per(s), "book": r, "pass": bool(r[0] >= R8[0] + 0.05 and all(r[1][i] >= R8[1][i] for i in range(3)))}
(ROOT / "results/gen469.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
