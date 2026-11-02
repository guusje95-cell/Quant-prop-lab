"""v9.9 R40 (research/v99/r40_protocol.json): leverage-cut shorts (R6 events) as a separate sleeve. Writes results/v99/r40_levcut_sleeve.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/hub_research", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import bybit_event_shorts as BES
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32


def events():
    ev = []
    for f in ("catalog_49.json", "catalog_161.json", "catalog_48.json", "catalog_93.json"):
        for a in json.loads((ROOT / "research_data/binance_announcements" / f).read_text(encoding="utf-8"))["articles"]:
            t = a["title"]
            if re.search(r"leverage|margin tier", t, re.I) and re.search(r"Update", t, re.I) and not re.search(r"multiple|portfolio margin|BLVT|Leveraged Token|tick size", t, re.I):
                for c in sorted(set(re.findall(r"\b([A-Z0-9]{2,15})USDT\b", t))):
                    ev.append((c, pd.to_datetime(a["releaseDate"], unit="ms")))
    return [e for e in sorted(set(ev), key=lambda e: e[1]) if pd.Timestamp("2021-06-01") <= e[1] <= pd.Timestamp("2026-09-30")]


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    extra = lambda ev: EL.pnl(idx, pre_cap=BES.make_hook(ev, idx))[0] - s8
    ref = book(V8); E = events(); h = extra(E); r = book(V8.assign(**{"leverage-cut short": h}))
    hu, _ = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    HA = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf})
    out = {"reference v9.8": ref, "events": len(E), "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
           "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": book(V8.assign(**{"leverage-cut short": extra([(c, t + pd.Timedelta(days=d)) for c, t in E])})) for d in (-60, 60)},
           "ALL": book(HA), "ALL + leverage-cut sleeve": book(HA.assign(**{"leverage-cut short": h}))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r40_levcut_sleeve.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
