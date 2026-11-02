"""CME-B (research/v99/cmeb_protocol.json): CME bitcoin basis level, contrarian, on BTC/ETH. Writes results/v99/cmeb_basis.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
from qpl.live import cfd_extra as X


def last_friday(y, m):
    d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
    while d.weekday() != 4:
        d -= pd.Timedelta(days=1)
    return d + pd.Timedelta(hours=15)


def basis():
    x = pd.read_parquet(ROOT / "research_data/databento/BTC_1h.parquet"); x["t"] = pd.to_datetime(x.ts_event, utc=True).dt.tz_localize(None)
    f0 = x[x.symbol.astype(str) == "BTC.v.0"].set_index("t")["close"].astype(float).sort_index()
    f1 = x[x.symbol.astype(str) == "BTC.v.1"].set_index("t")["close"].astype(float).sort_index()
    spot = B.k5("BTC").close.resample("1h").last()
    out = {}
    for d in pd.date_range("2021-01-01", "2026-09-30"):
        t = d - pd.Timedelta(hours=1)
        exp = last_friday(d.year, d.month); use1 = (exp - d) < pd.Timedelta(days=5)
        if use1:
            exp = last_friday((d + pd.offsets.MonthBegin(1)).year, (d + pd.offsets.MonthBegin(1)).month)
        f = (f1 if use1 else f0).loc[:t]; s = spot.loc[:t]
        if len(f) and len(s) and (t - f.index[-1]) <= pd.Timedelta(hours=72) and (t - s.index[-1]) <= pd.Timedelta(hours=2):
            days = max((exp - d).total_seconds() / 86400, 1.0)
            out[d] = (f.iloc[-1] / s.iloc[-1] - 1) * 365 / days
    return pd.Series(out)


def main():
    b = basis(); z = ((b - b.rolling(90, min_periods=60).mean()) / b.rolling(90, min_periods=60).std()).clip(-2, 2)
    w = pd.DataFrame({c: -0.15 * z / 2 for c in ("BTC", "ETH")}).fillna(0.0)                   # row d decided at 00:00 of d -> held during d
    w.index = w.index - pd.Timedelta(days=1)                                                     # book convention: row d-1 held during d
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    perp = CS._from_daily_weights(w, ["BTC", "ETH"], 5).reindex(idx).fillna(0.0)
    unit = lambda x: x * 0.15 / (C.dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    full = C.full; ref = full(unit(CS.portfolio_v5(V8)[0])); r = full(unit(CS.portfolio_v5(V8.assign(**{"CME basis": perp}))[0]))
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); bidx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", bidx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(bidx).fillna(0.0) for k, v in S.items()})
    days = w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))
    pos = w.reindex(days).shift(1).reindex(bidx.floor("D")).set_axis(bidx).fillna(0.0)
    R = B.panel("close", "1h", ["BTC", "ETH"]).pct_change(fill_method=None).reindex(bidx).fillna(0.0)
    cfd = X.cfd_pnl(pos, R, X.costs(["BTC", "ETH"]))
    rc_ref = full(C.book(base)); rc = full(C.book(base.assign(**{"CME basis CFD": cfd})))
    beats = lambda a, b_: bool(a[0] >= b_[0] + 0.05 and all(a[1][i] >= b_[1][i] for i in range(3)))
    out = {"basis days": int(b.notna().sum()), "basis mean / sd (annualised)": [round(float(b.mean()), 3), round(float(b.std()), 3)],
           "sleeve (perp)": full(perp), "crypto v9.8": [ref, r], "pass crypto": beats(r, ref), "sleeve (CFD)": full(cfd), "bf2.7": [rc_ref, rc], "pass CFD": beats(rc, rc_ref)}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/cmeb_basis.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
