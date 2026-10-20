"""Gen137 (config/gen137_protocol.json): crypto sleeves executed on CME BTC/ETH futures. Writes results/gen137.csv and
results/gen137_hourly.parquet (variant b sleeve P&L)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, B, per, sh = (g[k] for k in ("CS", "B", "per", "sh"))
sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
import cfd_book as CB
END = "2026-09-30"; HIDX = CS._hourly_close(["BTC"]).loc[:END + " 23:00"].index


def d2h(w):
    w = w.reindex(columns=["BTC", "ETH"]).fillna(0.0)
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)])))
    return w.shift(1).reindex(HIDX.floor("D")).set_axis(HIDX).fillna(0.0)


_, tp = CS.trend4h(positions=True); _, wp = CS.weiss_expiry(positions=True)
P = pd.read_parquet(ROOT / "results/gen108_preds.parquet"); wml = P.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
SLEEVES = {"S1 trend 4h": tp.reindex(index=HIDX, columns=["BTC", "ETH"]).fillna(0.0),
           "S2 deleveraging bounce": d2h(CS.delev_bounce_weights()),
           "S3 Coinbase premium": d2h(CB.coinbase_premium_w(pd.Timestamp(END + " 23:00"))),
           "S4 Weiss expiry": wp.reindex(index=HIDX, columns=["BTC", "ETH"]).fillna(0.0),
           "S5 ridge ML": d2h(wml),
           "S6 C* BTC/ETH legs": d2h(CS.cstar_weights()[["BTC", "ETH"]])}
CME = {c: F.front(c).loc[:END + " 23:00"] for c in ("BTC", "ETH")}


def execute(target, variant):
    out = []
    for c in ("BTC", "ETH"):
        f = CME[c]; idx = f.index; tgt = target[c].reindex(idx).fillna(0.0).to_numpy()
        gap_before = np.r_[np.inf, np.diff(idx.asi8) / 3.6e12]               # hours since the previous CME bar
        gap_after = np.r_[np.diff(idx.asi8) / 3.6e12, np.inf]
        if variant in ("b", "c"):
            tgt = np.where(gap_after > 3, 0.0, tgt)                           # flat into weekends / long closures
        if variant == "c":
            et = idx.tz_localize("UTC").tz_convert("America/New_York").hour
            tgt = np.where(et == 16, 0.0, tgt)                                # Topstep: flat by 15:10 CT, i.e. the 16:00 ET bar
        held = tgt.copy()
        held[1:] = np.where(gap_before[1:] > 1.01, held[:-1], tgt[1:])        # the gap is earned with the position held into it
        held = pd.Series(held, index=idx); c_ = F.cost_frac(c, f.close)
        pnl = held * f.r - held.diff().abs().fillna(held.abs()) * c_ - held.abs() * f.roll * 2 * c_
        out.append(pnl)
    return pd.concat(out, axis=1).fillna(0.0).sum(axis=1).reindex(HIDX).fillna(0.0)


rows, keep = [], {}
for name, tgt in SLEEVES.items():
    r = {"sleeve": name}
    for v in ("a", "b", "c"):
        p = execute(tgt, v); k = per(p, "2020-01-01"); r[f"{v} D/T/H"] = np.round(k, 3).tolist()
        if v == "b":
            keep[name] = p; r["pass (b)"] = bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3)
    rows.append(r); print(r, flush=True)
passed = [r["sleeve"] for r in rows if r["pass (b)"]]
if len(passed) >= 2:
    H = pd.DataFrame({k: keep[k] for k in passed})
    for name, var in (("book (b) weekend-flat", "b"), ("book (c) Topstep", "c")):
        Hv = H if var == "b" else pd.DataFrame({k: execute(SLEEVES[k], "c") for k in passed})
        bk = CS.portfolio_v5(Hv)[0]
        r = {"sleeve": name + " of " + ", ".join(passed), "b D/T/H": np.round(per(bk, "2022-01-01"), 3).tolist(),
             "2022-26": round(sh(bk, "2022-01-01", "2026-09-30"), 3)}
        rows.append(r); print(r, flush=True)
        if var == "b":
            bk.to_frame("book").to_parquet(ROOT / "results/gen137_book.parquet")
pd.DataFrame(rows).to_csv(ROOT / "results/gen137.csv", index=False)
pd.DataFrame(keep).to_parquet(ROOT / "results/gen137_hourly.parquet")
