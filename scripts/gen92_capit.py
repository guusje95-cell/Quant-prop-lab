"""Gen92 (config/gen92_protocol.json): capitulation family. Writes results/gen92.csv and results/cache_gen92_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen91_oi.py")}
exec(open(ROOT / "scripts/gen91_oi.py").read().split("ALTS = [c for c")[0], g)
CS, B, CFD, fhp, d2h, IDX, dsh, bk, BASE, B0, cst = (g[k] for k in ("CS", "B", "CFD", "fhp", "d2h", "IDX", "dsh", "bk", "BASE", "B0", "cst"))
ROWS, CANDS = [], {}
P = B.panel("close", "1D", ["BTC", "ETH"]).loc[:"2026-09-30"]; R = P.pct_change(fill_method=None)
QV = B.panel("quote_volume", "1D", ["BTC", "ETH"]).loc[:"2026-09-30"]


def hold_w(sig, hold=2, size=0.5):
    return sig.astype(float).rolling(hold, min_periods=1).max() * size


def report(name, h, dev=("2020-01-01", "2022-12-31"), test=("2023-01-01", "2024-12-31"), hold=("2025-01-01", "2026-09-30"), extra=None):
    bA = dsh(bk({**BASE, name: h}), "2022-01-01", "2026-09-30"); hd = h.groupby(h.index.floor("D")).sum()
    r = {"test": name, "DEV": dsh(h, *dev), "TEST": dsh(h, *test), "HOLD": dsh(h, *hold), "2022-26": dsh(h, "2022-01-01", "2026-09-30"),
         "corr C*": float(pd.concat([cst, hd], axis=1).loc["2022":].corr().iloc[0, 1]), "book before": B0, "book after": bA, **(extra or {})}
    r["pass"] = bool("variant" not in name and r["DEV"] > 0 and r["TEST"] >= 0.5 and r["HOLD"] >= 0.3 and bA > B0)
    ROWS.append(r); CANDS[name] = h; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


# L1 DVOL spike
w = pd.DataFrame(0.0, index=P.index, columns=CFD)
for c in ("BTC", "ETH"):
    dv = pd.read_parquet(ROOT / f"data/raw/deribit/{c}_DVOL.parquet")["close"]; dv.index = pd.DatetimeIndex(dv.index).tz_localize(None).normalize()
    dv = dv.reindex(P.index)
    w[c] = hold_w((dv / dv.shift(1) - 1 > 0.10) & (R[c] < 0)).to_numpy()
report("L1 DVOL spike bounce (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), extra={"signals": int(((w > 0) & (w.shift(1) == 0)).sum().sum())})

# L2 volume capitulation
w = pd.DataFrame(0.0, index=P.index, columns=CFD)
for c in ("BTC", "ETH"):
    w[c] = hold_w((QV[c] > 3 * QV[c].shift(1).rolling(30).mean()) & (R[c] < 0)).to_numpy()
report("L2 volume capitulation bounce (PRIMARY)", fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), extra={"signals": int(((w > 0) & (w.shift(1) == 0)).sum().sum())})

# L3 VIX term structure
vix = pd.read_parquet(ROOT / "data/raw/yahoo/VIX.parquet")["close"]; v3 = pd.read_parquet(ROOT / "data/raw/yahoo/VIX3M.parquet")["close"]
ratio = (vix / v3).dropna(); ratio.index = pd.DatetimeIndex(ratio.index).normalize()
IX = {}
for s in ("US500", "US100"):
    x = pd.read_parquet(ROOT / f"research_data/dukascopy/{s}_1h.parquet").astype("float64"); x = x[~x.index.duplicated()].sort_index()
    IX[s] = x.open
HIDX = pd.date_range("2018-01-01", "2026-09-30 23:00", freq="1h")


def l3(th):
    bd = ratio.index                                                         # US trading days
    pos = pd.Series(0.0, index=HIDX)
    for i, d in enumerate(bd[:-4]):
        if ratio.iloc[i] > th:
            t0 = bd[i + 1] + pd.Timedelta(hours=14); t1 = bd[min(i + 4, len(bd) - 1)] + pd.Timedelta(hours=14)
            pos.loc[t0:t1 - pd.Timedelta(hours=1)] = 1.0
    out = pd.Series(0.0, index=HIDX)
    for s, o in IX.items():
        o = o.reindex(HIDX).ffill(); r = o.shift(-1) / o - 1                 # hourly return from this bar's open to the next
        out += 0.5 * (pos * r.fillna(0.0) - pos.diff().abs().fillna(0.0) * 1.0 / 1e4 - pos * 0.03 / (365 * 24))
    return out.shift(1).fillna(0.0)                                          # book each hour's P&L at its end


def l3_yahoo(th):
    us = pd.read_parquet(ROOT / "data/raw/yahoo/US500.parquet")["close"]; us.index = pd.DatetimeIndex(us.index).normalize()
    rr = ratio.reindex(us.index); sig = (rr > th).astype(float)
    held = sig.shift(1).rolling(3, min_periods=1).max().fillna(0.0)            # enter next close, 3 days (conservative close-to-close)
    pnl = held.shift(1) * us.pct_change() - held.diff().abs() * 1e-4
    x = pnl.loc["2007":"2017"].dropna(); return float(x.mean() / x.std() * np.sqrt(252)), int((sig.loc["2007":"2017"]).sum())


for th, nm in ((1.0, "L3 VIX/VIX3M > 1.0 panic bounce, US500+US100 (PRIMARY)"), (1.05, "L3 variant ratio > 1.05")):
    h = l3(th); pre, ns_ = l3_yahoo(th)
    report(nm, h.reindex(IDX.union(HIDX)).fillna(0.0), dev=("2018-01-01", "2020-12-31"), test=("2021-01-01", "2023-12-31"), hold=("2024-01-01", "2026-09-30"),
           extra={"pre-check 2007-17 Sharpe (Yahoo daily)": pre, "signal days 2007-17": ns_, "signal days 2018-26": int((ratio.loc["2018":] > th).sum())})
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen92_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen92.csv", index=False)
print("done", flush=True)
