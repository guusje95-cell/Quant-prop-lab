"""COST QUOTE ONLY (downloads nothing, costs nothing) for CME options data from Databento, for the futures programme track 3
(option skew / positioning signals). Prints a table of quoted costs per product, schema and period so the user can decide.

    python -m qpl.live.databento_options_quote

The API key is read from the DATABENTO_API_KEY environment variable only (typed into get_options_quote.bat, never saved).
What the schemas give:
  definition  - every option contract: strike, expiry, put/call (needed to compute implied volatility and skew)
  statistics  - daily settlement price and open interest per contract (enough for daily skew and positioning)
  ohlcv-1d    - daily OHLCV per contract (traded prices; thinner for far strikes)
The result is written to research_data/databento_options_quote.csv so Claude can read it after a push."""
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATASET = "GLBX.MDP3"
PRODUCTS = {"ES.OPT": "E-mini S&P 500 options (standard)", "NQ.OPT": "E-mini Nasdaq-100 options", "OZN.OPT": "10-year T-note options",
            "LO.OPT": "WTI crude options", "OG.OPT": "gold options"}
SCHEMAS = ["definition", "statistics", "ohlcv-1d"]
PERIODS = {"2010-2026": ("2010-06-06", "2026-10-01"), "2018-2026": ("2018-01-01", "2026-10-01")}


def main():
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Set DATABENTO_API_KEY first (get_options_quote.bat asks for it). Do not paste the key anywhere else.")
    import databento as db
    client = db.Historical(key)
    rows = []
    for sym, name in PRODUCTS.items():
        for sch in SCHEMAS:
            for per, (s, e) in PERIODS.items():
                c = None; err = ""
                for k in range(3):
                    try:
                        c = float(client.metadata.get_cost(dataset=DATASET, start=s, end=e, symbols=[sym], schema=sch, stype_in="parent")); break
                    except Exception as ex:                                     # noqa: BLE001 - report, do not stop
                        err = str(ex)[:120]; time.sleep(5 * (k + 1))
                rows.append({"product": sym, "name": name, "schema": sch, "period": per, "usd": round(c, 2) if c is not None else None, "error": err if c is None else ""})
                print(f"{sym:8s} {sch:11s} {per}: " + (f"${c:,.2f}" if c is not None else f"no quote ({err})"), flush=True)
    df = pd.DataFrame(rows); out = ROOT / "research_data" / "databento_options_quote.csv"; df.to_csv(out, index=False)
    ok = df.dropna(subset=["usd"])
    if len(ok):
        print("\nCheapest useful set (definition + statistics) per product, 2018-2026:")
        sub = ok[(ok.schema.isin(["definition", "statistics"])) & (ok.period == "2018-2026")].groupby("product").usd.sum()
        print(sub.to_string()); print(f"All five products, 2018-2026: ${sub.sum():,.2f}")
    print(f"\nSaved {out}. Nothing was downloaded or charged.")


if __name__ == "__main__":
    main()
