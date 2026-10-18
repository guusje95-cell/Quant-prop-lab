"""Gen87 (config/gen87_protocol.json): dip-buy, BTC/ETH-only cascade and trend 4h in the CFD book. Reuses the Gen74 builders.
Writes results/gen87.csv and results/cache_gen87_hourly.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, B, CFD, END, fhp, d2h, SPREAD, R1h = ns["CS"], ns["B"], ns["CFD"], ns["END"], ns["from_hourly_pos"], ns["daily_to_hourly"], ns["SPREAD"], ns["R1"]
ROLL = ns["ROLL"]
ROWS, CANDS = [], {}


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b]; return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


P = B.panel("close", "1D", CFD).loc[:"2026-09-30"]; R = P.pct_change(fill_method=None); listed = P.notna().cumsum() >= 60


def dip_w(coins, k=2.5, ma=100, hold=3, cap=3):
    sd30 = R[coins].rolling(30).std().shift(1); m = P[coins].rolling(ma).mean()
    sig = (R[coins] < -k * sd30) & (P[coins] > m) & listed[coins]
    w = pd.DataFrame(0.0, index=P.index, columns=CFD); active = {}
    for d in P.index:
        active = {c: n - 1 for c, n in active.items() if n - 1 > 0}
        for c in sig.columns[sig.loc[d].fillna(False).to_numpy()]:
            if c not in active and len(active) < cap:
                active[c] = hold
        for c in active:
            w.at[d, c] = 0.2
    return w


def cascade2(swap):
    pnl, pos = CS.cascade(limit=0.005, through=0.001, coins=["BTC", "ETH"], cost_map={"BTC": 5.0, "ETH": 5.0}, positions=True)
    sw = pos.reindex(R1h.index).fillna(0.0).abs().sum(axis=1).where(ROLL, 0.0) * swap / 1e4
    return pnl.reindex(R1h.index).fillna(0.0) - sw


C85 = pd.read_parquet(ROOT / "results/cache_gen85_hourly.parquet").reindex(R1h.index).fillna(0.0)
S0 = ns["sleeves"](0.0, 1.0)
BASE = {"C*": C85["B1 swap-aware C* thr 0.5"], "Weiss expiry": C85["ref Weiss BTC/ETH"]}
SF = {k: S0[k] for k in ("C*", "premium carry", "trend 4h", "Weiss expiry")}
bk = lambda cols: CS.portfolio_v5(pd.DataFrame(cols).fillna(0.0))[0]
B0 = dsh(bk(BASE), "2022", "2026-09"); BSF = dsh(bk(SF), "2022", "2026-09")
print("Gen85 CFD book", round(B0, 3), "| swap-free book", round(BSF, 3), flush=True)
cst = BASE["C*"].groupby(BASE["C*"].index.floor("D")).sum()

_, tp = CS.trend4h(coins=("BTC", "ETH"), positions=True)
tests = {"R1 dip-buy 11 CFD coins (PRIMARY)": (lambda sw: fhp(d2h(dip_w(CFD)), sw), True, None),
         "R2 cascade strict BTC/ETH CFD (PRIMARY)": (cascade2, True, None),
         "R3 trend 4h BTC/ETH (PRIMARY)": (lambda sw: fhp(tp.loc[:END], sw), True, "trend 4h"),
         "R4 dip-buy BTC/ETH (variant)": (lambda sw: fhp(d2h(dip_w(["BTC", "ETH"])), sw), False, None)}
passed = []
for name, (fn, primary, replaces) in tests.items():
    h3, h0 = fn(3.3), fn(0.0)
    bA = dsh(bk({**BASE, name: h3}), "2022", "2026-09")
    sf = {k: v for k, v in SF.items() if k != replaces}; bSF = dsh(bk({**sf, name: h0}), "2022", "2026-09")
    r = {"test": name, "DEV 2020-22": dsh(h3, "2020", "2022"), "TEST 2023-24": dsh(h3, "2023", "2024"), "HOLD 2025-26": dsh(h3, "2025", "2026-09"),
         "corr C*": float(pd.concat([cst, h3.groupby(h3.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]),
         "book before": B0, "book after": bA, "swap-free: TEST": dsh(h0, "2023", "2024"), "swap-free: HOLD": dsh(h0, "2025", "2026-09"),
         "swap-free book before": BSF, "swap-free book after": bSF, "swap-free replaces": replaces or ""}
    r["pass"] = bool(primary and r["DEV 2020-22"] > 0 and r["TEST 2023-24"] >= 0.5 and r["HOLD 2025-26"] >= 0.3 and bA > B0)
    if r["pass"]:
        passed.append(name)
    ROWS.append(r); CANDS[name] = h3; CANDS[name + " | swap 0"] = h0
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
if len(passed) >= 2:
    bC = dsh(bk({**BASE, **{n: CANDS[n] for n in passed}}), "2022", "2026-09")
    ROWS.append({"test": "combination: " + " + ".join(passed), "book after": bC}); print("combination", passed, round(bC, 3), flush=True)
print("passed:", passed, flush=True)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen87_hourly.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen87.csv", index=False)
print("done", flush=True)
