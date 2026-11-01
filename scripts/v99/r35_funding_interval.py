"""v9.9 R35 (research/v99/r35_protocol.json): funding-interval change announcements, traded against the crowd, as a separate sleeve.
Writes results/v99/r35_funding_interval.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
ANN = ROOT / "research_data/binance_announcements"


def events():
    arts = {}
    for cat in (48, 49, 157, 93, 161):
        f = ANN / f"catalog_{cat}.json"
        if f.exists():
            arts.update({a["id"]: a for a in json.loads(f.read_text(encoding="utf-8"))["articles"]})
    ev = []
    for a in arts.values():
        t = pd.to_datetime(a["releaseDate"], unit="ms")
        if "Funding Rate Settlement Frequency" in a["title"] and pd.Timestamp("2021-06-01") <= t <= pd.Timestamp("2026-09-23"):
            ev += [(s[:-4], t) for s in re.findall(r"([A-Z0-9]{2,15}USDT)", a["title"])]
    return ev


def sleeve(ev, idx):
    pnl = pd.Series(0.0, index=idx); used = []; last = {}
    for c, t in sorted(ev, key=lambda e: e[1]):
        if c in last and t - last[c] < pd.Timedelta(days=7):
            continue
        cl, fu = EL._closes(c)
        if cl is None or not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
            continue
        f0 = fu.loc[:t].iloc[-1] if fu is not None and len(fu.loc[:t]) else 0.0
        side = -1 if f0 > 0 else (1 if f0 < 0 else 0)
        if side == 0:
            continue
        cl = cl.copy(); cl.index = cl.index + pd.Timedelta(hours=1)                     # stamp = close time
        start = t.ceil("h") + pd.Timedelta(hours=1); p = cl.loc[start:start + pd.Timedelta(days=7)]
        if len(p) < 2:
            continue
        adverse = p[(side * (p / p.iloc[0] - 1)) <= -0.30].index
        if len(adverse):
            p = p.loc[:adverse[0]]
        r = p.pct_change().dropna(); x = pd.Series(side * 0.05, index=r.index)
        f = fu.copy(); f.index = f.index + pd.Timedelta(hours=0); fr = f.groupby(level=0).sum().reindex(r.index).fillna(0.0) if len(f) else 0.0
        h = x * r - x * fr; h.iloc[0] -= 0.05 * 1e-3; h.iloc[-1] -= 0.05 * 1e-3
        h.index = h.index.floor("h") - pd.Timedelta(hours=1)
        pnl = pnl.add(h.groupby(level=0).sum().reindex(idx).fillna(0.0), fill_value=0.0); last[c] = t
        used.append({"coin": c, "t": str(t), "side": side, "funding": float(f0), "trade return %": round(float((1 + side * r).prod() - 1) * 100, 2)})
    return pnl, used


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); E = events(); h, used = sleeve(E, idx); R = np.array([u["trade return %"] for u in used])
    yrs = pd.to_datetime([u["t"] for u in used]).year; r = book(V8.assign(**{"funding-interval contrarian": h}))
    out = {"reference v9.8": ref, "parsed": len(E), "traded": len(used), "shorts / longs": [sum(u["side"] < 0 for u in used), sum(u["side"] > 0 for u in used)],
           "mean trade %": round(float(R.mean()), 2), "median %": round(float(np.median(R)), 2), "hit rate": round(float((R > 0).mean()), 3),
           "by year (n, mean %)": {int(y): [int((yrs == y).sum()), round(float(R[yrs == y].mean()), 2)] for y in sorted(set(yrs))},
           "sleeve 2022 / 23-24 / 25-26": per(h), "book": r, "pass": bool(len(used) >= 30 and r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "placebo": {f"{d:+d} days": book(V8.assign(**{"funding-interval contrarian": sleeve([(c, t + pd.Timedelta(days=d)) for c, t in E], idx)[0]})) for d in (-60, 60)}}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r35_funding_interval.json").write_text(json.dumps({**out, "trades": used}, indent=1))


if __name__ == "__main__":
    main()
