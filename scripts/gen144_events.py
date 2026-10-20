"""Gen144 (config/gen144_protocol.json): intraday FOMC, OPEX pinning, leveraged-ETF rebalancing, daily pre-FOMC drift.
Writes results/gen144.csv and results/gen144_daily.parquet."""
import shutil
import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import gen124_intraday as I
FOMC = set(pd.to_datetime(pd.read_parquet(ROOT / "research_data/more2/fomc_dates.parquet").statement_date).dt.normalize())


def third_friday(d):
    return d.weekday() == 4 and 15 <= d.day <= 21


def run(B, root):
    cost = lambda p: F.cost_frac(root, p)
    out = {k: {} for k in ("J8a", "J8b", "J4", "J5")}; prev_c, prev_id, absr = np.nan, None, []
    for day, g in B.groupby(B.index.normalize()):
        if day.weekday() >= 5:
            continue
        o930, i0 = I.at(g, "09:30", "open"); c16, i16 = I.last_before(g, "16:00")
        if day in FOMC:
            p1, ia = I.last_before(g, "13:55")
            if np.isfinite(o930) and np.isfinite(p1) and i0 == ia:
                out["J8a"][day] = (p1 / o930 - 1) - 2 * cost(o930)
            a0, ib = I.at(g, "14:00", "open"); a5, ic = I.last_before(g, "14:05"); x, idd = I.last_before(g, "15:55")
            if np.isfinite(a0) and np.isfinite(a5) and np.isfinite(x) and len({ib, ic, idd}) == 1 and a5 != a0:
                out["J8b"][day] = np.sign(a5 / a0 - 1) * (x / a5 - 1) - 2 * cost(a5)
        if third_friday(day):
            p11, i1 = I.last_before(g, "11:00"); p15, i2 = I.last_before(g, "15:00")
            if np.isfinite(o930) and np.isfinite(p11) and np.isfinite(p15) and len({i0, i1, i2}) == 1 and p11 != o930:
                out["J4"][day] = -np.sign(p11 / o930 - 1) * (p15 / p11 - 1) - 2 * cost(p11)
        p1530, i3 = I.last_before(g, "15:30"); p1558, i4 = I.last_before(g, "15:58")
        if np.isfinite(prev_c) and np.isfinite(p1530) and np.isfinite(p1558) and prev_id == i3 == i4 and len(absr) >= 20:
            m = p1530 / prev_c - 1
            if abs(m) > 1.5 * np.mean(absr[-20:]):
                out["J5"][day] = np.sign(m) * (p1558 / p1530 - 1) - 2 * cost(p1530)
        if np.isfinite(c16) and np.isfinite(prev_c) and prev_id == i16:
            absr.append(abs(c16 / prev_c - 1))
        prev_c, prev_id = c16, i16
    return {k: pd.Series(v, dtype=float) for k, v in out.items()}


B = {r: I.bars_futures(r) for r in ("ES", "NQ")}; RES = {r: run(B[r], r) for r in B}
tmp = Path(tempfile.mkdtemp()); shutil.copy(F.DB / "NQ_1m_2010_2017.parquet", tmp / "NQ_1m.parquet"); real = F.DB; F.DB = tmp
OLD = run(I.bars_futures("NQ").loc[:"2017-12-31 23:59"], "NQ"); F.DB = real
rows, PNL = [], {}
bd = pd.date_range("2018-01-01", "2026-09-30", freq="B"); bd_old = pd.date_range("2010-06-01", "2017-12-31", freq="B")
names = {"J8a": "J8a pre-FOMC drift (intraday)", "J8b": "J8b post-FOMC continuation", "J4": "J4 options-expiry pinning fade", "J5": "J5 leveraged-ETF rebalancing, big days"}
for k, nm in names.items():
    p = pd.concat([RES["ES"][k], RES["NQ"][k]], axis=1).fillna(0.0).mean(axis=1).reindex(bd).fillna(0.0)
    kk = tuple(round(I.sharpe(p, a, b), 3) for a, b in I.SPL)
    old = OLD[k].reindex(bd_old).fillna(0.0)
    r = {"test": nm, "DEV": kk[0], "TEST": kk[1], "HOLD": kk[2], "pass": bool(kk[0] > 0 and kk[1] >= 0.5 and kk[2] >= 0.3),
         "events": int(max(len(RES["ES"][k]), len(RES["NQ"][k]))), "mean bp/event": round(float(pd.concat([RES["ES"][k], RES["NQ"][k]]).mean() * 1e4), 2),
         "NQ 2010-17 (report)": round(I.sharpe(old, "2010-06-01", "2017-12-31"), 3)}
    rows.append(r); PNL[nm] = p; print(r, flush=True)
# J8c daily pre-FOMC drift 2010-26
es = F.daily("ES"); W = pd.Series(0.0, index=es.index)
for d in FOMC:
    if d in W.index:
        W.loc[d] = 1.0                                               # held during the statement day (decided at the previous close)
pnl = W * es.r - W.diff().abs().fillna(W.abs()) * es.cost
kk = F.splits(pnl); r = {"test": "J8c pre-FOMC drift, daily ES 2010-26", "DEV": kk[0], "TEST": kk[1], "HOLD": kk[2], "pass": F.passes(kk), "events": int(W.sum())}
rows.append(r); PNL[r["test"]] = pnl; print(r, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen144.csv", index=False); pd.DataFrame(PNL).to_parquet(ROOT / "results/gen144_daily.parquet")
