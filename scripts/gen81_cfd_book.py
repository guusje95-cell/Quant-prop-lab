"""Gen81 (config/gen81_protocol.json): C* rebalance band at CFD costs, and CME weekend-gap reversion on BTC/ETH CFDs.
Writes results/gen81.csv and results/cache_gen81_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B, engine as EN

warnings.filterwarnings("ignore")
END = "2026-09-30 23:00"
CFD = ["BTC", "ETH", "LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
SPREAD = {c: (5.0 if c in ("BTC", "ETH") else 10.0) for c in CFD}
SWAP = 3.3
H1 = B.panel("close", "1h", CFD).loc[:END]; R1 = H1.pct_change(fill_method=None).fillna(0.0)
ROLL = pd.Series(R1.index.hour == 21, index=R1.index)
ROWS, CANDS = [], {}


def from_hourly_pos(pos, swap_bp=SWAP):
    pos = pos.reindex(R1.index).reindex(columns=CFD).fillna(0.0)
    turn = pos.diff().abs().fillna(pos.abs()).mul(pd.Series(SPREAD) / 1e4, axis=1).sum(axis=1)
    return (pos * R1).sum(axis=1) - turn - pos.abs().sum(axis=1).where(ROLL, 0.0) * swap_bp / 1e4


def daily_to_hourly(w):
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)])))
    return w.reindex(columns=CFD).shift(1).reindex(R1.index.floor("D")).set_axis(R1.index).fillna(0.0)


def dsh(h, a, b):
    d = h.groupby(h.index.floor("D")).sum().loc[a:b] if hasattr(h.index, "floor") else h.loc[a:b]
    return float(d.mean() / d.std() * np.sqrt(365)) if d.std() > 0 else np.nan


def per_row(name, h, extra=None):
    r = {"test": name, "DEV 2020-22": dsh(h, "2020", "2022"), "TEST 2023-24": dsh(h, "2023", "2024"), "HOLD 2025-26": dsh(h, "2025", "2026-09"),
         "2023-26": dsh(h, "2023", "2026-09"), "2022-26": dsh(h, "2022", "2026-09"), **(extra or {})}
    ROWS.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True); return r


# ---------------------------------------------------------------- E1 rebalance band
cw = CS.cstar_weights().copy(); cw["BNB"] = 0.0
_, wp = CS.weiss_expiry(positions=True); weiss = from_hourly_pos(wp.loc[:END], 0.0)
BAND = {}
for band in (0.0, 0.10, 0.25, 0.50):
    w = EN.apply_band(cw, band) if band > 0 else cw
    h = from_hourly_pos(daily_to_hourly(w)); BAND[band] = h
    turn = w.diff().abs().sum(axis=1).loc["2022":].mean()
    per_row(f"E1 C* CFD, band {band:.2f}", h, {"avg daily turnover": float(turn)})
smooth = {b: np.mean([dsh(BAND[x], "2020", "2022") for x in nb]) for b, nb in
          ((0.0, (0.0, 0.10)), (0.10, (0.0, 0.10, 0.25)), (0.25, (0.10, 0.25, 0.50)), (0.50, (0.25, 0.50)))}
pick = max(smooth, key=smooth.get)
base_book, _, _ = CS.portfolio_v5(pd.DataFrame({"C*": BAND[0.0], "Weiss expiry": weiss}).fillna(0.0))
pick_book, _, _ = CS.portfolio_v5(pd.DataFrame({"C*": BAND[pick], "Weiss expiry": weiss}).fillna(0.0))
adopt = pick != 0.0 and dsh(BAND[pick], "2023", "2026-09") >= dsh(BAND[0.0], "2023", "2026-09") and \
    dsh(BAND[pick], "2025", "2026-09") >= dsh(BAND[0.0], "2025", "2026-09") and dsh(pick_book, "2022", "2026-09") > dsh(base_book, "2022", "2026-09")
print(f"E1 DEV-smoothed pick: band {pick}; CFD book 2022-26 Sharpe {dsh(base_book, '2022', '2026-09'):.3f} -> {dsh(pick_book, '2022', '2026-09'):.3f}; adopted: {adopt}", flush=True)
ROWS.append({"test": f"E1 decision: band {pick}", "adopted": adopt, "book_before": dsh(base_book, "2022", "2026-09"), "book_after": dsh(pick_book, "2022", "2026-09")})
BOOK = pick_book if adopt else base_book
BOOKD = BOOK.groupby(BOOK.index.floor("D")).sum()


# ---------------------------------------------------------------- E2 CME weekend-gap reversion
def cme_gap(coin, thr=0.01):
    k = B.k5(coin).loc[:END]; o = k.open.resample("1h").first(); hi = k.high.resample("1h").max(); lo = k.low.resample("1h").min()
    c = k.close.resample("1h").last(); out = {}
    for fri in pd.date_range("2020-01-03", "2026-09-25", freq="W-FRI"):
        tF = fri + pd.Timedelta(hours=20); tS = fri + pd.Timedelta(days=2, hours=22); tW = tS + pd.Timedelta(days=3)
        if tF not in c.index or tS not in o.index or tW not in o.index:
            continue
        F, S = c[tF], o[tS]; gap = S / F - 1
        if abs(gap) <= thr:
            continue
        side = -np.sign(gap); exit_t, exit_px = tW, o[tW]
        for t in pd.date_range(tS, tW - pd.Timedelta(hours=1), freq="1h"):
            if t in hi.index and ((side < 0 and lo[t] <= F) or (side > 0 and hi[t] >= F)):
                exit_t, exit_px = t + pd.Timedelta(hours=1), F; break
        rolls = sum(1 for t in pd.date_range(tS + pd.Timedelta(hours=1), exit_t, freq="1h") if t.hour == 22)
        out[exit_t.normalize()] = out.get(exit_t.normalize(), 0.0) + side * (exit_px / S - 1) - 2 * SPREAD[coin] / 1e4 - rolls * SWAP / 1e4
    return pd.Series(out)


days = pd.date_range("2020-01-01", "2026-09-30")
for thr, nm in ((0.01, "E2 CME weekend-gap reversion 1% (PRIMARY)"), (0.02, "E2 variant 2%")):
    g = (cme_gap("BTC", thr).reindex(days).fillna(0) + cme_gap("ETH", thr).reindex(days).fillna(0)) / 2
    CANDS[nm] = g
    j = pd.concat([BOOKD, g], axis=1).loc["2022":"2026-09"].fillna(0.0); j = j / j.std(); comb = j.mean(axis=1)
    per_row(nm, g, {"events": int((g != 0).sum()), "book_alone": dsh(BOOKD, "2022", "2026-09"), "book_plus": float(comb.mean() / comb.std() * np.sqrt(365)),
                    "corr_book": float(pd.concat([BOOKD, g], axis=1).dropna().corr().iloc[0, 1])})

pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen81_daily.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen81.csv", index=False)
print("done", flush=True)
