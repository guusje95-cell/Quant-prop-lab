"""Daily top-up of the CME hourly bars the futures book needs (Databento, your own account), for the futures paper trader.

The API key is read from the DATABENTO_API_KEY environment variable only (typed into the .bat window, never saved).

    python -m qpl.live.databento_update                      # COST CHECK ONLY (free, downloads nothing)
    python -m qpl.live.databento_update --max-cost 1.0       # downloads only if the quoted total is <= $1.00

New bars (after the research files, which end 2026-09-30 23:00 UTC) go to research_data/databento_live/<ROOT>_1h.parquet
(append-only, same columns as research_data/databento). `merged_dir()` writes research + live into hub_data/databento_merged/
for the paper trader (QPL_DATABENTO points there). Nothing here trades or spends money beyond the quoted, capped download."""
import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(os.environ.get("QPL_DB_RESEARCH", ROOT / "research_data" / "databento"))      # env overrides: tests only
LIVE = Path(os.environ.get("QPL_DB_LIVE", ROOT / "research_data" / "databento_live"))
MERGED = Path(os.environ.get("QPL_DB_MERGED", ROOT / "hub_data" / "databento_merged"))
DATASET, SCHEMA = "GLBX.MDP3", "ohlcv-1h"
COLS = ["ts_event", "symbol", "open", "high", "low", "close", "volume", "instrument_id"]
ROOTS = ["ES", "NQ", "RTY", "YM", "ZN", "ZB", "ZF", "ZT", "6E", "6J", "6B", "6A", "6C", "6S",       # = futures_db.NONCRYPTO: every
         "GC", "SI", "HG", "CL", "NG", "RB", "HO", "ZC", "ZS", "ZW", "LE", "HE"]                     # market a book sleeve reads


def last_ts(root: str) -> pd.Timestamp:
    for f in (LIVE / f"{root}_1h.parquet", RESEARCH / f"{root}_1h.parquet"):
        if f.exists():
            return pd.to_datetime(pd.read_parquet(f, columns=["ts_event"])["ts_event"], utc=True).max()
    return pd.Timestamp("2026-09-30 23:00", tz="UTC")


def merged_dir(roots=ROOTS) -> Path:
    """research + live bars per root into hub_data/databento_merged (rewritten each run; the research files stay untouched)."""
    MERGED.mkdir(parents=True, exist_ok=True)
    for r in roots:
        parts = [pd.read_parquet(f) for f in (RESEARCH / f"{r}_1h.parquet", LIVE / f"{r}_1h.parquet") if f.exists()]
        if parts:
            d = pd.concat(parts, ignore_index=True)
            d["ts_event"] = pd.to_datetime(d["ts_event"], utc=True)
            d.drop_duplicates(["ts_event", "symbol"], keep="last").sort_values("ts_event")[COLS].to_parquet(MERGED / f"{r}_1h.parquet", index=False)
    return MERGED


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max-cost", type=float, default=0.0, help="download only if the quoted total is <= this many dollars")
    ap.add_argument("--end", default=None, help="UTC end (exclusive); default today 00:00 UTC")
    a = ap.parse_args()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (futures_paper_update.bat asks for it). Do not paste the key anywhere else.")
    import databento as db
    client = db.Historical(key)
    end = pd.Timestamp(a.end, tz="UTC") if a.end else pd.Timestamp.now("UTC").normalize()
    plan = {}
    for r in ROOTS:
        s = last_ts(r) + pd.Timedelta(hours=1)
        if s < end:
            plan[r] = (s, end)
    if not plan:
        print("Nothing to download: every root is up to date."); return
    total, cost = 0.0, {}
    for r, (s, e) in plan.items():
        for k in range(4):
            try:
                c = float(client.metadata.get_cost(dataset=DATASET, start=s.isoformat(), end=e.isoformat(), symbols=[f"{r}.v.0", f"{r}.v.1"],
                                                   schema=SCHEMA, stype_in="continuous")); break
            except Exception as ex:                                            # noqa: BLE001 - Databento 504s / data not yet available
                if k == 3:
                    print(f"{r}: cost check failed ({str(ex)[:120]}); skipped"); c = None
                else:
                    time.sleep(10 * (k + 1))
        if c is not None:
            cost[r] = c; total += c
            print(f"{r:3s} {s:%Y-%m-%d %H:%M} .. {e:%Y-%m-%d %H:%M}  ${c:.4f}", flush=True)
    print(f"TOTAL quoted cost: ${total:.4f} (limit ${a.max_cost:.2f})")
    if total > a.max_cost:
        print("Above the limit (or the limit is 0 = cost check only): nothing downloaded."); return
    LIVE.mkdir(parents=True, exist_ok=True)
    for r in cost:
        s, e = plan[r]
        df = client.timeseries.get_range(dataset=DATASET, start=s.isoformat(), end=e.isoformat(), symbols=[f"{r}.v.0", f"{r}.v.1"],
                                         schema=SCHEMA, stype_in="continuous").to_df().reset_index()
        if df.empty:
            print(f"{r}: no new bars"); continue
        df = df[COLS]; f = LIVE / f"{r}_1h.parquet"
        if f.exists():
            df = pd.concat([pd.read_parquet(f), df], ignore_index=True)
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
        df = df.drop_duplicates(["ts_event", "symbol"], keep="last").sort_values("ts_event")
        df.to_parquet(f, index=False, compression="zstd"); print(f"{r}: {len(df)} live rows up to {df.ts_event.max()}", flush=True)
    print("Done.")


if __name__ == "__main__":
    main()
