"""Gen57 T9 + T10 (config/gen57_protocol.json): C* + BTC leads executed on Binance USD-M perps with real funding, 00:00 vs 08:00 UTC
rebalance, and four pre-registered overlays (crowding, taker confirmation, wick guard). Weights are the frozen C* weights
(spot signal, 15% vol on DEV). DEV = 2020-01..2022-12, TEST = 2023-01..2026-09. Writes results/gen57_cstar_perp.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import binance_pack as B, strategies as S

COINS = B.MAJ10; COST = 7.5 / 1e4
cs = S.CStarTrend(); W, SPOT = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0)
W = W[COINS]
D_OPEN, D_HIGH, D_LOW, D_CLOSE = (B.panel(f, "1D", COINS) for f in ("open", "high", "low", "close"))
idx = D_CLOSE.index[(D_CLOSE.index >= "2020-01-02") & (D_CLOSE.index <= "2026-09-30")]
FUND = B.funding_panel(COINS)


def daily_funding(offset_h=0):
    """funding paid by a long held from day d (offset) to day d+1 (offset): settlements in (d+offset, d+1+offset]."""
    f = FUND.copy(); f.index = (f.index - pd.Timedelta(hours=offset_h) - pd.Timedelta(seconds=1)).floor("D")
    return f.groupby(level=0).sum().reindex(idx).fillna(0.0)


def run(held, ret, fund=None):
    held = held.reindex(idx).fillna(0.0)
    pnl = (held * ret.reindex(idx).fillna(0.0)).sum(axis=1) - held.diff().abs().sum(axis=1).fillna(0.0) * COST
    if fund is not None:
        pnl -= (held * fund).sum(axis=1)
    return pnl


def stats(x, name):
    out = {"variant": name}
    for per, sl in (("ALL", slice("2020-01-02", None)), ("DEV", slice("2020-01-02", "2022-12-31")), ("TEST", slice("2023-01-01", None))):
        y = x.loc[sl]
        m = (1 + y).resample("ME").prod() - 1
        dd = (1 + y).cumprod(); dd = (dd / dd.cummax() - 1).min()
        out.update({f"{per}_sharpe": y.mean() / y.std() * np.sqrt(365), f"{per}_ann": y.mean() * 365, f"{per}_maxdd": dd,
                    f"{per}_posm": (m > 0).mean(), f"{per}_worst_day": y.min()})
    return out


held = W.shift(1)                                                     # weights from close d-1 held over day d
r_perp = D_CLOSE.pct_change(fill_method=None)
F0 = daily_funding(0)
rows = [stats(SPOT["net"].reindex(idx).fillna(0.0), "spot backtest (reference)"),
        stats(run(held, r_perp), "perp prices, no funding"),
        stats(run(held, r_perp, F0), "perp + real funding (00:00 rebalance)")]
print("annual funding drag on C* (fraction of equity):", float((held.reindex(idx).fillna(0) * F0).sum(axis=1).mean() * 365))

# 08:00 UTC rebalance: same weights, executed 8 hours later
H = B.panel("close", "1h", COINS)
P08 = H[H.index.hour == 7]; P08.index = P08.index.floor("D")       # close of 07:00 bar = price at 08:00 of that day
r08 = P08.pct_change(fill_method=None)                              # 08:00 d-1 -> 08:00 d, labelled d
held08 = W.shift(1).reindex(idx)                                    # decided at 00:00 d, in place from 08:00 d
rows.append(stats(run(held08.shift(1), r08, daily_funding(8)), "perp + funding, rebalance 08:00 UTC"))

# ---- T10 overlays on 'perp + funding (00:00)'
fd = FUND.copy(); fd.index = fd.index.floor("D"); fday = fd.groupby(level=0).mean().reindex(idx)
f3 = fday.rolling(3, min_periods=2).mean()
hi = f3.rolling(365, min_periods=120).quantile(0.9).shift(1)
oi = pd.DataFrame({c: B.metrics(c)["sum_open_interest_value"].resample("1D").last() for c in COINS}).reindex(idx)
oi7 = oi / oi.shift(7) - 1
crowd = (f3 > hi) & (oi7 > 0.15)
w_a = W.reindex(idx).where(~crowd, W.reindex(idx) * 0.5)
rows.append(stats(run(w_a.shift(1), r_perp, F0), "T10a crowding filter (halve when funding top-10% & OI +15%/7d)"))

tq = B.panel("taker_buy_quote_volume", "1D", COINS); qv = B.panel("quote_volume", "1D", COINS)
share = (tq / qv).reindex(idx)
wb = W.reindex(idx).copy(); prev = pd.Series(0.0, index=COINS)
for d in idx:
    cur = wb.loc[d]
    new_entry = (prev <= 0) & (cur > 0)
    blocked = new_entry & ~(share.loc[d] > 0.5)
    cur = cur.where(~blocked, 0.0); wb.loc[d] = cur; prev = cur
rows.append(stats(run(wb.shift(1), r_perp, F0), "T10b taker confirmation for new entries"))

tr = pd.concat([D_HIGH - D_LOW, (D_HIGH - D_CLOSE.shift(1)).abs(), (D_LOW - D_CLOSE.shift(1)).abs()]).groupby(level=0).max()
atrp = (tr.rolling(14).mean() / D_CLOSE).shift(1)                    # ATR as a fraction, known at the start of the day
low_from_open = D_LOW / D_OPEN - 1; ret_from_open = D_CLOSE / D_OPEN - 1
gap = D_OPEN / D_CLOSE.shift(1) - 1                                  # ~0 for 24/7 markets
stop = -3 * atrp
r_c = r_perp.copy()
hit = low_from_open <= stop
r_c = r_c.where(~hit, (1 + gap) * (1 + stop - 0.001) - 1)           # stopped at -3 ATR (+10 bp slippage), flat for the rest of the day
rows.append(stats(run(held, r_c, F0.where(~hit.reindex(idx).fillna(False), F0 * 2 / 3)), "T10c wick guard: intraday stop at -3 ATR"))
print("wick-guard stop days per coin-year:", float(hit.reindex(idx).sum().sum() / len(COINS) / (len(idx) / 365)))

out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen57_cstar_perp.csv", index=False)
pd.set_option("display.width", 250)
print(out[["variant", "ALL_sharpe", "DEV_sharpe", "TEST_sharpe", "ALL_ann", "ALL_maxdd", "ALL_posm", "ALL_worst_day"]].round(3).to_string())
