"""Daily-flat futures paper (DF-1c, corrected 2026-11-03): the 8 equity-index sleeves (P1, R1, T1, T2, FC, MM, OIL, K3) with signals on
the TRUE futures prices and the P&L of a daily-flat account (flat 16:00-18:00 ET and at weekends, session-open gaps not earned, exit /
re-entry costs at every closure), fbook rule (1/sd on 2010-22, 10% vol target). Appends each completed trading day once to
paper_trading/futuresdf2/ledger_hourly.csv. (The first version, paper_trading/futuresdf, computed the signals on the patched bars:
retired, see research/v99/df1c_protocol.json.) Simulation only: no orders, no broker.

    python scripts/futures_paper_dailyflat.py            # append new days (run by futures_paper_update.bat)
    python scripts/futures_paper_dailyflat.py --check    # research data only: must reproduce results/v99/df1c.json"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/v99")); sys.path.insert(0, str(ROOT / "src"))
os.environ["QPL_DAILY_FLAT"] = "1"; os.environ["QPL_DF_SIGNALS"] = "true"
CHECK = "--check" in sys.argv
if not CHECK:
    from qpl.live import databento_update as DU
    os.environ["QPL_DATABENTO"] = str(DU.merged_dir())
import futures_db as F  # noqa: E402

OUT = Path(os.environ.get("QPL_FUT_PAPER_OUT_DF", ROOT / "paper_trading/futuresdf2"))
RESEARCH_END = pd.Timestamp("2026-09-30")


def sleeves(end: str) -> pd.DataFrame:
    F.END = f"{end} 23:00"
    import dailyflat_positions as DP
    pos = DP.session_positions(); H = DP.hourly(pos)
    import dailyflat
    dailyflat.patch()                                                     # P&L on the patched (daily-flat) bars
    out = {}
    for n in DP.EQ8:
        tot = 0.0
        for r in H[n].columns:
            f = F.front(r); idx = f.index; et = F.ny(idx); p = H[n][r].reindex(idx).fillna(0.0).copy()
            p[(et.h == 16).to_numpy()] = 0.0
            gap = np.r_[True, np.diff(idx.asi8) / 3.6e12 > 1.01]
            turn = p.diff().abs().fillna(p.abs()); turn[gap] = (p.abs() + p.shift(1).abs().fillna(0.0))[gap]
            tot = (tot if isinstance(tot, pd.Series) else pd.Series(dtype=float)).add((p * f.r.fillna(0.0) - turn * F.cost_frac(r, f.close)).groupby(F.trade_date(idx)).sum(), fill_value=0.0)   # markets start at different dates (RTY 2017): no NaN days
        out[n] = tot
    Q = pd.DataFrame(out); return Q[Q.index.weekday < 5].loc["2010-06-01":end].fillna(0.0)


def book(Q: pd.DataFrame):
    T = Q.loc[:"2022-12-31"]; w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
    raw = (Q * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna(), pd.DataFrame(np.outer(lvl.fillna(0.0), w), index=Q.index, columns=Q.columns)


def main():
    if CHECK:
        b, _ = book(sleeves(str(RESEARCH_END.date())))
        out = {"splits": [round(F.sharpe(b, *s), 3) for s in F.SPLITS], "df1c": json.loads((ROOT / "results/v99/df1c.json").read_text())[
            "DF-1c corrected (true signals, daily-flat P&L), per-sleeve costs"]}
        print(json.dumps(out)); sys.exit(0 if out["splits"] == out["df1c"] else 1)
    last = pd.to_datetime(pd.read_parquet(F.DB / "ES_1h.parquet", columns=["ts_event"])["ts_event"], utc=True).max().tz_localize(None)
    complete = F.trade_date(pd.DatetimeIndex([last]))[0] - pd.Timedelta(days=1)
    Q = sleeves(str(last.date())); b, W = book(Q)
    f = OUT / "ledger_hourly.csv"; L = pd.read_csv(f) if f.exists() else pd.DataFrame()
    done = pd.to_datetime(L["hour"]).dt.normalize().max() if len(L) else RESEARCH_END
    now = pd.Timestamp.now("UTC").tz_localize(None); rows = []
    for d in b.index[(b.index > done) & (b.index <= complete)]:
        close = d + pd.Timedelta(hours=21); lag = (now - close).total_seconds() / 3600
        r = {"hour": str(close), "port": float(b.loc[d])}
        for c in Q.columns:
            r[c] = float(Q.loc[d, c]); r["w " + c] = float(W.loc[d, c])
        r.update({"computed_at": str(now.floor("s")), "lag_h": round(lag, 1), "late": bool(lag > 30)}); rows.append(r)
    OUT.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.concat([L, pd.DataFrame(rows)], ignore_index=True).to_csv(f, index=False)
    L = pd.read_csv(f) if f.exists() else pd.DataFrame()
    st = {"data_end": str(last), "appended": len(rows), "ledger_days": len(L), "method": "DF-1c (true-price signals, daily-flat P&L)"}
    if len(L) >= 5:
        x = L["port"].astype(float); ref = b.loc["2023-01-01":"2026-09-30"]
        st.update({"paper Sharpe (ann.)": round(float(x.mean() / x.std() * np.sqrt(252)), 2), "paper cum": round(float((1 + x).prod() - 1), 4),
                   "z vs backtest": round(float((x.mean() - ref.mean()) / (ref.std() / np.sqrt(len(x)))), 2)})
    (OUT / "status.json").write_text(json.dumps(st, indent=1)); print(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
