"""Paper trading of the futures book (15 sleeves, Gen205-238 + Gen221, EQR fit 2010-22, 10% vol target; config/paper_futures.json).

Each run: research + new Databento bars (hub_data/databento_merged, see qpl.live.databento_update) -> the whole book is rebuilt
with the ADOPTED settings (scripts/futures_book_build.py, unchanged; only its research end date is moved forward) -> every
completed CME trading day after the last ledger row is appended ONCE to paper_trading/futures/ledger_hourly.csv and never revised.
Every day after 2026-09-30 is unseen by the research (the data ended there), so the backfill from 2026-10-01 is honest
out-of-sample evidence; rows computed more than 30 hours after the session close are flagged `late`.

    python scripts/futures_paper.py            # append new days
    python scripts/futures_paper.py --check    # research-data rebuild must equal the saved book (no new data needed)
    python scripts/futures_paper.py --reconcile  # recompute every ledger day with today's data and compare (appends nothing)

Simulation only: no orders, no broker, no credentials."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
CHECK = "--check" in sys.argv
if not CHECK:
    from qpl.live import databento_update as DU
    os.environ["QPL_DATABENTO"] = str(DU.merged_dir())                  # before futures_db is imported
import futures_db as F                                                    # noqa: E402

OUT = Path(os.environ.get("QPL_FUT_PAPER_OUT", ROOT / "paper_trading" / "futures"))           # env overrides: tests only
CFG = json.loads((ROOT / "config/paper_futures.json").read_text())
RESEARCH_END = "2026-09-30"


def data_end() -> pd.Timestamp:
    return pd.to_datetime(pd.read_parquet(F.DB / "ES_1h.parquet", columns=["ts_event"])["ts_event"], utc=True).max().tz_localize(None)


def build(end_date: str):
    """Sleeves (daily, unit) and the book's per-sleeve weights w_i * level_t, exactly as fbook.build but without its research end clip."""
    F.END = f"{end_date} 23:00"
    F.front.cache_clear(); F.second.cache_clear()
    src = (ROOT / "scripts/futures_book_build.py").read_text().split("\nb = B.build(P)")[0].replace('"2026-09-30"', f'"{end_date}"')
    g = {"__file__": str(ROOT / "scripts/futures_book_build.py"), "__name__": "futures_book_build_live"}
    exec(compile(src, "futures_book_build.py", "exec"), g)
    P = g["P"]
    P = P[P.index.weekday < 5].loc["2010-06-01":end_date].fillna(0.0); T = P.loc[:"2022-12-31"]
    w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    raw = (P * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    W = pd.DataFrame(np.outer(lvl.fillna(0.0), w), index=P.index, columns=P.columns)
    return P, W, (raw * lvl).dropna()


def ledger() -> pd.DataFrame:
    f = OUT / "ledger_hourly.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


def event(name, **kw):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "events.jsonl", "a") as fh:
        fh.write(json.dumps({"wall_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S"), "event": name, **kw}) + "\n")


def main():
    if CHECK:
        sys.path.insert(0, str(ROOT / "scripts")); import fbook
        P, W, b = build(RESEARCH_END); ref = fbook.build(fbook.sleeves())
        x = pd.concat([b, ref], axis=1).dropna()
        out = {"days": len(x), "max abs diff vs saved book": float((x.iloc[:, 0] - x.iloc[:, 1]).abs().max()),
               "splits": [round(F.sharpe(b, *s), 3) for s in F.SPLITS]}
        print(json.dumps(out, indent=1)); sys.exit(0 if out["max abs diff vs saved book"] < 1e-9 else 1)
    last = data_end()
    complete = F.trade_date(pd.DatetimeIndex([last]))[0] - pd.Timedelta(days=1)  # the trading day of the newest bar may be partial
    end_date = str(last.date())
    P, W, b = build(end_date)
    L = ledger(); done = pd.to_datetime(L["hour"]).dt.normalize().max() if len(L) else pd.Timestamp(os.environ.get("QPL_FUT_START", CFG["frozen"]["start_after"]))
    new = [d for d in b.index if done < d <= complete]
    now = pd.Timestamp.now("UTC").tz_localize(None)
    rows = []
    for d in new:
        close = pd.Timestamp(d) + pd.Timedelta(hours=21)                       # 17:00 ET ~ 21:00-22:00 UTC
        lag = (now - close).total_seconds() / 3600
        r = {"hour": close.strftime("%Y-%m-%d %H:%M:%S"), "port": float(b.loc[d])}
        for s in P.columns:
            r[s] = float(P.loc[d, s]); r["w " + s] = float(W.loc[d, s])
        r.update({"computed_at": now.strftime("%Y-%m-%d %H:%M:%S"), "lag_h": round(lag, 1), "late": bool(lag > 30)})
        rows.append(r)
    if rows and "--reconcile" not in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        pd.concat([L, pd.DataFrame(rows)], ignore_index=True).to_csv(OUT / "ledger_hourly.csv", index=False)
        event("appended", days=len(rows), first=rows[0]["hour"], last=rows[-1]["hour"], data_end=str(last))
    stale = (now - last).total_seconds() / 86400 > 4
    if stale:
        event("stale_data", data_end=str(last))
    L = ledger()
    summ = {"data_end": str(last), "appended": len(rows), "ledger_days": len(L), "stale": bool(stale)}
    if len(L) >= 5:
        r = L["port"].astype(float); summ.update({"paper Sharpe (ann.)": round(float(r.mean() / r.std() * np.sqrt(252)), 2), "paper cum": round(float((1 + r).prod() - 1), 4),
                                                   "z vs backtest": round(float((r.mean() - CFG["reference"]["daily_mean"]) / (CFG["reference"]["daily_sd"] / np.sqrt(len(r)))), 2)})
    (OUT / "status.json").write_text(json.dumps(summ, indent=1)); print(json.dumps(summ, indent=1))
    if "--reconcile" in sys.argv and len(L):
        x = pd.Series(L["port"].astype(float).to_numpy(), index=pd.to_datetime(L["hour"]).dt.normalize())
        y = b.reindex(x.index)
        print(json.dumps({"corr": round(float(x.corr(y)), 4), "cum diff": round(float((1 + x).prod() - (1 + y.fillna(0)).prod()), 5)}, indent=1))


if __name__ == "__main__":
    main()
