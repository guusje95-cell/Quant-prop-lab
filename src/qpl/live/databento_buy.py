"""Download named Databento items after showing the exact price (asks for confirmation). Usage:
  python -m qpl.live.databento_buy qqq_imbalance fut_stats           (needs DATABENTO_API_KEY in this window only)
Saves to research_data/databento_extra/<item>.parquet (zstd)."""
import os
import sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[3] / "research_data/databento_extra"
ITEMS = {
    "qqq_imbalance": ("XNAS.ITCH", "imbalance", ["QQQ"], "raw_symbol", "2018-06-01", "2026-10-01"),
    "spy_imbalance": ("ARCX.PILLAR", "imbalance", ["SPY"], "raw_symbol", "2018-06-01", "2026-10-01"),
    "fut_stats": ("GLBX.MDP3", "statistics", ["ES.FUT", "NQ.FUT"], "parent", "2010-06-06", "2026-10-01"),
    "es_opt_stats": ("GLBX.MDP3", "statistics", ["ES.OPT"], "parent", "2018-01-01", "2026-10-01"),
}


def main():
    names = [a for a in sys.argv[1:] if a in ITEMS]
    if not names:
        sys.exit(f"name items to download: {list(ITEMS)}")
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (in this window only).")
    import databento as db
    client = db.Historical(key); OUT.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for n in names:
        ds, sch, sym, st, a, z = ITEMS[n]
        c = client.metadata.get_cost(dataset=ds, schema=sch, symbols=sym, stype_in=st, start=a, end=z); total += c; print(f"{n:15s} ${c:8.2f}")
    if input(f"TOTAL ${total:.2f}. Download? type yes: ").strip().lower() != "yes":
        sys.exit("nothing downloaded")
    for n in names:
        f = OUT / f"{n}.parquet"
        if f.exists():
            print(n, "exists, skipped"); continue
        ds, sch, sym, st, a, z = ITEMS[n]
        for k in range(5):
            try:
                data = client.timeseries.get_range(dataset=ds, schema=sch, symbols=sym, stype_in=st, start=a, end=z); break
            except Exception as e:                                  # noqa: BLE001 (504s happen)
                if k == 4:
                    raise
                import time
                print(" retrying after", str(e)[:60]); time.sleep(30 * (k + 1))
        df = data.to_df().reset_index()
        df.to_parquet(f, index=False, compression="zstd"); print(n, len(df), "rows", round(f.stat().st_size / 1e6, 1), "MB")
    print("done")


if __name__ == "__main__":
    main()
