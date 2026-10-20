"""Free CBOE volatility index histories (VIX, VIX3M, VIX9D, VXN, VVIX) for the variance-risk-premium research (Gen179+).
Run on your PC (the research container cannot reach cboe.com):  python -m qpl.live.vix_data
Writes research_data/more2/vix_<name>.parquet with columns open/high/low/close indexed by date."""
import io
import sys
import urllib.request
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parents[3] / "research_data/more2"
URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"
NAMES = ["VIX", "VIX3M", "VIX9D", "VXN", "VVIX"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for n in NAMES:
        try:
            req = urllib.request.Request(URL.format(n), headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=60).read().decode()
            d = pd.read_csv(io.StringIO(raw)); d.columns = [c.strip().lower() for c in d.columns]
            d["date"] = pd.to_datetime(d["date"]); d = d.set_index("date").sort_index()
            d.to_parquet(OUT / f"vix_{n}.parquet"); print(n, len(d), d.index.min().date(), d.index.max().date())
        except Exception as e:                                       # one failing index should not stop the others
            print(n, "FAILED:", e, file=sys.stderr)


if __name__ == "__main__":
    main()
