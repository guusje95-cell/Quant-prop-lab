"""FPA-4c (descriptive, 0 trials): is the FPA-4 'overnight' return real on CME futures TRADE prices (Databento GC / SI hourly, front
contract per hour = the symbol with the most hourly bars that day... simplified: the most-traded symbol of each day by bar count),
or only in the Dukascopy BID quotes? Long from the 16:00 ET bar close (last price before the 17:00 break) or the 18:00 / 19:00 ET bar
close, to the 07:00 ET bar close (= 08:00). Writes results/v99/fpa4c_futures_check.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]


def front(sym):
    x = pd.read_parquet(ROOT / f"research_data/databento/{sym}_1h.parquet")
    x = x[~x["symbol"].astype(str).str.contains("-")]                      # outright contracts only (no spreads)
    t = pd.to_datetime(x["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None); x = x.assign(t=t)
    x["day"] = x.t.dt.normalize()
    main = x.groupby(["day", "symbol"]).size().reset_index().sort_values(0).drop_duplicates("day", keep="last").set_index("day")["symbol"]
    x = x[x.symbol.values == main.reindex(x.day).values]
    return x.set_index("t")["close"].astype(float).sort_index()


def leg(c, start, end_h=7):
    out = {}
    for d in pd.bdate_range("2013-01-02", "2026-09-30"):
        a_t = d - pd.Timedelta(hours=24 - start); b_t = d + pd.Timedelta(hours=end_h)
        if a_t in c.index and b_t in c.index:
            out[d] = c[b_t] / c[a_t] - 1 - 2e-4
    return pd.Series(out)


def main():
    out = {}
    for s in ("GC", "SI"):
        c = front(s); c = c[~c.index.duplicated(keep="last")]
        f = lambda z, a, b: round(float(z.loc[a:b].mean() / z.loc[a:b].std() * np.sqrt(252)), 2) if len(z.loc[a:b]) > 50 else None
        out[s] = {f"from the {h}:00 bar close": {"n": int(len(leg(c, h))), "2013-17 / 18-22 / 23-26": [f(leg(c, h), "2013", "2017"), f(leg(c, h), "2018", "2022"), f(leg(c, h), "2023", "2026")]}
                  for h in (16, 18, 19)}
        print(s, out[s], flush=True)
    (ROOT / "results/v99/fpa4c_futures_check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
