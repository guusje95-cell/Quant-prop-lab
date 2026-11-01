"""v9.9 R32 (research/v99/r32_protocol.json): Binance monitoring-tag and futures-delisting shorts as separate sleeves (Gen467 rules).
Writes results/v99/r32_binance_tag_sleeves.json."""
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
import pit_universe as PU
END = "2026-09-30"; ANN = ROOT / "research_data/binance_announcements"


def events():
    arts, seen, A = [], set(), []
    for cat in (161, 49):
        arts += json.loads((ANN / f"catalog_{cat}.json").read_text(encoding="utf-8"))["articles"]
    for a in arts:
        if a["id"] not in seen:
            seen.add(a["id"]); A.append((pd.to_datetime(a["releaseDate"], unit="ms"), a["title"]))
    tick = lambda s: [t for t in re.split(r"[,&\s]+|\band\b", re.sub(r"\(.*?\)", " ", s)) if re.fullmatch(r"[A-Z0-9]{2,15}", t or "")]
    EV = {"monitoring tag": [], "futures delisting": []}
    for t, title in A:
        if t < pd.Timestamp("2021-06-01") or t > pd.Timestamp(END):
            continue
        if re.match(r"Binance Will Delist (.+?) on \d{4}-\d{2}-\d{2}", title) and "Futures" not in title:
            continue
        m = re.search(r"Monitoring Tag to Include (.+?)( on \d{4}-\d{2}-\d{2}|$)", title)
        if m:
            EV["monitoring tag"] += [(x, t) for x in tick(m.group(1))]; continue
        if title.startswith("Binance Futures Will Delist") and "Multiple" not in title:
            EV["futures delisting"] += [(x[:-4], t) for x in re.findall(r"([A-Z0-9]{2,15}USDT)", title)]
    return EV


def sleeve(evs, hold, idx):
    P, CF = {}, {}
    for c, t in evs:
        if c in PU.TF:
            continue
        cl, fu = EL._closes(c)
        if cl is None:
            continue
        start = t.ceil("h") + pd.Timedelta(hours=1); end = start + pd.Timedelta(days=hold)
        if not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
            continue
        cc = cl.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * 1.30].index; last = hit[0] if len(hit) else min(end, cl.index.max())
        p = pd.Series(-0.05, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
        p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
        cur = P.get(c, pd.Series(0.0, index=idx)); P[c] = cur.where(cur != 0, p); CF[c] = (cl, fu)
    if not P:
        return pd.Series(0.0, index=idx), 0
    Pd = pd.DataFrame(P).reindex(idx).fillna(0.0); g = Pd.abs().sum(axis=1); Pd = Pd.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx)
    for n in Pd.columns:
        c, f = CF[n]; p = Pd[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy() if f is not None else pd.Series(dtype=float)
        if len(fu):
            fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        else:
            fu = pd.Series(0.0, index=idx)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
    return out, len(P)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); EV = events(); out = {"reference v9.8": ref, "parsed": {k: len(v) for k, v in EV.items()}}
    for name, kind, hold in (("A monitoring-tag short", "monitoring tag", 30), ("B futures-delisting short", "futures delisting", 14)):
        h, n = sleeve(EV[kind], hold, idx); r = book(V8.assign(**{name: h}))
        pl = {f"{d:+d} days": book(V8.assign(**{name: sleeve([(c, t + pd.Timedelta(days=d)) for c, t in EV[kind]], hold, idx)[0]})) for d in (-60, 60)}
        out[name] = {"coins traded": n, "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
                     "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))), "placebo": pl}
        print(name, json.dumps(out[name]), flush=True)
    (ROOT / "results/v99/r32_binance_tag_sleeves.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
