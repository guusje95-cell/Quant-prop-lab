"""Gen88 (config/gen88_protocol.json, registered 2026-10-18 before the data existed): Coinbase premium.
Writes results/gen88.csv and results/cache_gen88_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, B, CFD, fhp, d2h, R1 = ns["CS"], ns["B"], ns["CFD"], ns["from_hourly_pos"], ns["daily_to_hourly"], ns["R1"]
IDX = R1.index; END = "2026-09-30 23:00"


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0)
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


Z, PREM = {}, {}
for c, prod in (("BTC", "BTC-USD"), ("ETH", "ETH-USD")):
    cb = pd.read_parquet(ROOT / f"research_data/coinbase/{prod}_1h.parquet")["close"]
    bn = B.k5(c).close.resample("1h").last()
    prem = (cb / bn - 1).dropna().loc[:END]                     # both indexed by hour start, close = end of the hour
    p24 = prem.rolling(24, min_periods=20).mean()
    m30 = p24.rolling(24 * 30, min_periods=24 * 20).mean(); s30 = p24.rolling(24 * 30, min_periods=24 * 20).std()
    Z[c] = (p24 - m30) / s30; PREM[c] = prem
zd = pd.DataFrame({c: z.resample("1D").last() for c, z in Z.items()})          # value at the 23:00 bar = known at 00:00
print("premium stats (bp): ", {c: (round(p.median() * 1e4, 1), round(p.quantile(0.01) * 1e4, 1), round(p.quantile(0.99) * 1e4, 1)) for c, p in PREM.items()}, flush=True)
print("hours with premium:", {c: len(p) for c, p in PREM.items()}, flush=True)


def q1(th):
    w = pd.DataFrame(0.0, index=zd.index, columns=CFD)
    for c in ("BTC", "ETH"):
        w[c] = np.where(zd[c] > th, 0.5, np.where(zd[c] < -th, -0.5, 0.0))
    return fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0), w


C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet").reindex(IDX).fillna(0.0)
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"]}
G90 = {**BASE, "delev bounce": fhp(d2h(CS.delev_bounce_weights().reindex(columns=CFD).fillna(0.0)), 3.3).reindex(IDX).fillna(0.0)}
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
B0 = dsh(bk(BASE), "2022-01-01", "2026-09-30"); B90 = dsh(bk(G90), "2022-01-01", "2026-09-30")
print("Gen85 book", round(B0, 3), "| Gen90 book (info)", round(B90, 3), flush=True)
per = lambda h: (dsh(h, "2020-01-01", "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"))
ROWS, CANDS = [], {}
cst = BASE["C*"].groupby(IDX.floor("D")).sum()
for th, nm, prim in ((1.0, "Q1 premium momentum z>1 (PRIMARY)", True), (0.5, "Q3 variant z>0.5", False)):
    h, w = q1(th); p = per(h); bA = dsh(bk({**BASE, nm: h}), "2022-01-01", "2026-09-30")
    r = {"test": nm, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "days long": int((w[["BTC", "ETH"]] > 0).sum().sum()), "days short": int((w[["BTC", "ETH"]] < 0).sum().sum()),
         "corr C*": float(pd.concat([cst, h.groupby(IDX.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]),
         "book before": B0, "book after": bA, "Gen90 book after (info)": dsh(bk({**G90, nm: h}), "2022-01-01", "2026-09-30")}
    r["pass"] = bool(prim and p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and bA > B0)
    ROWS.append(r); CANDS[nm] = h; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
# Q2 C* filter
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0; a = cw.abs(); m = a.where(a > 0).mean(axis=1); cw = cw.where(a.ge(m * 0.5, axis=0), 0.0)
f = pd.Series(np.where(zd["BTC"] > 0, 1.25, np.where(zd["BTC"] <= 0, 0.75, 1.0)), index=zd.index).reindex(cw.index).fillna(1.0)
h2 = fhp(d2h(cw.mul(f, axis=0)), 3.3).reindex(IDX).fillna(0.0); p2 = per(h2); pc = per(BASE["C*"])
bA = dsh(bk({**BASE, "C*": h2}), "2022-01-01", "2026-09-30")
r = {"test": "Q2 C* premium filter (PRIMARY)", "DEV": p2[0], "TEST": p2[1], "HOLD": p2[2], "C* DEV": pc[0], "C* TEST": pc[1], "C* HOLD": pc[2],
     "book before": B0, "book after": bA, "Gen90 book after (info)": dsh(bk({**G90, "C*": h2}), "2022-01-01", "2026-09-30")}
r["pass"] = bool(all(x > y for x, y in zip(p2, pc)) and bA > B0)
ROWS.append(r); CANDS[r["test"]] = h2; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen88_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen88.csv", index=False)
print("done", flush=True)
