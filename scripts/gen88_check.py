"""Gen88 checks for Q1 (descriptive, no selection): timestamp alignment of Coinbase vs Binance, entry delays, thresholds, hold, per coin,
long/short legs, 2x costs, swap-free, placebo with shuffled signal days. Writes results/gen88_check.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen88_coinbase.py")}
exec(open(ROOT / "scripts/gen88_coinbase.py").read().split("C85 = pd.read_parquet")[0], g)
B, CFD, fhp, d2h, IDX, dsh, Z, PREM, zd, R1 = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "dsh", "Z", "PREM", "zd", "R1"))
# 1) alignment: hourly returns on both venues should line up at lag 0
for c, prod in (("BTC", "BTC-USD"), ("ETH", "ETH-USD")):
    cb = pd.read_parquet(ROOT / f"research_data/coinbase/{prod}_1h.parquet")["close"].pct_change()
    bn = B.k5(c).close.resample("1h").last().pct_change()
    j = pd.concat([cb, bn], axis=1).dropna().loc["2021":"2026-09"]
    print(c, "corr of hourly returns Coinbase vs Binance at lag -1/0/+1:",
          [round(j.iloc[:, 0].corr(j.iloc[:, 1].shift(k)), 3) for k in (-1, 0, 1)], flush=True)
    pr = PREM[c]; rr = bn.reindex(pr.index)
    print("   corr(premium level, Binance return same hour / next hour):", round(pr.corr(rr), 3), round(pr.corr(rr.shift(-1)), 3), flush=True)


def q(th=1.0, hold=1, coins=("BTC", "ETH"), lag_h=0, swap=3.3, side="both", mult=1.0, sig=None):
    zz = zd if sig is None else sig
    w = pd.DataFrame(0.0, index=zz.index, columns=CFD)
    for c in coins:
        s = pd.Series(np.where(zz[c] > th, 0.5, np.where(zz[c] < -th, -0.5, 0.0)), index=zz.index)
        if side == "long":
            s = s.clip(lower=0)
        if side == "short":
            s = s.clip(upper=0)
        if hold > 1:
            s = s.replace(0.0, np.nan).ffill(limit=hold - 1).fillna(0.0)
        w[c] = s
    pos = d2h(w)
    if lag_h:
        pos = pos.shift(lag_h).fillna(0.0)
    return fhp(pos, swap, mult).reindex(IDX).fillna(0.0)


per = lambda h: (dsh(h, "2020-01-01", "2022-12-31"), dsh(h, "2023-01-01", "2024-12-31"), dsh(h, "2025-01-01", "2026-09-30"), dsh(h, "2020-01-01", "2026-09-30"))
rows = []
for nm, kw in (("base z>1 hold 1d", {}), ("z>0.75", {"th": 0.75}), ("z>1.25", {"th": 1.25}), ("z>1.5", {"th": 1.5}), ("hold 2d", {"hold": 2}),
               ("hold 3d", {"hold": 3}), ("BTC only", {"coins": ("BTC",)}), ("ETH only", {"coins": ("ETH",)}), ("long leg only", {"side": "long"}),
               ("short leg only", {"side": "short"}), ("entry 1h late", {"lag_h": 1}), ("entry 4h late", {"lag_h": 4}), ("entry 12h late", {"lag_h": 12}),
               ("2x spread", {"mult": 2.0}), ("swap-free", {"swap": 0.0}), ("swap 6.6", {"swap": 6.6})):
    p = per(q(**kw)); rows.append({"variant": nm, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "2020-26": p[3]})
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
# placebo: shuffle the daily z rows in blocks of 30 days (keeps the long/short mix, breaks the timing), 200 draws
rng = np.random.default_rng(3); base = per(q())[3]; sims = []
blocks = [zd.iloc[i:i + 30] for i in range(0, len(zd), 30)]
for _ in range(200):
    order = rng.permutation(len(blocks)); sh = pd.concat([blocks[i] for i in order]).set_axis(zd.index[:sum(len(b) for b in blocks)])
    sims.append(per(q(sig=sh))[3])
sims = np.array(sims)
rows.append({"variant": "placebo: 30-day blocks shuffled (200)", "2020-26": float(sims.mean()), "p95": float(np.percentile(sims, 95)), "p-value": float((sims >= base).mean())})
print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen88_check.csv", index=False)
