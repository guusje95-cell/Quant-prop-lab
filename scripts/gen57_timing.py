"""Gen57/Gen60 timing strategies on Binance perps (pre-registered in config/gen57_protocol.json and config/gen60_paper_scan_queue.json).
T1/B2 evening window (taker, maker approx.), B2 long-short, B1 noise-area intraday trend, T6 premium-bound reversion, T8 Gao
first->last half hour, T7 Wen hour pairs (confirmatory). Splits: DEV 2020-22 | TEST 2023-24 | HOLD 2025-26 (and 2023+).
Writes results/gen57_timing.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import binance_pack as B, strategies as S

cs = S.CStarTrend(); _, CD = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0)
CSTAR = CD["net"]
PER = {"DEV": ("2020-01-01", "2022-12-31"), "TEST": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2026-12-31"), "2023+": ("2023-01-01", "2026-12-31")}
ROWS = []


def report(name, daily, note=""):
    daily = daily.fillna(0.0)
    r = {"strategy": name, "note": note}
    for k, (a, b) in PER.items():
        y = daily.loc[a:b]
        if len(y) < 60 or y.std() == 0:
            continue
        m = (1 + y).resample("ME").prod() - 1
        r.update({f"{k}_sharpe": y.mean() / y.std() * np.sqrt(365), f"{k}_ann": y.mean() * 365, f"{k}_posm": (m > 0).mean()})
    a = pd.concat([daily, CSTAR], axis=1).dropna().loc["2020":]
    r["corr_cstar"] = a.corr().iloc[0, 1]
    worst = CSTAR.loc["2020":].nsmallest(20).index
    r["mean_on_cstar_worst20"] = daily.reindex(worst).mean()
    ROWS.append(r)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def window_pnl(c5, o5, h5, l5, start_h, end_h, side=1, cost=5, maker=False):
    """Hold from start_h:00 to end_h:00 UTC each day (end_h may be next day if < start_h). Returns daily pnl (unit notional)."""
    days = c5.index.floor("D").unique()
    t0 = days + pd.Timedelta(hours=start_h)
    t1 = days + pd.Timedelta(hours=end_h + (24 if end_h <= start_h else 0))
    px0 = o5.reindex(t0).to_numpy(); px1 = o5.reindex(t1).to_numpy()
    gross = side * (px1 / px0 - 1)
    if not maker:
        net = gross - 2 * cost / 1e4
    else:   # limit at the bar-open price; filled only if the first 5-min bar trades >= 1 bp through it, else that leg is a taker fill
        lo0 = l5.reindex(t0).to_numpy(); hi0 = h5.reindex(t0).to_numpy(); lo1 = l5.reindex(t1).to_numpy(); hi1 = h5.reindex(t1).to_numpy()
        f0 = (lo0 <= px0 * (1 - 1e-4)) if side > 0 else (hi0 >= px0 * (1 + 1e-4))
        f1 = (hi1 >= px1 * (1 + 1e-4)) if side > 0 else (lo1 <= px1 * (1 - 1e-4))
        net = gross - np.where(f0, 2, 5) / 1e4 - np.where(f1, 2, 5) / 1e4
    return pd.Series(net, index=days).dropna()


def main():
    # ---------------- T1 / B2: evening window
    for coin in ("BTC", "ETH"):
        k = B.k5(coin)
        for maker in (False, True):
            report(f"T1 {coin} long 21-23 UTC {'maker' if maker else 'taker'}", window_pnl(k.close, k.open, k.high, k.low, 21, 23, 1, maker=maker))
    k = B.k5("BTC")
    ls = window_pnl(k.close, k.open, k.high, k.low, 21, 23, 1).add(window_pnl(k.close, k.open, k.high, k.low, 1, 5, -1), fill_value=0) / 2
    report("B2 BTC long 21-23 / short 01-05 UTC (taker)", ls)
    wk = k.index.floor("D").unique(); wk = wk[wk.dayofweek < 5]
    v2 = window_pnl(k.close, k.open, k.high, k.low, 20, 13, 1).reindex(wk)            # 20:00 -> 13:00 next day (hour grid)
    v2 = v2.add(window_pnl(k.close, k.open, k.high, k.low, 13, 20, -1).reindex(wk), fill_value=0) / 2
    report("B2 variant BTC long 20->13, short 13->20 UTC weekdays (taker)", v2, "13:30 approximated by 13:00")
    alts = [c for c in B.coins() if c not in ("BTC",)]
    panel = pd.concat([window_pnl(B.k5(c).close, B.k5(c).open, B.k5(c).high, B.k5(c).low, 21, 23, 1) for c in alts], axis=1).mean(axis=1)
    report("T1 check: 19 other coins long 21-23 UTC (taker, equal weight)", panel)


    # ---------------- B1: noise-area intraday trend (Zarattini et al. 2024 adapted to 24h UTC day)
    def noise_area(coin, lookback=14, vol_target=0.10, cost=5):
        k = B.k5(coin)
        c30 = k.close.resample("30min").last(); o_day = k.open.resample("1D").first()
        pv = (k.close * k.volume).resample("30min").sum(); vv = k.volume.resample("30min").sum()
        df = pd.DataFrame({"c": c30, "pv": pv, "v": vv}).dropna()
        df["day"] = df.index.floor("D"); df["slot"] = (df.index.hour * 2 + df.index.minute // 30).astype(int)
        df["o"] = o_day.reindex(df["day"]).to_numpy()
        df["move"] = (df.c / df.o - 1).abs()
        piv = df.pivot_table(index="day", columns="slot", values="move")
        sigma = piv.rolling(lookback, min_periods=lookback).mean().shift(1)            # same slot, previous 14 days
        df["sig"] = sigma.stack().reindex(pd.MultiIndex.from_arrays([df.day, df.slot])).to_numpy()
        df["vwap"] = df.groupby("day").pv.cumsum() / df.groupby("day").v.cumsum()
        dret = k.close.resample("1D").last().pct_change()
        lev = (vol_target / (dret.rolling(14).std() * np.sqrt(365))).clip(upper=2.0).shift(1)
        out = {}
        for day, g in df.groupby("day"):
            if g.sig.isna().all() or day not in lev.index or np.isnan(lev.get(day, np.nan)):
                continue
            pos = 0; pnl = 0.0; prev = g.o.iloc[0]
            for c, s, vw in zip(g.c.to_numpy(), g.sig.to_numpy(), g.vwap.to_numpy()):
                pnl += pos * (c / prev - 1); prev = c
                if np.isnan(s):
                    continue
                up, dn = g.o.iloc[0] * (1 + s), g.o.iloc[0] * (1 - s)
                new = pos
                if pos == 0:
                    new = 1 if c > up else (-1 if c < dn else 0)
                elif pos == 1 and c < max(up, vw):
                    new = -1 if c < dn else 0
                elif pos == -1 and c > min(dn, vw):
                    new = 1 if c > up else 0
                if new != pos:
                    pnl -= abs(new - pos) * cost / 1e4; pos = new
            pnl -= abs(pos) * cost / 1e4                                              # flat at the end of the day
            out[day] = pnl * lev[day]
        return pd.Series(out)


    na = {c: noise_area(c) for c in ("BTC", "ETH")}
    for c in na:
        report(f"B1 noise-area intraday trend {c} (taker 5 bp, 10% vol)", na[c])
    report("B1 noise-area BTC+ETH equal weight", pd.concat(na.values(), axis=1).mean(axis=1))


    # ---------------- T6: premium outside +-0.05% clamp -> reversal next 8h (perp vs index)
    def premium_rev(coin, thr=0.0005, hold=8, cost=5):
        p = B.premium(coin)["close"]
        c = B.k5(coin).close.resample("1h").last()
        sig = pd.Series(np.where(p > thr, -1, np.where(p < -thr, 1, 0)), index=p.index).reindex(c.index).fillna(0)
        pos = sig.where(sig != 0).ffill(limit=hold - 1).fillna(0)                      # hold up to 8 h after the last signal
        r = c.pct_change().shift(-1)                                                    # signal at the close of hour t -> next hour
        pnl = pos * r - pos.diff().abs().fillna(0) * cost / 1e4
        return pnl.groupby(pnl.index.floor("D")).sum()


    pr = {c: premium_rev(c) for c in B.coins()}
    report("T6 premium-bound reversion, 20 coins equal weight", pd.concat(pr.values(), axis=1).mean(axis=1))
    report("T6 premium-bound reversion, BTC", pr["BTC"])


    # ---------------- T8: Gao first 30 min -> last 30 min on BTC 24h UTC day ; T7 Wen pairs (confirmatory)
    def gao(coin, cost=5):
        c = B.k5(coin).close; o = B.k5(coin).open
        days = c.index.floor("D").unique()
        first = c.reindex(days + pd.Timedelta(minutes=25)).to_numpy() / o.reindex(days).to_numpy() - 1
        last = c.reindex(days + pd.Timedelta(minutes=1435)).to_numpy() / o.reindex(days + pd.Timedelta(minutes=1410)).to_numpy() - 1
        pos = np.sign(first)
        return pd.Series(pos * last - (pos != 0) * 2 * cost / 1e4, index=days).dropna()


    report("T8 Gao first->last half hour BTC (taker)", gao("BTC"))
    h = B.k5("BTC").close.resample("1h").last().pct_change()
    R = pd.DataFrame({"r": h, "d": h.index.floor("D"), "hr": h.index.hour}).pivot_table(index="d", columns="hr", values="r")
    pairs = [(3, 5, -1), (3, 15, -1), (8, 22, 1), (12, 13, -1), (22, 23, -1)]
    legs = [(sg * np.sign(R[i - 1]) * R[j - 1] - 2 * 5 / 1e4 * (R[i - 1] != 0)) for i, j, sg in pairs]
    report("T7 Wen et al. 5 effective hour pairs BTC Binance perp (taker)", pd.concat(legs, axis=1).mean(axis=1))

    out = pd.DataFrame(ROWS); out.to_csv(ROOT / "results/gen57_timing.csv", index=False)


if __name__ == "__main__":
    main()
