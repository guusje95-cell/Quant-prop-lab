"""Short-rate (STIR) futures from Databento for the futures programme (Gen478): 30-day Fed funds (ZQ), 3-month SOFR (SR3) and
Eurodollar (GE, until its 2023 delisting), hourly OHLCV of several continuous ranks (deferred contracts carry the rate path).

The API key is read from the DATABENTO_API_KEY environment variable only (typed into get_futures_stir.bat, never saved).

    python -m qpl.live.databento_stir                    # COST CHECK ONLY (free, downloads nothing)
    python -m qpl.live.databento_stir --max-cost 10      # downloads only if the quoted total is <= $10

Writes research_data/databento_stir/<ROOT>_1h.parquet with the same columns as research_data/databento (symbol = ROOT.v.<rank>)."""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "databento_stir"
DATASET, SCHEMA, START, END = "GLBX.MDP3", "ohlcv-1h", "2010-06-06", "2026-10-01"
PLAN = {"ZQ": [0, 1, 6], "SR3": [0, 1, 4], "GE": [0, 1, 4]}       # GE (Eurodollar) for the years before SOFR futures traded


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max-cost", type=float, default=0.0)
    a = ap.parse_args()
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (get_futures_stir.bat asks for it). Do not paste the key anywhere else.")
    import databento as db
    client = db.Historical(key)
    syms = {r: [f"{r}.v.{k}" for k in ks] for r, ks in PLAN.items()}
    total, cost = 0.0, {}
    for r, s in syms.items():
        if (OUT / f"{r}_1h.parquet").exists():
            print(f"{r}: already downloaded (skipped, not charged again)"); continue
        for k in range(4):
            try:
                c = float(client.metadata.get_cost(dataset=DATASET, start=START, end=END, symbols=s, schema=SCHEMA, stype_in="continuous")); break
            except Exception as e:                                             # noqa: BLE001 - Databento 504s: wait and retry
                if k == 3:
                    raise
                print(f"  cost {r}: {str(e)[:80]} - retrying", flush=True); time.sleep(20 * (k + 1))
        cost[r] = c; total += c; print(f"{r:4s} {s}  ${c:8.2f}", flush=True)
    print(f"TOTAL quoted cost: ${total:.2f} (limit ${a.max_cost:.2f})")
    if not cost or total > a.max_cost:
        print("Nothing downloaded (above the limit, the limit is 0 = cost check only, or nothing new)."); return
    OUT.mkdir(parents=True, exist_ok=True)
    for r in cost:
        df = client.timeseries.get_range(dataset=DATASET, start=START, end=END, symbols=syms[r], schema=SCHEMA, stype_in="continuous").to_df()
        df = df.reset_index()[["ts_event", "symbol", "open", "high", "low", "close", "volume", "instrument_id"]]
        df.to_parquet(OUT / f"{r}_1h.parquet", index=False, compression="zstd"); print(f"{r}: {len(df)} rows", flush=True)
    print("Done.")


if __name__ == "__main__":
    main()
