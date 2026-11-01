"""v9.9 R34 (research/v99/r34_protocol.json): 'Binance Will Add X on Earn, ..., Margin' events as a separate sell-the-news sleeve.
Writes results/v99/r34_binance_add.json."""
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
import r30b_checks as RB
ANN = ROOT / "research_data/binance_announcements"


def events():
    arts = {}
    for cat in (48, 49, 157, 93):
        f = ANN / f"catalog_{cat}.json"
        if f.exists():
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
    ev = {}
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms"); ti = a["title"]
        if not (pd.Timestamp("2021-06-01") <= t <= pd.Timestamp("2026-09-23")) or not re.match(r"Binance Will Add .+ on .*Margin", ti):
            continue
        for tk in re.findall(r"\(([A-Z0-9]{2,15})\)", ti):
            for c in (tk, "1000" + tk):
                cl, _ = EL._closes(c)
                if cl is not None and cl.index.min() <= t - pd.Timedelta(days=7):
                    T = t.ceil("h") - pd.Timedelta(hours=1)                         # R16 entry = close of bar T + 1 h = first whole hour after release + 1 h
                    ev[c] = min(ev.get(c, T), T); break
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
    ref = book(V8); E = list(events().items()); h, _ = RB.venue(E, idx)
    _, used = R16.trades(dict(E), idx, "A"); R = np.array([u["trade return %"] for u in used]); yrs = pd.to_datetime([u["t"] for u in used]).year
    r = book(V8.assign(**{"binance add short": h})); hc, _ = RB.venue(list(R16.events().items()), idx)
    out = {"reference v9.8": ref, "events": len(E), "traded": len(used), "mean trade %": round(float(R.mean()), 2) if len(R) else None,
           "median %": round(float(np.median(R)), 2) if len(R) else None, "hit rate": round(float((R > 0).mean()), 3) if len(R) else None,
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
           "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": book(V8.assign(**{"binance add short": RB.venue([(c, t + pd.Timedelta(days=d)) for c, t in E], idx)[0]})) for d in (-60, 60)},
           "with the Coinbase sleeve": {"reference v9.8 + Coinbase sleeve": book(V8.assign(**{"venue listing short": hc})),
                                        "+ binance add sleeve": book(V8.assign(**{"venue listing short": hc, "binance add short": h}))}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r34_binance_add.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
