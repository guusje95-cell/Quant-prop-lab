"""Gen114 T1-T4 (config/gen114_protocol.json): futures trend+carry and Topstep-compatible session trades on Databento CME hourly.
Writes results/gen114_futures.csv and results/gen114_t1_daily.parquet (T1 daily P&L for the book / correlation checks)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F

EW = {(16, 64): 3.75, (32, 128): 2.65, (64, 256): 1.87}          # Carver forecast scalars
roots = [r for r in F.NONCRYPTO if (F.DB / f"{r}_1h.parquet").exists()]
D = {r: F.daily(r) for r in roots}
R = pd.DataFrame({r: D[r].r for r in roots}).sort_index()
idx = R.index


def forecasts(r):
    d = D[r]; px = (1 + d.r).cumprod()
    sd = d.r.ewm(span=35, min_periods=30).std()                   # daily return vol
    tr = sum((px.ewm(span=f).mean() - px.ewm(span=s).mean()) / (px * sd) * k for (f, s), k in EW.items()) / len(EW)
    carry = (d.close / d.close2 - 1) / F.SPEC[r][3]
    ca = (carry / (sd * np.sqrt(256))) * 30
    return tr.clip(-20, 20), ca.clip(-20, 20), sd


TR, CA, SD = {}, {}, {}
for r in roots:
    TR[r], CA[r], SD[r] = forecasts(r)
TR, CA, SD = (pd.DataFrame(x).reindex(idx) for x in (TR, CA, SD))
FC = (0.6 * TR + 0.4 * CA.fillna(0.0)).clip(-20, 20)
COST = pd.DataFrame({r: D[r].cost for r in roots}).reindex(idx).ffill()
ROLL = pd.DataFrame({r: D[r].roll for r in roots}).reindex(idx).fillna(0)


def book_daily(fc, members, vol=0.15):
    """Equal risk per instrument, portfolio scaled to `vol` with trailing 60-day realised vol (decided the day before)."""
    n = fc[members].notna().sum(axis=1).clip(lower=1)
    pos = (fc[members] / 10) * (vol / (SD[members] * np.sqrt(256))).div(np.sqrt(n), axis=0)
    pos = pos.fillna(0.0)
    held = pos.shift(1).fillna(0.0)                                  # decided at the close of d-1, held during d
    gross = (held * R[members].fillna(0.0)).sum(axis=1)
    lvl = (vol / (gross.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1).fillna(1.0)
    held = held.mul(lvl, axis=0)
    turn = held.diff().abs().fillna(held.abs()) + 2 * held.abs() * ROLL[members]
    pnl = (held * R[members].fillna(0.0)).sum(axis=1) - (turn * COST[members]).sum(axis=1)
    return pnl, held


rows = []


def report(name, pnl, extra=None):
    k = F.splits(pnl); r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": F.passes(k), **(extra or {})}
    rows.append(r); print(r, flush=True)


# T1
t1, held1 = book_daily(FC, roots)
report("T1 trend+carry multi-day (24 roots)", t1)
t1.to_frame("pnl").to_parquet(ROOT / "results/gen114_t1_daily.parquet")
# T1 at $100k with whole micro (or full) contracts: report only
eq = 100_000; px = pd.DataFrame({r: D[r].close for r in roots}).reindex(idx).ffill()
mult = pd.Series({r: (F.SPEC[r][2] or F.SPEC[r][1]) for r in roots})
contracts = (held1 * eq / (px.shift(1) * mult)).round()            # sized at the previous close (known)
heldr = contracts * px.shift(1) * mult / eq
heldr = heldr.fillna(0.0)
turn = heldr.diff().abs().fillna(heldr.abs()) + 2 * heldr.abs() * ROLL
t1r = (heldr * R.fillna(0.0)).sum(axis=1) - (turn * COST).sum(axis=1)
report("T1 at $100k, whole contracts (report only)", t1r, {"mean |contracts|": round(float(contracts.abs().sum(axis=1).mean()), 1)})

# hourly helpers for T2-T4
def hourly(root):
    f = F.front(root); return f, F.ny(f.index)


def run_hourly(name, P, extra=None):
    """P: dict root -> hourly position Series (on that root's front index). Costs per change in position."""
    tot = []
    for r, p in P.items():
        f = F.front(r); p = p.reindex(f.index).fillna(0.0)
        c = F.cost_frac(r, f.close)
        tot.append(p * f.r - p.diff().abs().fillna(p.abs()) * c - p.abs() * f.roll * 2 * c)
    pnl = pd.concat(tot, axis=1).fillna(0.0).sum(axis=1)
    report(name, pnl.groupby(pnl.index.floor("D")).sum(), extra)


# T2 intraday momentum
P = {}
for r in ["ES", "NQ", "RTY", "YM", "GC", "CL", "ZN"]:
    if r not in roots:
        continue
    f, t = hourly(r); px = (1 + f.r).cumprod()
    c15 = px[t.h == 15].groupby(t.date[t.h == 15]).last(); c9 = px[t.h == 9].groupby(t.date[t.h == 9]).last()
    sig = np.sign(c9 / c15.shift(1).reindex(c9.index, method=None) - 1)
    m = t.h == 15; P[r] = pd.Series(0.0, index=f.index); P[r][m] = t.date[m].map(sig).fillna(0.0).to_numpy() * 0.5
run_hourly("T2 intraday momentum (last hour)", P)
# T3 overnight drift
P = {}
for r in ["ES", "NQ"]:
    f, t = hourly(r); m = (t.h >= 18) | (t.h <= 8); P[r] = pd.Series(np.where(m, 0.5, 0.0), index=f.index)
run_hourly("T3 overnight drift ES/NQ", P)
# T4 T1 signal, in-session only (18:00 -> 16:00 ET), flat 16:00-18:00
P = {}
for r in ["ES", "NQ", "ZN", "GC", "CL", "6E"]:
    f, t = hourly(r); dpos = held1[r].reindex(F.trade_date(f.index)).to_numpy()
    P[r] = pd.Series(np.where((t.h == 16) | (t.h == 17), 0.0, dpos), index=f.index).fillna(0.0)
run_hourly("T4 T1 signal in-session only", P)
pd.DataFrame(rows).to_csv(ROOT / "results/gen114_futures.csv", index=False)
