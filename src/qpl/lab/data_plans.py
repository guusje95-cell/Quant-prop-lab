"""One-click download plans for the user's PC (the research cloud cannot reach these sites).

    python -m qpl.lab.data_plans dukascopy-hourly              # all 35 instruments hourly 2013-today (fast: 1 request per month)
    python -m qpl.lab.data_plans dukascopy --priority 1        # 1-minute 2018-today for US100 US500 US30 DE40 gold EURUSD (slow: Dukascopy throttles)
    python -m qpl.lab.data_plans dukascopy --priority 2 / 3     # more instruments (run overnight; resumable)
    python -m qpl.lab.data_plans dukascopy-spread               # ASK candles 2023+ for the priority-1 set -> real spreads
    python -m qpl.lab.data_plans databento                      # DRY RUN: prints the exact cost of every item, downloads nothing
    python -m qpl.lab.data_plans databento --go --budget 100    # downloads in priority order while the total stays <= budget

Everything is written twice: full resolution to data/lab/ (for the Backtest Lab on your PC, not committed) and a compact pack to
research_data/ (5-minute / hourly / daily, float32, zstd) that you commit and push so Claude can use it."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from qpl.lab import download as DL
from qpl.lab.data import LAB, ROOT

DUKA_PLAN = {
    1: ["US100", "US500", "US30", "DE40", "XAUUSD", "EURUSD"],
    2: ["US2000", "UK100", "JP225", "EU50", "FR40", "XAGUSD", "WTI", "BRENT", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF",
        "BTCUSD", "ETHUSD"],
    3: ["AUS200", "HK50", "CH20", "ES35", "NATGAS", "COPPER", "BUND", "USTBOND", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP", "EURCHF", "AUDJPY"],
}
DUKA_START = {"BTCUSD": "2017-05-01", "ETHUSD": "2017-12-01"}

GLBX_START = "2010-06-06"
DATABENTO_PLAN = [   # (priority, roots, schema, roll, ranks, start)
    (1, ["ES", "NQ", "YM", "RTY", "GC", "CL", "ZN", "6E"], "ohlcv-1m", "v", [0], GLBX_START),
    (2, ["CL", "NG", "RB", "HO", "GC", "SI", "HG", "PL", "PA", "ZC", "ZS", "ZW", "ZL", "ZM", "KE", "LE", "HE", "GF",
         "ES", "NQ", "YM", "RTY", "ZT", "ZF", "ZN", "ZB", "6E", "6J", "6B", "6A", "6C", "6S"], "ohlcv-1d", "c", [0, 1, 2], GLBX_START),
    (3, ["SI", "HG", "NG", "ZB", "ZF", "6J", "6B", "6A"], "ohlcv-1m", "v", [0], GLBX_START),
    (3, ["BTC", "MBT"], "ohlcv-1m", "v", [0], "2017-12-17"),
    (3, ["ETH"], "ohlcv-1m", "v", [0], "2021-02-08"),
    (4, ["ES", "NQ", "GC", "CL"], "tbbo", "v", [0], "2026-09-01"),
]


def _pack(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    d = df.set_index("time")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return d[list(agg)].resample(rule).agg(agg).dropna(subset=["close"]).astype("float32")


def dukascopy_hourly(start: str = "2013-01-01"):
    """All 35 instruments, hourly, 2013-today: one request per month, the fast first pass."""
    out = ROOT / "research_data" / "dukascopy"; out.mkdir(parents=True, exist_ok=True)
    for pr in (1, 2, 3):
        for sym in DUKA_PLAN[pr]:
            f = out / f"{sym}_1h.parquet"
            if f.exists():
                print(sym, "hourly already done"); continue
            try:
                df = DL.duka_hourly(sym, DUKA_START.get(sym, start))
                df.set_index("time").astype("float32").to_parquet(f, compression="zstd")
                print(sym, "hourly:", len(df), "bars", df.time.min(), "..", df.time.max(), flush=True)
            except Exception as e:
                print(sym, "FAILED:", e, flush=True)
    print("pack ->", out)


def dukascopy(priority: int, start: str = "2018-01-01"):
    """Priority 1: 1-minute data (needed for intraday tests). Priorities 2-3: hourly data (one request per month, minutes per
    instrument) - enough for session, trend and fix tests; 1-minute for those can be added later if a test needs it."""
    out = ROOT / "research_data" / "dukascopy"; out.mkdir(parents=True, exist_ok=True)
    for sym in DUKA_PLAN[priority]:
        try:
            if priority == 1:
                df = DL.dukascopy(sym, DUKA_START.get(sym, start))
                DL.save({sym: df}, f"dukascopy_{sym}_1m", "1m")
                _pack(df, "5min").to_parquet(out / f"{sym}_5m.parquet", compression="zstd")
                _pack(df, "1h").to_parquet(out / f"{sym}_1h.parquet", compression="zstd")
            else:
                df = DL.duka_hourly(sym, DUKA_START.get(sym, start))
                df.set_index("time").astype("float32").to_parquet(out / f"{sym}_1h.parquet", compression="zstd")
        except Exception as e:
            print(sym, "FAILED:", e, flush=True); continue
        print(sym, "done:", len(df), "bars", df.time.min(), "..", df.time.max(), flush=True)
    print("pack ->", out, "(commit: git add research_data && git commit -m 'Dukascopy data' && git push)")


def dukascopy_spread(start: str = "2025-01-01"):
    """ASK candles (2025+) for the priority-1 set; writes a small table of the bid/ask spread (bp) by year and UTC hour."""
    out = ROOT / "research_data" / "dukascopy"; out.mkdir(parents=True, exist_ok=True)
    rows = []
    for sym in DUKA_PLAN[1]:
        try:
            ask = DL.dukascopy(sym, start, side="ASK"); bid = DL.dukascopy(sym, start)
        except Exception as e:
            print(sym, "FAILED:", e, flush=True); continue
        m = bid.merge(ask, on="time", suffixes=("_b", "_a"))
        sp = (m.close_a - m.close_b) / m.close_b * 1e4
        g = pd.DataFrame({"year": m.time.dt.year, "hour": m.time.dt.hour, "spread_bp": sp})
        t = g.groupby(["year", "hour"]).spread_bp.agg(["median", "mean", lambda x: x.quantile(0.9)]).reset_index()
        t.columns = ["year", "hour_utc", "median_bp", "mean_bp", "p90_bp"]; t["symbol"] = sym; rows.append(t)
        print(sym, "median spread", round(float(sp.median()), 2), "bp", flush=True)
    if rows:
        pd.concat(rows).to_csv(out / "spreads_by_hour.csv", index=False)
        print("spread table ->", out / "spreads_by_hour.csv")


def databento(go: bool, budget: float):
    client = DL.databento_client()
    items = []
    for prio, roots, schema, roll, ranks, start in DATABENTO_PLAN:
        for r in roots:
            for k in ranks:
                q = DL.databento_query(r, start=start, roll=roll, rank=k, schema=schema)
                try:
                    cost = float(client.metadata.get_cost(**q))
                except Exception as e:
                    print(f"  {r}.{roll}.{k} {schema}: cost check failed ({e})"); continue
                items.append((prio, r, schema, roll, k, start, cost))
    items.sort(key=lambda x: x[0])
    total = 0.0; chosen = []
    print(f"{'prio':>4} {'symbol':>10} {'schema':>9} {'from':>11} {'cost $':>8} {'running $':>10}")
    for it in items:
        ok = total + it[6] <= budget
        if ok:
            total += it[6]; chosen.append(it)
        print(f"{it[0]:>4} {it[1] + '.' + it[3] + '.' + str(it[4]):>10} {it[2]:>9} {it[5]:>11} {it[6]:8.2f} {total:10.2f} {'' if ok else '  (skipped: over budget)'}")
    print(f"total selected ${total:.2f} of budget ${budget:.2f}")
    if not go:
        print("dry run only. To download: python -m qpl.lab.data_plans databento --go --budget", budget); return
    out = ROOT / "research_data" / "databento"; out.mkdir(parents=True, exist_ok=True)
    for prio, r, schema, roll, k, start, cost in chosen:
        name = f"{r}_{roll}{k}_{schema}"
        try:
            df = DL.databento(r, start=start, max_usd=cost + 0.5, roll=roll, rank=k, schema=schema, client=client)
        except Exception as e:
            print(name, "FAILED:", e, flush=True); continue
        if schema == "ohlcv-1m":
            DL.save({r: df}, f"databento_{r}_1m", "1m")
            _pack(df, "5min").to_parquet(out / f"{r}_5m.parquet", compression="zstd")
        elif schema == "ohlcv-1d":
            df.set_index("time").astype("float32").to_parquet(out / f"{name}.parquet", compression="zstd")
        else:
            df.to_parquet(out / f"{name}.parquet", compression="zstd")
        print(name, "saved", len(df), "rows", flush=True)
    print("pack ->", out, "(commit: git add research_data && git commit -m 'Databento data' && git push)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["dukascopy", "dukascopy-hourly", "dukascopy-spread", "databento"])
    ap.add_argument("--priority", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--go", action="store_true", help="databento: actually download (default is a dry run that only prints costs)")
    ap.add_argument("--budget", type=float, default=100.0, help="databento: maximum total estimated cost in USD (free credit is $125)")
    a = ap.parse_args()
    if a.what == "dukascopy":
        dukascopy(a.priority)
    elif a.what == "dukascopy-hourly":
        dukascopy_hourly()
    elif a.what == "dukascopy-spread":
        dukascopy_spread()
    else:
        databento(a.go, a.budget)


if __name__ == "__main__":
    main()
