"""Hourly P&L of the crypto sleeves on Binance perps (fractions of equity at unit size), for portfolio and prop analysis.
C* + BTC leads (frozen weights, 7.5 bp, real funding), funding carry XS (7d avg, hold 1d), liquidation-cascade buy (max 3 open,
0.2 notional each), ETH 21-23 UTC with maker fills. Import-safe; results cached in results/cache_sleeves_hourly.parquet."""
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import binance_pack as B

CACHE = ROOT / "results" / "cache_sleeves_hourly.parquet"
END = os.environ.get("QPL_END", "2026-09-30 23:00")       # paper trading sets this to the last completed hour


def _hourly_close(coins):
    return B.panel("close", "1h", coins).loc[:END]


def _funding_hourly(coins, index):
    f = B.funding_panel(coins).copy(); f.index = f.index - pd.Timedelta(hours=1)          # charged in the bar that ends at settlement
    return f.groupby(level=0).sum().reindex(index).fillna(0.0)


def _from_daily_weights(w_daily, coins, cost_bps):
    H = _hourly_close(coins); r = H.pct_change(fill_method=None).fillna(0.0)
    w_daily = w_daily.reindex(w_daily.index.append(pd.DatetimeIndex([w_daily.index[-1] + pd.Timedelta(days=1)])))  # room for the next day
    held_d = w_daily.reindex(columns=coins).shift(1)                                       # decided at the close of d-1
    held = held_d.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0)
    turn = held_d.fillna(0.0).diff().abs().sum(axis=1).reindex(H.index.floor("D")).set_axis(H.index).where(H.index.hour == 0, 0.0)
    fund = _funding_hourly(coins, H.index)
    return (held * r).sum(axis=1) - (held * fund).sum(axis=1) - turn.fillna(0.0) * cost_bps / 1e4


def cstar_weights():
    """C* daily target weights (row d = decided at the close of day d, held during day d+1), MAJ10 columns."""
    import gen52_optimize as G
    from qpl.lab import strategies as S
    cs = S.CStarTrend(); W, _ = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0)
    return W[B.MAJ10]


def cstar():
    return _from_daily_weights(cstar_weights(), B.MAJ10, 7.5)


def carry():
    C = B.coins(); P = B.panel("close", "1D", C)
    F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D")
    fs = F.groupby(level=0).sum().reindex(P.index).rolling(7).mean(); listed = P.notna().cumsum() >= 60
    rk = (-fs).where(listed).rank(axis=1, pct=True)
    w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
    return _from_daily_weights(w.fillna(0.0), C, 5)


def premium_carry(look=7, hold=7):
    """Gen61 G4 (passed): long lowest third / short highest third of the 7-day average premium index, rebalance weekly."""
    return _from_daily_weights(premium_weights(look, hold), B.coins(), 5)


def premium_weights(look=7, hold=7):
    """Daily target weights of premium carry (row d = decided at the close of day d)."""
    C = B.coins(); P = B.panel("close", "1D", C)
    prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


def cascade(hold=12, k=3.0, cost=5, max_open=3, size=0.2, limit=0.0, through=0.0, doi_th=0.05, positions=False, live=False,
            coins=None, maker_fee=2.0, cost_map=None):
    """Liquidation-cascade buy. live=True (paper trading): the entry fee is booked in the fill hour (known then) instead of the
    signal hour; P&L is otherwise identical. positions=True also returns hourly notional per coin and, in .attrs, the trades
    still open at the end of the data and the signals of the last hour (limit orders for the next hour)."""
    import gen57_cascade_hourly as CH
    trades, pending = [], []
    for coin in (coins or B.coins()):
        d = CH.hourly(coin).loc[:END]; c, lo, hi, v, o = d.c, d.lo, d.hi, d.v, d.oi
        r = c.pct_change(); sd = r.rolling(720).std().shift(1); vq = v.rolling(720).quantile(0.95).shift(1); doi = o.pct_change()
        atr = (hi - lo).rolling(14).mean(); ev = (r < -k * sd) & (doi < -doi_th) & (v > vq)
        cv, lov, atv = c.to_numpy(), lo.to_numpy(), atr.to_numpy(); n = len(cv)
        for t in np.flatnonzero(ev.to_numpy()):
            if t + 1 >= n:
                pending.append({"coin": coin, "signal_hour": str(c.index[t]), "limit_price": float(cv[t] * (1 - limit)),
                                "stop": float(lov[t] - atv[t]), "fill_rule": f"fills only if price trades {through:.1%} below the limit"})
                continue
            stop = lov[t] - atv[t]; ex = None
            entry = cv[t]
            if limit > 0:                                         # Gen67 E1: limit buy `limit` below the event close, valid 1 hour
                entry = cv[t] * (1 - limit)
                if lov[t + 1] > entry * (1 - through):              # Gen68 L1: require a trade-through, not just a touch
                    continue
            for j in range(t + 1, min(t + 1 + hold, n)):
                if lov[j] <= stop:
                    ex = (j, min(stop, entry)); break
            still_open = ex is None and t + hold > n - 1            # data ends before the planned exit: no exit booked yet
            if ex is None:
                ex = (min(t + hold, n - 1), cv[min(t + hold, n - 1)])
            if limit > 0:                                         # mark to market from the limit price
                seq = [entry] + [cv[m] for m in range(t + 1, ex[0])] + [ex[1]]
                path = [(c.index[t + 1 + i] if t + 1 + i < ex[0] else c.index[ex[0]], seq[i + 1] / seq[i] - 1) for i in range(len(seq) - 1)]
            else:
                path = [(c.index[m], cv[m] / cv[m - 1] - 1) for m in range(t + 1, ex[0])] + [(c.index[ex[0]], ex[1] / cv[ex[0] - 1] - 1)]
            trades.append((c.index[t], c.index[ex[0]], path, limit > 0, coin, still_open,
                           {"coin": coin, "entry": float(entry), "stop": float(stop), "planned_exit": str(c.index[t] + pd.Timedelta(hours=hold))}))
    trades.sort(key=lambda x: x[0])
    idx = _hourly_close(["BTC"]).index; pnl = pd.Series(0.0, index=idx); open_ex = []
    pos = pd.DataFrame(0.0, index=idx, columns=B.coins()) if positions else None
    open_now = []
    for t0, t1, path, maker, coin, still_open, info in trades:
        open_ex = [e for e in open_ex if e > t0]
        if len(open_ex) >= max_open:
            continue
        open_ex.append(pd.Timestamp.max if still_open else t1)
        if still_open:
            open_now.append({**info, "size": size})
        if positions:
            pos.loc[t0 + pd.Timedelta(hours=1):t1, coin] += size        # hours whose return the trade earns
        t_fee = t0 + pd.Timedelta(hours=1) if live else t0
        c_in = (cost_map or {}).get(coin, maker_fee if maker else cost); c_out = (cost_map or {}).get(coin, cost)
        if t_fee in pnl.index:
            pnl.loc[t_fee] -= size * c_in / 1e4
        for ts, rr in path:
            if ts in pnl.index:
                pnl.loc[ts] += size * rr
        if t1 in pnl.index and not still_open:
            pnl.loc[t1] -= size * c_out / 1e4
    if positions:
        free = max_open - len(open_now)
        pos.attrs = {"open_trades": open_now, "pending_signals": pending[:max(free, 0)]}
        return pnl, pos
    return pnl


def eth_evening():
    k = B.k5("ETH"); h = k.close.resample("1h").last().loc[:END]; r = h.pct_change().fillna(0.0)
    days = h.index.floor("D").unique()
    t0 = days + pd.Timedelta(hours=21); t1 = days + pd.Timedelta(hours=23)
    o0, l0 = k.open.reindex(t0).to_numpy(), k.low.reindex(t0).to_numpy(); o1, h1 = k.open.reindex(t1).to_numpy(), k.high.reindex(t1).to_numpy()
    c0 = np.where(l0 <= o0 * (1 - 1e-4), 2, 5) / 1e4; c1 = np.where(h1 >= o1 * (1 + 1e-4), 2, 5) / 1e4
    pnl = r.where(r.index.hour.isin([21, 22]), 0.0).copy()
    pnl.loc[pnl.index.intersection(t0)] -= pd.Series(c0, index=t0).reindex(pnl.index.intersection(t0)).fillna(0).to_numpy()
    e22 = t0 + pd.Timedelta(hours=1)
    pnl.loc[pnl.index.intersection(e22)] -= pd.Series(c1, index=e22).reindex(pnl.index.intersection(e22)).fillna(0).to_numpy()
    return pnl


def trend4h(coins=("BTC", "ETH", "SOL"), n_in=20, n_out=10, cost=5, positions=False):
    """Gen63 I6 / Gen69: 4-hour breakout trend (long-short), per coin 10% vol target (cap 2), funding; hourly P&L, equal weight."""
    out, held_all = [], {}
    for coin in coins:
        k = B.k5(coin); c4 = k.close.resample("4h").last().loc[:END]; h4 = k.high.resample("4h").max().loc[c4.index]; l4 = k.low.resample("4h").min().loc[c4.index]
        hi_in, lo_in = h4.rolling(n_in).max().shift(1).to_numpy(), l4.rolling(n_in).min().shift(1).to_numpy()
        hi_out, lo_out = h4.rolling(n_out).max().shift(1).to_numpy(), l4.rolling(n_out).min().shift(1).to_numpy()
        cv = c4.to_numpy(); pos = np.zeros(len(cv)); p = 0
        for i in range(len(cv)):
            if p == 0:
                p = 1 if cv[i] > hi_in[i] else (-1 if cv[i] < lo_in[i] else 0)
            elif p == 1 and cv[i] < lo_out[i]:
                p = 0
            elif p == -1 and cv[i] > hi_out[i]:
                p = 0
            pos[i] = p
        r4 = c4.pct_change().fillna(0)
        lev = (0.10 / (r4.rolling(6 * 30).std().shift(1) * np.sqrt(6 * 365))).clip(upper=2.0).fillna(0)
        held4 = pd.Series(pos, index=c4.index) * lev                       # decided at the close of each 4h bar ...
        held4.index = held4.index + pd.Timedelta(hours=4)                   # ... i.e. known at bar open + 4h (no look-ahead)
        h1 = k.close.resample("1h").last().loc[:END]; r1 = h1.pct_change().fillna(0)
        held = held4.reindex(h1.index, method="ffill").fillna(0)            # applies to hourly bars opening at/after that time
        f = B.funding(coin).copy(); f.index = f.index - pd.Timedelta(hours=1)
        f = f.groupby(level=0).sum().reindex(h1.index).fillna(0.0)
        out.append(held * r1 - held * f - held.diff().abs().fillna(0) * cost / 1e4)
        if positions:                                                       # include the next hour (known at the last close)
            ext = h1.index.append(pd.DatetimeIndex([h1.index[-1] + pd.Timedelta(hours=1)]))
            held_all[coin] = held4.reindex(ext, method="ffill").fillna(0) / len(coins)
    pnl = pd.concat(out, axis=1).fillna(0).mean(axis=1)
    return (pnl, pd.DataFrame(held_all).fillna(0.0)) if positions else pnl


def all_sleeves(refresh=False):
    if CACHE.exists() and not refresh:
        return pd.read_parquet(CACHE)
    df = pd.DataFrame({"C*": cstar(), "funding carry": carry(), "premium carry": premium_carry(), "cascade": cascade(), "cascade limit": cascade(limit=0.005),
                       "cascade limit strict": cascade(limit=0.005, through=0.001), "trend 4h": trend4h(),
                       "ETH evening": eth_evening()}).fillna(0.0)
    df.to_parquet(CACHE)
    return df


def to_daily(h: pd.Series) -> pd.DataFrame:
    """hourly returns -> daily net / worst / best (intraday path, UTC days)."""
    rows = []
    for d, g in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + g.to_numpy())
        rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


def portfolio_v3(cols=("C*", "premium carry", "cascade limit strict"), vol=0.15):
    """Gen68 portfolio v3: sleeves at equal risk (10% each on their own history), portfolio scaled daily to `vol` with trailing
    30-day realised vol (cap 1.5x, decided at the previous close), as an hourly return series from 2022."""
    H = all_sleeves()[list(cols)].loc["2021-12-01":"2026-09-30 23:00"]
    D = H.groupby(H.index.floor("D")).sum()
    ph = H.mul(pd.Series({c: 0.10 / (D[c].std() * np.sqrt(365)) for c in D})).mean(axis=1)
    pdly = ph.groupby(ph.index.floor("D")).sum()
    ph = ph * vol / (pdly.loc["2022":].std() * np.sqrt(365)); pdly = ph.groupby(ph.index.floor("D")).sum()   # same level as v1/v2
    mult = (vol / (pdly.rolling(30).std().shift(1) * np.sqrt(365))).clip(upper=1.5)
    out = (ph * mult.reindex(ph.index.floor("D")).set_axis(ph.index)).loc["2022-01-01":].dropna()
    od = out.groupby(out.index.floor("D")).sum()
    return out * vol / (od.std() * np.sqrt(365))                      # realised vol back to `vol` (descriptive, like v1/v2)


def weiss_expiry(coins=("BTC", "ETH"), positions=False):
    """Gen70 W1: on the last Friday of each month, at 08:00 UTC take -sign(07:00-08:00 return), close at 10:00; taker 5 bp per side;
    unit notional per coin, averaged over BTC and ETH. The trade's P&L (both legs, both fees) is booked in the 10:00 bar, the first
    moment it is fully known; daily totals equal Gen70."""
    out, held = [], {}
    for coin in coins:
        k = B.k5(coin); h = k.close.resample("1h").last().loc[:END]; o = k.open
        pnl = pd.Series(0.0, index=h.index); held[coin] = pd.Series(0.0, index=h.index)
        days = pd.date_range("2020-01-03", pd.Timestamp(END).normalize(), freq="W-FRI")
        days = days[(days + pd.Timedelta(days=7)).month != days.month]
        for d in days:
            t7, t8, t9, t10 = (d + pd.Timedelta(hours=x) for x in (7, 8, 9, 10))
            if not all(t in o.index for t in (t7, t8)):
                continue
            pre = o[t8] / o[t7] - 1
            if pre == 0:
                continue
            side = -np.sign(pre); held[coin][[t for t in (t8, t9) if t in held[coin].index]] = side / len(coins)
            if t10 in o.index and t10 in pnl.index:              # booked once both legs are known (10:00 bar), same day
                pnl[t10] += side * (o[t9] / o[t8] - 1) - 5 / 1e4 + side * (o[t9] / o[t8]) * (o[t10] / o[t9] - 1) - 5 / 1e4
        out.append(pnl)
    pnl = pd.concat(out, axis=1).fillna(0).mean(axis=1)
    return (pnl, pd.DataFrame(held).fillna(0.0)) if positions else pnl


V5_SLEEVES = ("C*", "premium carry", "cascade limit strict", "trend 4h", "Weiss expiry")


def v5_sleeves(live=False):
    """Hourly P&L of the five v5 sleeves at their frozen settings (Gen72: defaults kept). live=True: costs booked when known."""
    return pd.DataFrame({"C*": cstar(), "premium carry": premium_carry(), "cascade limit strict": cascade(limit=0.005, through=0.001, live=live),
                         "trend 4h": trend4h(), "Weiss expiry": weiss_expiry()}).fillna(0.0)


def v5_weights(D, sleeves=V5_SLEEVES, weiss_scale=0.5):
    """Gen72 P1: point-in-time equal risk. At each month start, each live sleeve gets 0.10 / its trailing-365-day daily vol
    (annualised), divided by the number of live sleeves; Weiss expiry at half weight. Uses days before the month only."""
    W = pd.DataFrame(np.nan, index=D.index, columns=list(sleeves))
    for m in D.index[~D.index.to_period("M").duplicated()]:
        hist = D.loc[m - pd.Timedelta(days=365):m - pd.Timedelta(days=1)]
        live = [c for c in sleeves if (hist[c] != 0).sum() >= (6 if c == "Weiss expiry" else 30) and hist[c].std() > 0]
        if len(live) < 2:
            continue
        w = pd.Series(0.10 / (hist[live].std().to_numpy()), index=live) / len(live)
        if "Weiss expiry" in w:
            w["Weiss expiry"] *= weiss_scale
        W.loc[m, :] = 0.0; W.loc[m, w.index] = w.to_numpy()
    return W.ffill().fillna(0.0)


def portfolio_v5(H=None, vol=0.15, start="2022-01-01"):
    """Gen72 final portfolio v5 as an hourly return series (point-in-time, no final rescaling):
    sleeve weights from v5_weights, a level multiplier vol / trailing-365-day realised vol of the weighted sum, and 30-day vol
    targeting (cap 1.5x); both multipliers use days before the current one. Returns (hourly returns, daily sleeve weights,
    daily total multiplier)."""
    H = v5_sleeves() if H is None else H
    D = H.groupby(H.index.floor("D")).sum()
    W = v5_weights(D, list(H.columns))
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index)
    raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1)
    x1 = rawd * lvl
    tgt = (vol / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1)
    mult = (lvl * tgt).loc[start:]
    ph = (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()
    return ph, W, mult


def delev_bounce_weights(coins=("BTC", "ETH"), th=0.10, hold=2, size=0.5):
    """Gen89 H4 / Gen90 (passed): daily target weights (row d = decided at the close of d, held during d+1). Long `size` in a coin for
    `hold` days when its open-interest value fell more than `th` over the 24 hours to 23:55 UTC AND its price fell over the same 24h."""
    days = pd.date_range("2021-12-01", pd.Timestamp(END).normalize())
    w = pd.DataFrame(0.0, index=days, columns=list(coins))
    for c in coins:
        m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last().ffill(); px = B.k5(c).close.resample("1h").last()
        mid = days + pd.Timedelta(days=1); t = mid - pd.Timedelta(minutes=5)
        f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
        sig = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -th) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=days)
        w[c] = sig.astype(float).rolling(hold, min_periods=1).max() * size
    return w


def delev_bounce(coins=("BTC", "ETH")):
    """Hourly P&L of the deleveraging bounce at Binance perp costs (taker 5 bp, funding)."""
    return _from_daily_weights(delev_bounce_weights(coins), list(coins), 5)
