"""Gen100: firm-condition feasibility of the CFD book (not a strategy trial). Uses the frozen signals (scratchpad dumps from
gen96_pit_dump.py) and re-prices them under each firm's verified / unverified conditions:
  - coin universe actually offered (FundedNext's help-centre list has no SOL, AVAX, DOT, BCH),
  - commission per side on top of the spread (FundedNext 4 bp, FTMO 3.25 bp, BrightFunded 1.2 bp; third-party / help-centre via search),
  - spread scenarios (not published: low = 2 bp BTC/ETH, 5 bp alts; base = 5 / 10 bp),
  - swap 0 (swap-free) or 3.3 bp/day,
  - weekend flat (FTMO funded Standard: positions closed before the weekend),
  - gross notional vs leverage caps (FTMO Swing / FundedNext crypto reported 1:1; FTMO Standard 1:3.3).
Writes results/gen100_firms.csv and results/gen100_exposure.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
src = open(ROOT / "scripts/gen74_crypto_cfd.py").read().split('SCEN = {')[0]
ns = {"__file__": str(ROOT / "scripts/gen74_crypto_cfd.py")}; exec(compile(src, "gen74_builders", "exec"), ns)
CS, CFD, d2h, R1 = ns["CS"], ns["CFD"], ns["daily_to_hourly"], ns["R1"]
IDX = R1.index; ROLL = pd.Series(IDX.hour == 21, index=IDX)
cw = pd.read_parquet(S / "cstar_full.parquet"); bw = pd.read_parquet(S / "bounce_full.parquet"); wp = pd.read_parquet(S / "weiss_full.parquet")
POS0 = {"C*": d2h(cw).reindex(IDX).fillna(0.0), "Weiss expiry": wp.reindex(IDX).fillna(0.0), "delev bounce": d2h(bw.reindex(columns=CFD).fillna(0.0)).reindex(IDX).fillna(0.0)}
WEEKEND = pd.Series((IDX.dayofweek == 4) & (IDX.hour >= 20) | (IDX.dayofweek == 5) | (IDX.dayofweek == 6), index=IDX)   # Fri 20:00 -> Mon 00:00 UTC flat


def pnl(pos, spread, comm, swap, universe, weekend_flat):
    pos = pos.reindex(columns=CFD).fillna(0.0)
    pos[[c for c in CFD if c not in universe]] = 0.0
    if weekend_flat:
        pos = pos.mul((~WEEKEND).astype(float), axis=0)
    cost = pd.Series({c: spread[0] if c in ("BTC", "ETH") else spread[1] for c in CFD}) + comm
    turn = pos.diff().abs().fillna(pos.abs()).mul(cost / 1e4, axis=1).sum(axis=1)
    return (pos * R1).sum(axis=1) - turn - pos.abs().sum(axis=1).where(ROLL, 0.0) * swap / 1e4, pos


def book(**kw):
    H, P = {}, {}
    for k, p in POS0.items():
        H[k], P[k] = pnl(p, swap=0.0 if k == "Weiss expiry" else kw["swap"], **{a: b for a, b in kw.items() if a != "swap"})
    H = pd.DataFrame(H).fillna(0.0); ph, W, mult = CS.portfolio_v5(H)
    d = ph.groupby(ph.index.floor("D")).sum().loc["2022":"2026-09-30"]
    k15 = 0.15 / (d.std() * np.sqrt(365))                               # the prop sims run the book at 15% vol
    Wh = W.reindex(IDX.floor("D")).set_axis(IDX); mh = mult.reindex(IDX.floor("D")).set_axis(IDX)
    gross = sum(P[k].abs().sum(axis=1) * Wh[k] for k in P) * mh * k15
    sh = lambda a, b: float(d.loc[a:b].mean() / d.loc[a:b].std() * np.sqrt(365))
    return {"Sharpe 2022-26": sh("2022", "2026-09-30"), "TEST 23-24": sh("2023", "2024"), "HOLD 25-26": sh("2025", "2026-09-30"),
            "gross p50 @15%vol": float(gross.loc["2022":].median()), "gross p99 @15%vol": float(gross.loc["2022":].quantile(0.99)), "gross max @15%vol": float(gross.loc["2022":].max())}


ALL = set(CFD); FN = {"BTC", "ETH", "XRP", "ADA", "DOGE", "LINK", "LTC"}            # FundedNext help-centre list (plus XLM, XMR not used)
BF = ALL - {"LTC", "DOGE"}                                                         # BrightFunded: LTC / DOGE not found in sources
rows = []
scen = [
    ("reference (Gen90 model): 5/10 bp all-in, swap 3.3", dict(spread=(5, 10), comm=0, swap=3.3, universe=ALL, weekend_flat=False)),
    ("reference swap-free: 5/10 bp all-in, swap 0", dict(spread=(5, 10), comm=0, swap=0.0, universe=ALL, weekend_flat=False)),
    ("FundedNext swap-free, 6 coins, low spread 2/5 + 4 bp comm", dict(spread=(2, 5), comm=4.0, swap=0.0, universe=FN, weekend_flat=False)),
    ("FundedNext swap-free, 6 coins, base spread 5/10 + 4 bp comm", dict(spread=(5, 10), comm=4.0, swap=0.0, universe=FN, weekend_flat=False)),
    ("FundedNext standard, 6 coins, base + 4 bp, swap 3.3", dict(spread=(5, 10), comm=4.0, swap=3.3, universe=FN, weekend_flat=False)),
    ("FTMO evaluation/Swing, all coins, low 2/5 + 3.25, swap 3.3", dict(spread=(2, 5), comm=3.25, swap=3.3, universe=ALL, weekend_flat=False)),
    ("FTMO evaluation/Swing, all coins, base 5/10 + 3.25, swap 3.3", dict(spread=(5, 10), comm=3.25, swap=3.3, universe=ALL, weekend_flat=False)),
    ("FTMO funded Standard: weekend flat, base + 3.25, swap 3.3", dict(spread=(5, 10), comm=3.25, swap=3.3, universe=ALL, weekend_flat=True)),
    ("BrightFunded standard, no LTC/DOGE, base + 1.2, swap 3.3", dict(spread=(5, 10), comm=1.2, swap=3.3, universe=BF, weekend_flat=False)),
    ("BrightFunded swap-free (if add-on exists), base + 1.2", dict(spread=(5, 10), comm=1.2, swap=0.0, universe=BF, weekend_flat=False)),
    ("BrightFunded swap-free, low 2/5 + 1.2", dict(spread=(2, 5), comm=1.2, swap=0.0, universe=BF, weekend_flat=False)),
]
for nm, kw in scen:
    r = {"scenario": nm, **book(**kw)}; rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen100_firms.csv", index=False)
print("done", flush=True)
