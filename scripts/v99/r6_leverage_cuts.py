"""v9.9 R6 (research/v99/r6_protocol.json): Binance single-coin leverage / margin-tier cuts as event shorts. Writes results/v99/r6_leverage_cuts.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/hub_research")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import event_live as EL
import bybit_event_shorts as BES
ev = []
for f in ("catalog_49.json", "catalog_161.json", "catalog_48.json", "catalog_93.json"):
    for a in json.loads((ROOT / "research_data/binance_announcements" / f).read_text())["articles"]:
        t = a["title"]
        if re.search(r"leverage|margin tier", t, re.I) and re.search(r"Update", t, re.I) and not re.search(r"multiple|portfolio margin|BLVT|Leveraged Token|tick size", t, re.I):
            for c in sorted(set(re.findall(r"\b([A-Z0-9]{2,15})USDT\b", t))):
                ev.append((c, pd.to_datetime(a["releaseDate"], unit="ms")))
ev = sorted(set(ev), key=lambda e: e[1]); ev = [e for e in ev if pd.Timestamp("2021-06-01") <= e[1] <= pd.Timestamp("2026-09-30")]
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z="2026-09-30"):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025")]
s0, _, _ = EL.pnl(idx); b0 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s0}))[0])
h = BES.make_hook(ev, idx); s1, _, _ = EL.pnl(idx, pre_cap=h); b1 = unit(CS.portfolio_v5(V7.assign(**{"listing short": s1}))[0])
out = {"events": len(ev), "events used": getattr(h, "added", 0), "event short before / after": [per(s0), per(s1)],
       "reference v9.8": [shp(b0), per(b0)], "book with leverage-cut shorts": [shp(b1), per(b1)]}
r, ref = out["book with leverage-cut shorts"], out["reference v9.8"]
out["pass"] = bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))
(ROOT / "results/v99/r6_leverage_cuts.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
