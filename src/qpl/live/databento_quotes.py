"""QUOTE ONLY (downloads nothing, costs nothing): prices of the Databento datasets that could unlock intraday edges.
  python -m qpl.live.databento_quotes        (needs DATABENTO_API_KEY in this window only)"""
import os
import sys
ITEMS = [  # (label, dataset, schema, symbols, stype_in, start, end)
    ("ES+NQ trades with aggressor side (order flow), 2018-2026", "GLBX.MDP3", "trades", ["ES.v.0", "NQ.v.0"], "continuous", "2018-01-01", "2026-10-01"),
    ("ES+NQ trades, 2024-2026 only", "GLBX.MDP3", "trades", ["ES.v.0", "NQ.v.0"], "continuous", "2024-01-01", "2026-10-01"),
    ("ES+NQ top of book + trades (tbbo), 2024-2026", "GLBX.MDP3", "tbbo", ["ES.v.0", "NQ.v.0"], "continuous", "2024-01-01", "2026-10-01"),
    ("ES+NQ 1-second bars, 2018-2026", "GLBX.MDP3", "ohlcv-1s", ["ES.v.0", "NQ.v.0"], "continuous", "2018-01-01", "2026-10-01"),
    ("ES options (all strikes) daily bars, 2018-2026 (for gamma exposure)", "GLBX.MDP3", "ohlcv-1d", ["ES.OPT"], "parent", "2018-01-01", "2026-10-01"),
    ("ES options statistics incl. open interest, 2018-2026 (for gamma exposure)", "GLBX.MDP3", "statistics", ["ES.OPT"], "parent", "2018-01-01", "2026-10-01"),
    ("ES+NQ futures statistics (settlement, open interest, volume), 2010-2026", "GLBX.MDP3", "statistics", ["ES.FUT", "NQ.FUT"], "parent", "2010-06-06", "2026-10-01"),
]


def main():
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (in this window only).")
    import databento as db
    client = db.Historical(key)
    for label, ds, sch, sym, st, a, z in ITEMS:
        try:
            c = client.metadata.get_cost(dataset=ds, schema=sch, symbols=sym, stype_in=st, start=a, end=z)
            print(f"${c:10.2f}  {label}", flush=True)
        except Exception as e:                                  # noqa: BLE001
            print(f"   n/a      {label}: {str(e)[:90]}", flush=True)
    print("Nothing was downloaded. Tell Claude these prices.")


if __name__ == "__main__":
    main()
