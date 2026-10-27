"""Gen467 (config/gen467_protocol.json): delisting / monitoring-tag shorts merged with the listing short. Writes results/gen467.json."""
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
import pit_universe as PU
END = "2026-09-30"; ANN = ROOT / "research_data/binance_announcements"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, EVL = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
arts = []
for cat in (161, 49):
    arts += json.loads((ANN / f"catalog_{cat}.json").read_text())["articles"]
seen = set(); A = []
for a in arts:
    if a["id"] in seen:
        continue
    seen.add(a["id"]); A.append((pd.to_datetime(a["releaseDate"], unit="ms"), a["title"]))
def tick(s):
    s = re.sub(r"\(.*?\)", " ", s)
    return [t for t in re.split(r"[,&\s]+|\band\b", s) if re.fullmatch(r"[A-Z0-9]{2,15}", t or "")]
EV = {"spot delisting": [], "monitoring tag": [], "futures delisting": []}
for t, title in A:
    if t < pd.Timestamp("2021-06-01") or t > pd.Timestamp(END):
        continue
    m = re.match(r"Binance Will Delist (.+?) on \d{4}-\d{2}-\d{2}", title)
    if m and "Futures" not in title:
        EV["spot delisting"] += [(x, t) for x in tick(m.group(1))]; continue
    m = re.search(r"Monitoring Tag to Include (.+?)( on \d{4}-\d{2}-\d{2}|$)", title)
    if m:
        EV["monitoring tag"] += [(x, t) for x in tick(m.group(1))]; continue
    if title.startswith("Binance Futures Will Delist") and "Multiple" not in title:
        EV["futures delisting"] += [(x[:-4], t) for x in re.findall(r"([A-Z0-9]{2,15}USDT)", title)]
def close_f(c):
    if c in PU.PACK:
        from qpl.lab import binance_pack as B
        cl = B.k5(c).close.resample("1h").last(); fu = B.funding(c).copy()
    else:
        src = PU.EX / f"{c}USDT_1h.parquet" if c in PU.EXTRA else PU.PIT / f"{c}USDT_1h.parquet"
        if not src.exists():
            return None
        cl = pd.read_parquet(src)["close"].astype(float)
        fsrc = PU.EX / f"{c}USDT_funding.parquet" if c in PU.EXTRA else PU.PIT / f"{c}USDT_funding.parquet"
        x = pd.read_parquet(fsrc); fu = pd.Series(x["last_funding_rate"].astype(float).to_numpy(), index=pd.to_datetime(x["time"]))
    cl.index = pd.DatetimeIndex(cl.index).as_unit("ns"); fu.index = pd.DatetimeIndex(fu.index).as_unit("ns").floor("h")
    return cl, fu.groupby(level=0).sum()
def positions(evs, hold):
    P, CF, n = {}, {}, 0
    for c, t in evs:
        if c in PU.TF:
            continue
        cf = close_f(c) if c not in CF else CF[c]
        if cf is None:
            continue
        cl, fu = cf; start = t.ceil("h") + pd.Timedelta(hours=1); end = start + pd.Timedelta(days=hold)
        if not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
            continue                                                  # the perp was not trading at the announcement
        cc = cl.loc[start:end]
        if len(cc) == 0:
            continue
        hit = cc[cc >= cc.iloc[0] * 1.30].index; last = hit[0] if len(hit) else min(end, cl.index.max())
        p = pd.Series(-0.05, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
        p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
        cur = P.get(c, pd.Series(0.0, index=idx)); P[c] = cur.where(cur != 0, p); CF[c] = cf; n += 1
    return pd.DataFrame(P), CF, n
LL.CAP = 1e9; PL = LL.positions(idx, EVL); CFL = {s[:-4]: (c, f) for s, t0, c, f in EVL}
def merged(kinds):
    Ps, CF, counts = [PL], dict(CFL), {}
    for k in kinds:
        P, cf, n = positions(EV[k], 30 if k == "monitoring tag" else 14); Ps.append(P.add_prefix(k[:3] + "_")); counts[k] = n
        CF.update({k[:3] + "_" + c: v for c, v in cf.items()})
    P = pd.concat(Ps, axis=1).reindex(idx).fillna(0.0)
    g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    out = pd.Series(0.0, index=idx)
    for n in P.columns:
        c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
    return out, counts
out = {"reference v9.7": [REF[0], REF[1]], "parsed events": {k: len(v) for k, v in EV.items()}, "trials": {}}
for nm, kinds in (("A + spot delisting", ["spot delisting"]), ("B + monitoring tag", ["monitoring tag"]), ("C + all three", ["spot delisting", "monitoring tag", "futures delisting"])):
    s, counts = merged(kinds); b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"events traded": counts, "sleeve": per(s), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen467.json").write_text(json.dumps(out, indent=1)); print(out["parsed events"])
