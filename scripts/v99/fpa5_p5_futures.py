"""FPA-5 (research/v99/fpa5_protocol.json): P5 on Databento NQ / ES 1-minute trades. Writes results/v99/fpa5_p5_futures.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99"):
    sys.path.insert(0, str(ROOT / p))
import fpa1_price_action as F
import fpa1b_checks as B


def load(f):
    x = pd.read_parquet(ROOT / f"research_data/databento/{f}.parquet")
    x = x[~x["symbol"].astype(str).str.contains("-")]
    t = pd.to_datetime(x["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None); x = x.assign(t=t, day=t.dt.normalize())
    main = x.groupby(["day", "symbol"]).size().reset_index().sort_values(0).drop_duplicates("day", keep="last").set_index("day")["symbol"]
    x = x[x.symbol.values == main.reindex(x.day).values].set_index("t").sort_index()
    x = x[~x.index.duplicated()][["open", "high", "low", "close"]].astype(float)
    return x.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def run(x, a, z):
    s, _ = B.p5(x); bd = pd.bdate_range(a, z); s = s.reindex(bd).fillna(0.0)
    return s


def main():
    out = {}
    for cost in (1e-4, 5e-5):
        F.COST = cost; r = {}
        nq0 = load("NQ_1m_2010_2017"); s = run(nq0, "2010-06-07", "2017-12-29"); r["A NQ 2010-17"] = [F.sharpe(s, "2010", "2013"), F.sharpe(s, "2014", "2017"), F.sharpe(s, "2010", "2017"), int((s != 0).sum())]
        for f in ("NQ_1m", "ES_1m"):
            s = run(load(f), "2018-01-02", "2026-09-30"); r[f"B {f[:2]} 2018-26"] = [F.sharpe(s, "2018", "2022"), F.sharpe(s, "2023", "2026"), F.sharpe(s, "2018", "2026"), int((s != 0).sum())]
        out[f"{cost * 1e4:.1f} bp per side (sub-periods, full, trades)"] = r; print(cost, r, flush=True)
    r = out["1.0 bp per side (sub-periods, full, trades)"]
    out["verdict"] = {"A NQ 2010-17 >= 0.4": bool(r["A NQ 2010-17"][2] is not None and r["A NQ 2010-17"][2] >= 0.4),
                      "B NQ and ES 2018-26 >= 0.3": bool(all(r[k][2] is not None and r[k][2] >= 0.3 for k in ("B NQ 2018-26", "B ES 2018-26")))}
    print(out["verdict"]); (ROOT / "results/v99/fpa5_p5_futures.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
