"""CME futures history from Databento (your own account), saved to research_data/databento/.

The API key is read from the DATABENTO_API_KEY environment variable only: never put it in a file, in source code or in chat.

    python -m qpl.live.databento_futures                 # COST CHECK ONLY (free, downloads nothing)
    python -m qpl.live.databento_futures --download --max-cost 20
    python -m qpl.live.databento_futures --minute                     # cost check for 1-minute bars (ES NQ GC CL, 2018+)
        downloads only if the quoted total is <= --max-cost dollars (set it to what your free credit covers).

Data: GLBX.MDP3 (CME Globex, from 2010-06-06), hourly OHLCV, volume-rolled continuous front (.v.0) and second (.v.1) contract
(the second one gives the roll yield / carry). Daily bars are built from the hourly ones in research."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "databento"
DATASET, SCHEMA, START, END = "GLBX.MDP3", "ohlcv-1h", "2010-06-06", "2026-10-01"
ROOTS = ["ES", "NQ", "RTY", "YM",                 # equity indices (micros MES/MNQ/M2K/MYM track these 1:1)
         "ZN", "ZB", "ZF", "ZT",                  # treasuries
         "6E", "6J", "6B", "6A", "6C", "6S",      # FX
         "GC", "SI", "HG", "CL", "NG", "RB", "HO",  # metals, energy
         "ZC", "ZS", "ZW", "LE", "HE",            # grains, livestock
         "BTC", "ETH"]                            # CME crypto (basis vs Binance, CME gap / expiry)


def symbols():
    return [f"{r}.v.{k}" for r in ROOTS for k in (0, 1)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--download", action="store_true"); ap.add_argument("--max-cost", type=float, default=0.0)
    ap.add_argument("--minute", action="store_true", help="1-minute bars, front contract only, for --roots from --start (intraday research)")
    ap.add_argument("--priority", action="store_true", help="download --roots in the given order while the running total stays <= --max-cost (skip the rest)")
    ap.add_argument("--roots", nargs="*", default=None, help="minute mode: default ES NQ GC CL; hourly mode: default all ROOTS"); ap.add_argument("--start", default="2018-01-01"); ap.add_argument("--end", default=None)
    a = ap.parse_args()
    global SCHEMA, START, ROOTS, END
    if a.minute:
        SCHEMA, START, ROOTS = "ohlcv-1m", a.start, (a.roots or ["ES", "NQ", "GC", "CL"])
        if a.end:
            END = a.end
    elif a.roots:
        ROOTS = a.roots                                     # hourly mode for a few extra roots (e.g. BZ, Gen128)
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (see get_futures_data.bat). Do not paste the key anywhere else.")
    import databento as db
    client = db.Historical(key)
    total = 0.0; cost = {}
    for r in ROOTS:
        c = client.metadata.get_cost(dataset=DATASET, start=START, end=END, symbols=[f"{r}.v.0"] if a.minute else [f"{r}.v.0", f"{r}.v.1"], schema=SCHEMA, stype_in="continuous")
        total += c; cost[r] = c; print(f"{r:4s} ${c:8.2f}", flush=True)
    print(f"TOTAL quoted cost: ${total:.2f}  (check your free credit on databento.com -> Billing)")
    if not a.download:
        print("Cost check only; nothing downloaded."); return
    if a.priority:
        run, keep = 0.0, []
        for r in ROOTS:
            if run + cost[r] <= a.max_cost:
                run += cost[r]; keep.append(r)
        print(f"Priority mode: downloading {keep} for ${run:.2f}; skipped {[r for r in ROOTS if r not in keep]}")
        ROOTS = keep
    elif total > a.max_cost:
        sys.exit(f"Quoted ${total:.2f} is above --max-cost {a.max_cost:.2f}: nothing downloaded.")
    OUT.mkdir(parents=True, exist_ok=True)
    for r in ROOTS:
        f = OUT / ((f"{r}_1m_{START[:4]}_{int(END[:4]) - 1}.parquet" if a.end else f"{r}_1m.parquet") if a.minute else f"{r}_1h.parquet")
        if f.exists():
            print(f"{r}: exists, skipped"); continue
        data = client.timeseries.get_range(dataset=DATASET, start=START, end=END, symbols=[f"{r}.v.0"] if a.minute else [f"{r}.v.0", f"{r}.v.1"],
                                           schema=SCHEMA, stype_in="continuous")
        df = data.to_df()
        df = df.reset_index()[["ts_event", "symbol", "open", "high", "low", "close", "volume", "instrument_id"]]
        if a.minute:                                   # keep files well under GitHub's 100 MB limit
            df = df.astype({c: "float32" for c in ("open", "high", "low", "close")}).astype({"volume": "int32", "symbol": "category"})
        df.to_parquet(f, index=False, compression="zstd"); print(f"{r}: {len(df)} rows, {f.stat().st_size / 1e6:.0f} MB", flush=True)
    print("Done.")


if __name__ == "__main__":
    main()
