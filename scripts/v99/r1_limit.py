"""v9.9 R1 (execution): limit orders for the DAILY sleeves (C*, delev bounce, ridge ML, alt kimchi, basket) of v9.8, measured against
the unchanged v9.8 book with realistic Bybit taker costs on its net trades (control, Gen473b: 3.283).

Per day and coin (pack coins with 5-minute data; other coins stay taker), x = the part of the 00:00 net trade that comes from the daily
sleeves (same sign as the net trade). Control: x is bought at 00:00 (price P0 = 5-min close before 00:00 + d) as taker: half spread
hs + 5.5 bp. Candidate: a limit at P0 * (1 -/+ (hs + o)) resting for W minutes from 00:00 + d. Fill rule (conservative, OHLC only):
filled only if a later 5-min bar trades THROUGH the limit by delta (low <= L * (1 - delta) for a buy); no queue-position or volume
information, so a fill is full or nothing. Filled: maker 2 bp, P&L from the fill price. Not filled: cancel and cross at the window
end (taker at the then price: the missed move is lost). Adverse selection is in the numbers by construction: limits fill when the
price moves against the order. Difference vs control is added to the control book (exact for the window; afterwards identical).
Writes results/v99/r1_limit.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import binance_pack as B, extra_pack as X
END = "2026-09-30"
N = pd.read_parquet(ROOT / "results/v99/netpos.parquet"); ND = pd.read_parquet(ROOT / "results/v99/netpos_daily.parquet")
BC = pd.read_parquet(ROOT / "results/v99/book_charged.parquet"); ix = N.index
TOP10 = {"SOL", "XRP", "BNB", "DOGE", "ADA", "TRX", "AVAX", "LINK", "TON", "SUI"}; ALT = set(B.coins()) | set(X.coins())
cls = lambda c: "major" if c in ("BTC", "ETH") else "top10" if c in TOP10 else "alt" if c in ALT else "event"
HS = {"major": 0.5, "top10": 1.5, "alt": 3.0, "event": 10.0}
nt = N.diff().abs().fillna(0.0)
taker = sum(nt[c] * (5.5 + HS[cls(c)]) / 1e4 for c in N.columns)
control = BC["book"] + BC["charged"] - taker
dd = lambda h: h.groupby(h.index.floor("D")).sum()
def stats(h):
    d = dd(h.loc["2022":END]); s = lambda a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365)), 3)
    eq = d.cumsum()
    return {"Sharpe": s("2022", END), "2022 / 23-24 / 25-26": [s("2022", "2022"), s("2023", "2024"), s("2025", END)],
            "by year": [s(y, y) for y in ("2022", "2023", "2024", "2025", "2026")], "return / vol per year (unit book)": [round(float(d.mean() * 365), 4), round(float(d.std() * np.sqrt(365)), 4)],
            "max drawdown (unit book, additive)": round(float((eq - eq.cummax()).min()), 4)}
# daily-sleeve part of the 00:00 net trades
mid = ix[ix.hour == 0]
dN = N.diff().loc[mid]; dD = ND.diff().loc[mid]
X_ = dD.where(np.sign(dD) == np.sign(dN), 0.0); X_ = np.sign(X_) * np.minimum(X_.abs(), dN.abs())
coins = [c for c in X_.columns if c in B.coins() and X_[c].abs().sum() > 0]
K5 = {c: B.k5(c)[["low", "high", "close"]] for c in coins}
def run(o=0.0, W=60, delta=1.0, d=0):
    diff = pd.Series(0.0, index=ix); n_tr = n_fill = 0; gain = []
    for c in coins:
        k = K5[c]; hs = HS[cls(c)] / 1e4
        for t, x in X_[c].items():
            if x == 0 or not np.isfinite(x):
                continue
            s = t + pd.Timedelta(minutes=d); bars = k.loc[s:s + pd.Timedelta(minutes=W - 5)]
            pre = k["close"].loc[:s - pd.Timedelta(minutes=5)]
            if len(bars) == 0 or len(pre) == 0:
                continue
            P0 = pre.iloc[-1]; PW = bars["close"].iloc[-1]; sg = np.sign(x); n_tr += 1
            base = x * (PW / (P0 * (1 + sg * hs)) - 1) - abs(x) * 5.5e-4             # control: taker at the start (half spread + fee)
            L = P0 * (1 - sg * (hs + o / 1e4))
            hit = bars["low"] <= L * (1 - delta / 1e4) if sg > 0 else bars["high"] >= L * (1 + delta / 1e4)
            if hit.any():
                n_fill += 1; cand = x * (PW / L - 1) - abs(x) * 2e-4
            else:
                cand = -abs(x) * (hs + 5.5e-4)                                       # cross at the window end, no exposure during it
            # the control book already holds x from s: its return P0 -> PW is in the book; add (cand - base) on top of x*(PW/P0-1)
            dlt = cand - base
            h = (s + pd.Timedelta(minutes=W - 5)).floor("h")
            if h in diff.index:
                diff[h] += dlt; gain.append(dlt / abs(x) * 1e4)
    res = stats(control + diff); res.update({"orders": n_tr, "fill rate": round(n_fill / max(n_tr, 1), 3), "mean gain per order (bp of notional)": round(float(np.mean(gain)), 2),
                                             "p5 / p95 gain (bp)": [round(float(np.percentile(gain, 5)), 1), round(float(np.percentile(gain, 95)), 1)]})
    return res
out = {"control (v9.8, Bybit taker on net trades)": stats(control), "limit coins": coins, "variants": {}}
grid = [dict(o=0, W=60, delta=1), dict(o=2, W=60, delta=1), dict(o=5, W=60, delta=1), dict(o=0, W=30, delta=1), dict(o=0, W=120, delta=1),
        dict(o=0, W=60, delta=3), dict(o=0, W=60, delta=1, d=10), dict(o=2, W=60, delta=3, d=10)]
for g in grid:
    k_ = ", ".join(f"{a}={b}" for a, b in g.items()); out["variants"][k_] = run(**g); print(k_, out["variants"][k_], flush=True)
(ROOT / "results/v99/r1_limit.json").write_text(json.dumps(out, indent=1))
