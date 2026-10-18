"""Gen85 (config/gen85_protocol.json): CFD-book improvements. Reuses the Gen74 builders.
Writes results/gen85.csv and results/cache_gen85_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, CFD, END, fhp, d2h = ns["CS"], ns["CFD"], ns["END"], ns["from_hourly_pos"], ns["daily_to_hourly"]
ROWS, CANDS = [], {}


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b]; return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


def per(name, h, **extra):
    r = {"test": name, "DEV 2020-22": dsh(h, "2020", "2022"), "TEST 2023-24": dsh(h, "2023", "2024"), "HOLD 2025-26": dsh(h, "2025", "2026-09"), **extra}
    ROWS.append(r); CANDS[name] = h; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True); return r


def book(cols):
    return CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]


S3 = ns["sleeves"](3.3, 1.0); S0 = ns["sleeves"](0.0, 1.0)
base = {"C*": S3["C*"], "Weiss expiry": S3["Weiss expiry"]}
B0 = dsh(book(base), "2022", "2026-09"); print("base CFD book 2022-26", round(B0, 3), flush=True)
SF = {k: S0[k] for k in ("C*", "premium carry", "trend 4h", "Weiss expiry")}
BSF = dsh(book(SF), "2022", "2026-09"); print("swap-free book 2022-26", round(BSF, 3), flush=True)
per("ref Weiss BTC/ETH", S3["Weiss expiry"]); per("ref C* CFD", S3["C*"])

# A1 Weiss on 11 CFD coins (spread per coin instead of the 5 bp taker in the builder: P&L from positions)
_, wp = CS.weiss_expiry(coins=tuple(CFD), positions=True)
wa = fhp(wp.loc[:END], 0.0)
bA = dsh(book({**base, "Weiss expiry": wa}), "2022", "2026-09")
_, wp2 = CS.weiss_expiry(positions=True); wb = fhp(wp2.loc[:END], 0.0)
rb = per("ref Weiss BTC/ETH, CFD spreads", wb)
ra = per("A1 Weiss 11 CFD coins (PRIMARY)", wa, book_before=B0, book_after=bA)
ra["adopt"] = bool(ra["TEST 2023-24"] > rb["TEST 2023-24"] and ra["HOLD 2025-26"] > rb["HOLD 2025-26"] and bA > B0)
print("A1 adopt", ra["adopt"], flush=True)

# B1 swap-aware C*
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0
res = {}
for thr in (0.0, 0.5, 1.0):
    a = cw.abs(); m = a.where(a > 0).mean(axis=1)
    w = cw.where(a.ge(m * thr, axis=0) | (thr == 0), 0.0)
    h = fhp(d2h(w), 3.3); res[thr] = h
    per(f"B1 swap-aware C* thr {thr}", h, gross=float(w.abs().sum(axis=1).loc["2022":].mean()), book_after=dsh(book({**base, "C*": h}), "2022", "2026-09"))
pick = max(res, key=lambda t: dsh(res[t], "2020", "2022"))
bB = dsh(book({**base, "C*": res[pick]}), "2022", "2026-09")
adoptB = pick != 0.0 and dsh(res[pick], "2023", "2024") >= dsh(res[0.0], "2023", "2024") and dsh(res[pick], "2025", "2026-09") >= dsh(res[0.0], "2025", "2026-09") and bB > B0
ROWS.append({"test": f"B1 decision: thr {pick}", "adopt": adoptB, "book_after": bB}); print("B1 pick", pick, "adopt", adoptB, flush=True)

# B2 C* by side
for side, w in (("long only", cw.clip(lower=0)), ("short only", cw.clip(upper=0))):
    h = fhp(d2h(w), 3.3)
    per(f"B2 C* {side} (info)", h, book_after=dsh(book({**base, "C*": h}), "2022", "2026-09"))

# D1 trend 4h on 11 CFD coins
_, tp = CS.trend4h(coins=tuple(CFD), positions=True)
t3 = fhp(tp.loc[:END], 3.3); t0 = fhp(tp.loc[:END], 0.0)
bD = dsh(book({**base, "trend 4h 11": t3}), "2022", "2026-09")
rd = per("D1 trend 4h 11 CFD coins, swap 3.3 (PRIMARY)", t3, book_before=B0, book_after=bD,
         corr_cstar=float(pd.concat([S3["C*"], t3], axis=1).groupby(S3.index.floor("D")).sum().loc["2020":].corr().iloc[0, 1]))
rd["adopt"] = bool(rd["TEST 2023-24"] >= 0.5 and rd["HOLD 2025-26"] >= 0.3 and bD > B0)
bD0 = dsh(book({**SF, "trend 4h": t0}), "2022", "2026-09")
per("D1 trend 4h 11 coins in swap-free book (swap 0, replaces trend 4h BTC/ETH/SOL)", t0, book_before=BSF, book_after=bD0)
per("ref trend 4h BTC/ETH/SOL swap 3.3", S3["trend 4h"])
print("D1 adopt", rd["adopt"], flush=True)

pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen85_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen85.csv", index=False)
print("done", flush=True)
