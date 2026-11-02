"""v9.9 R42 (research/v99/r42_protocol.json): Binance HODLer-airdrop coins as a sell-the-news sleeve. Writes results/v99/r42_hodler.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34


def events():
    arts = {}
    for cat in (48, 49, 157, 93):
        f = ROOT / f"research_data/binance_announcements/catalog_{cat}.json"
        if f.exists():
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
    ev = {}
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms")
        if "HODLer Airdrop" not in a["title"] or not (pd.Timestamp("2021-06-01") <= t <= pd.Timestamp("2026-09-23")):
            continue
        for tk in re.findall(r"\(([A-Z0-9]{2,15})\)", a["title"]):
            for c in (tk, "1000" + tk):
                cl, _ = EL._closes(c)
                if cl is None:
                    continue
                first = cl.index[(cl.index >= t.floor("h"))]
                if len(first) and first[0] <= t + pd.Timedelta(hours=72):
                    ev[c] = min(ev.get(c, first[0]), first[0]); break
    return ev


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); E = events(); h, _ = RB.venue(list(E.items()), idx); _, used = R16.trades(E, idx, "A")
    R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year; r = book(V8.assign(**{"hodler short": h}))
    hu, _ = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    ha, _ = RB.venue(list(R34.events().items()), idx); HB = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha})
    out = {"reference v9.8": ref, "events with a perp within 72 h": len(E), "traded": len(used),
           "mean trade %": round(float(R.mean()), 2) if len(R) else None, "median %": round(float(np.median(R)), 2) if len(R) else None,
           "hit rate": round(float((R > 0).mean()), 3) if len(R) else None,
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "sleeve 2022 / 23-24 / 25-26": per(h), "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": book(V8.assign(**{"hodler short": RB.venue([(c, t + pd.Timedelta(days=d)) for c, t in E.items()], idx)[0]})) for d in (-60, 60)},
           "ALL + add": book(HB), "ALL + add + hodler": book(HB.assign(**{"hodler short": h}))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r42_hodler.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
