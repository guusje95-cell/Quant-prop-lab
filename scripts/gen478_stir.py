"""Gen478 (config/gen478_protocol.json): short-rate futures (ZQ, SR3, GE) as futures-book sleeves. Writes results/gen478.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import fbook
import futures_db as F
D = ROOT / "research_data/databento_stir"
COST = {"ZQ": (0.0025, 4167.0), "SR3": (0.005, 2500.0), "GE": (0.005, 2500.0)}    # tick, $ per 1.00 price point


def series(root: str, rank: int) -> pd.DataFrame:
    """daily (CME trade date) roll-safe return, close and cost fraction of ROOT.v.rank"""
    d = pd.read_parquet(D / f"{root}_1h.parquet"); d = d[d.symbol == f"{root}.v.{rank}"].copy()
    d["ts"] = pd.to_datetime(d.ts_event, utc=True).dt.tz_localize(None); d = d.drop_duplicates("ts").set_index("ts").sort_index()
    d = d[d.index <= pd.Timestamp("2026-09-30 23:00")]
    same = d.instrument_id.eq(d.instrument_id.shift(1)); r = (d.close / d.close.shift(1) - 1).where(same).fillna(0.0)
    td = F.trade_date(d.index)
    out = pd.DataFrame({"r": r.groupby(td).apply(lambda x: float(np.prod(1 + x) - 1)), "close": d.close.groupby(td).last()})
    out = out[out.index.weekday < 5]
    tick, mult = COST[root]; out["cost"] = tick / out.close + 2.5 / (out.close * mult)
    return out


def sleeve(legs):
    """legs: list of (daily frame, position series); vol-sized, NO cap (protocol), equal weight"""
    pnl, lev = [], []
    for d, pos in legs:
        vol = d.r.rolling(60, min_periods=40).std() * np.sqrt(252)
        w = (pos.reindex(d.index).fillna(0.0) * 0.10 / vol).replace([np.inf, -np.inf], 0.0).fillna(0.0).shift(1).fillna(0.0)
        pnl.append(w * d.r - w.diff().abs().fillna(w.abs()) * d.cost); lev.append(w.abs())
    return pd.concat(pnl, axis=1).fillna(0.0).mean(axis=1), pd.concat(lev, axis=1).fillna(0.0).mean(axis=1)


ge4, sr4 = series("GE", 4), series("SR3", 4)
y1 = pd.concat([ge4.loc[:"2018-12-31"], sr4.loc["2019-01-01":]])
ge0, sr0 = series("GE", 0), series("SR3", 0)
p0 = pd.concat([ge0.close.loc[:"2018-12-31"], sr0.close.loc["2019-01-01":]]); p4 = y1.close
zq6 = series("ZQ", 6)
trend = lambda d: 0.5 * (np.sign(d.r.rolling(63).apply(lambda x: np.prod(1 + x) - 1, raw=True)) + np.sign(d.r.rolling(252).apply(lambda x: np.prod(1 + x) - 1, raw=True)))
S, LEV = {}, {}
S["S1 STIR trend"], LEV["S1 STIR trend"] = sleeve([(y1, trend(y1)), (zq6, trend(zq6))])
S["S2 STIR term premium"], LEV["S2 STIR term premium"] = sleeve([(y1, ((p0 - p4) / 0.25).clip(0, 1))])
base = fbook.sleeves(); bk = fbook.build(base); ref = [round(F.sharpe(bk, *s), 3) for s in F.SPLITS]
out = {"reference": ref, "trials": {}}; entrants = {}
for k, p in S.items():
    tune = round(F.sharpe(p, "2010-06-01", "2022-12-31"), 3)
    b = fbook.build(base.assign(**{k: p})); r = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
    e = bool(tune >= 0.3)
    out["trials"][k] = {"sleeve 2010-17 / 2018-22 / 2023-26": list(F.splits(p)), "tune": tune, "appraisal ES/NQ 2010-22": round(fbook.appraisal(p), 3),
                        "corr with book 2023-26": round(float(pd.concat([p, bk], axis=1, sort=True).loc["2023":].corr().iloc[0, 1]), 2),
                        "median notional leverage per market when active": round(float(LEV[k][LEV[k] > 0].median()), 1),
                        "by year": {str(y): round(F.sharpe(p, str(y), str(y)), 2) for y in range(2011, 2027)},
                        "enters": e, "book": r, "pass": bool(e and r[2] >= ref[2] + 0.05 and r[0] >= ref[0] and r[1] >= ref[1])}
    if e:
        entrants[k] = p
    print(k, {x: v for x, v in out["trials"][k].items() if x != "by year"}, flush=True)
if len(entrants) > 1:
    b = fbook.build(base.assign(**entrants)); out["all entrants together"] = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
out["passed"] = [k for k, v in out["trials"].items() if v["pass"]]
(ROOT / "results/gen478.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in out if k != "trials"}, indent=1))
