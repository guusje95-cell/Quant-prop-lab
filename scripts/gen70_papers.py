"""Gen70 (config/gen70_protocol.json): full-text replications of four uploaded papers on the Binance USD-M pack.
W  Weiss et al. option-expiry reversal | A  Bui & Nguyen AdaptiveTrend | D  Dhanya MD own-history factor books | C  CTREND.
Writes results/gen70_papers.csv and results/cache_gen70_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen57_timing as T
import crypto_sleeves as CS
from qpl.lab import binance_pack as B

warnings.filterwarnings("ignore")
C = B.coins(); END = "2026-09-30"
P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
QV = B.panel("quote_volume", "1D", C).loc[:END]
F = B.funding_panel(C); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D"); FD = F.groupby(level=0).sum().reindex(P.index)
listed = P.notna().cumsum() >= 60
SUN = P.index[P.index.dayofweek == 6]                     # decision at Sunday close = Monday 00:00 UTC
cands = {}


def pnl_w(w, cost=5):
    held = w.reindex(P.index).ffill().fillna(0.0).shift(1).fillna(0.0)
    return (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1) * cost / 1e4


def weekly_to_daily(w):
    return w.reindex(P.index).ffill().fillna(0.0)


def book(score, frac=0.2, wts=None):
    """Dollar-neutral long top `frac` / short bottom `frac` (each leg sums to 1); weights within a leg equal or by `wts`."""
    s = score.where(listed.reindex(score.index)); n = (s.notna().sum(axis=1) * frac).clip(lower=1).round()
    rk_hi = s.rank(axis=1, ascending=False, method="first"); rk_lo = s.rank(axis=1, method="first")
    hi = rk_hi.le(n, axis=0) & s.notna(); lo = rk_lo.le(n, axis=0) & s.notna()
    base = pd.DataFrame(1.0, index=s.index, columns=s.columns) if wts is None else wts.reindex(s.index).fillna(0.0)
    lw = (base * hi).div((base * hi).sum(axis=1), axis=0); sw = (base * lo).div((base * lo).sum(axis=1), axis=0)
    ok = s.notna().sum(axis=1) >= 10                       # need a real cross-section
    return (lw - sw).fillna(0.0).where(ok, 0.0)


# ---------------------------------------------------------------- W: Weiss et al. expiry reversal
def weiss(coin):
    k = B.k5(coin).loc[:END]; o = k.open
    days = P.index
    o7, o8, o10 = (o.reindex(days + pd.Timedelta(hours=h)).to_numpy() for h in (7, 8, 10))
    pre = pd.Series(o8 / o7 - 1, index=days); post = pd.Series(o10 / o8 - 1, index=days)
    return pre, post


def weiss_rule(mask, pre, post):
    trade = (-np.sign(pre) * post - 2 * 5 / 1e4).where(mask & pre.ne(0) & post.notna(), 0.0)
    return trade.fillna(0.0)


fri = pd.Series(P.index.dayofweek == 4, index=P.index)
last_fri = fri & ((P.index + pd.Timedelta(days=7)).month != P.index.month)
W = {"W1": [], "W2": [], "W3": [], "W4": []}
for c in ("BTC", "ETH"):
    pre, post = weiss(c)
    big = pre.abs() > pre.abs().rolling(365, min_periods=180).quantile(0.9).shift(1)
    W["W1"].append(weiss_rule(last_fri, pre, post)); W["W2"].append(weiss_rule(fri, pre, post))
    W["W3"].append(weiss_rule(big, pre, post)); W["W4"].append(weiss_rule(pd.Series(True, index=P.index), pre, post))
names = {"W1": "W1 Weiss reversal, last Friday (PRIMARY)", "W2": "W2 Weiss reversal, every Friday",
         "W3": "W3 Weiss reversal, big pre-move days", "W4": "W4 Weiss reversal, every day (placebo)"}
for k_, v in W.items():
    cands[names[k_]] = (v[0] + v[1]) / 2


# ---------------------------------------------------------------- A: AdaptiveTrend
GRID = [(L, th, a) for L in (12, 28, 56) for th in (0.02, 0.05, 0.10) for a in (2.0, 2.5, 3.0)]


def bars6(coin):
    k = B.k5(coin).loc[:END]
    c = k.close.resample("6h").last(); h = k.high.resample("6h").max(); l = k.low.resample("6h").min()
    ok = c.notna(); c, h, l = c[ok], h[ok], l[ok]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return c, tr.rolling(14).mean()


def sim(c, atr, L, th, a, side):
    """side +1 long-only, -1 short-only, 0 both. Returns position held during the next bar (decided at bar close)."""
    cv, av = c.to_numpy(), atr.to_numpy(); mom = (c / c.shift(L) - 1).to_numpy()
    pos = np.zeros(len(cv)); p = 0; stop = np.nan
    for i in range(len(cv)):
        if p == 1:
            stop = max(stop, cv[i] - a * av[i])
            if cv[i] < stop:
                p = 0
        elif p == -1:
            stop = min(stop, cv[i] + a * av[i])
            if cv[i] > stop:
                p = 0
        if p == 0 and np.isfinite(mom[i]) and np.isfinite(av[i]):
            if side >= 0 and mom[i] > th:
                p, stop = 1, cv[i] - a * av[i]
            elif side <= 0 and mom[i] < -th:
                p, stop = -1, cv[i] + a * av[i]
        pos[i] = p
    return pd.Series(pos, index=c.index)


def adaptive():
    rets, fund, longs, shorts, fixed = {}, {}, {}, {}, {}
    for coin in C:
        c, atr = bars6(coin)
        rets[coin] = c.pct_change().fillna(0.0)
        fund[coin] = B.funding(coin).reindex(c.index).fillna(0.0).shift(-1).fillna(0.0)  # settlement at the end of the bar
        longs[coin] = {g: sim(c, atr, *g, 1) for g in GRID}
        shorts[coin] = {g: sim(c, atr, *g, -1) for g in GRID}
        fixed[coin] = sim(c, atr, 28, 0.05, 2.5, 0)
        print("A sims", coin, flush=True)
    idx = pd.DatetimeIndex(sorted(set().union(*[r.index for r in rets.values()])))
    Rr = pd.DataFrame(rets).reindex(idx).fillna(0.0); Ff = pd.DataFrame(fund).reindex(idx).fillna(0.0)

    def cell_sharpe(pos, r, f, a, b):
        x = (pos.shift(1) * r - pos.shift(1) * f - pos.diff().abs() * 5 / 1e4).loc[a:b]
        return x.mean() / x.std() * np.sqrt(4 * 365) if x.std() > 0 else np.nan

    months = pd.date_range("2020-03-01", END, freq="MS")
    size = QV.rolling(30, min_periods=20).mean()
    Wt = pd.DataFrame(0.0, index=idx, columns=C)
    for m in months:
        prev_a, prev_b = m - pd.offsets.MonthBegin(1), m - pd.Timedelta(hours=6)
        sz = size.loc[:m - pd.Timedelta(days=1)].iloc[-1].dropna()
        if len(sz) < 10:
            continue
        rank = sz.rank(ascending=False)
        lc, sc = rank[rank <= 15].index, rank[rank > len(sz) - 5].index
        sel_l, sel_s = {}, {}
        for coin in lc:
            sh = {g: cell_sharpe(longs[coin][g], Rr[coin], Ff[coin], prev_a, prev_b) for g in GRID}
            g, v = max(sh.items(), key=lambda kv: -np.inf if np.isnan(kv[1]) else kv[1])
            if v >= 1.3:
                sel_l[coin] = g
        for coin in sc:
            sh = {g: cell_sharpe(shorts[coin][g], Rr[coin], Ff[coin], prev_a, prev_b) for g in GRID}
            g, v = max(sh.items(), key=lambda kv: -np.inf if np.isnan(kv[1]) else kv[1])
            if v >= 1.7:
                sel_s[coin] = g
        nxt = m + pd.offsets.MonthBegin(1) - pd.Timedelta(hours=6)
        for coin, g in sel_l.items():
            Wt.loc[m:nxt, coin] += longs[coin][g].reindex(idx).loc[m:nxt].fillna(0) * 0.7 / len(sel_l)
        for coin, g in sel_s.items():
            Wt.loc[m:nxt, coin] += shorts[coin][g].reindex(idx).loc[m:nxt].fillna(0) * 0.3 / len(sel_s)

    def pnl6(w):
        held = w.shift(1).fillna(0.0)
        x = (held * Rr - held * Ff).sum(axis=1) - w.diff().abs().sum(axis=1).fillna(0) * 5 / 1e4
        return x.groupby(x.index.floor("D")).sum().reindex(P.index).fillna(0.0)

    Fx = pd.DataFrame({c: fixed[c] for c in C}).reindex(idx).fillna(0.0)
    Fx = Fx.clip(lower=0) * 0.7 / len(C) + Fx.clip(upper=0) * 0.3 / len(C)
    return pnl6(Wt), pnl6(Fx)


a1, a2 = adaptive()
cands["A1 AdaptiveTrend, monthly selection 70/30 (PRIMARY)"] = a1
cands["A2 AdaptiveTrend, fixed params, all coins 70/30"] = a2


# ---------------------------------------------------------------- D: Dhanya MD own-history factor books
def hourly(coin):
    k = B.k5(coin).loc[:END]
    g = k.resample("1h")
    h = pd.DataFrame({"close": g.close.last(), "v": g.volume.sum(), "qv": g.quote_volume.sum(), "b": g.taker_buy_volume.sum()})
    return k, h.dropna()


def raw_factors(coin):
    k, h = hourly(coin)
    wk = lambda x: x.index.floor("D") + pd.to_timedelta((6 - x.index.floor("D").dayofweek) % 7, unit="D")   # week label = Sunday
    r = h.close.pct_change()
    lab = wk(h)
    out = {}
    v_w = h.qv.groupby(lab).sum()
    out["AVOL"] = -np.log(v_w / v_w.shift(1).rolling(12).mean())
    # smart money Q
    sc = r.abs() / np.sqrt(h.v.replace(0, np.nan))

    def qf(df):
        top = df[df.sc >= df.sc.quantile(0.8)]
        return (top.qv.sum() / top.v.sum()) / (df.qv.sum() / df.v.sum()) if len(top) and df.v.sum() > 0 else np.nan
    out["Q"] = pd.DataFrame({"sc": sc, "qv": h.qv, "v": h.v, "lab": lab}).dropna().groupby("lab").apply(qf)
    rp, rn, r2 = (r.clip(lower=0) ** 2).groupby(lab).sum(), (r.clip(upper=0) ** 2).groupby(lab).sum(), (r ** 2).groupby(lab).sum()
    out["RSJ"] = -(rp - rn) / r2
    out["OFI"] = (2 * h.b - h.v).groupby(lab).sum() / h.v.groupby(lab).sum()
    day = h.index.floor("D")
    dc = pd.DataFrame({"c": h.close, "v": h.v, "d": day}).groupby("d").apply(lambda d: d.c.corr(d.v) if len(d) >= 20 else np.nan)
    dlab = dc.index + pd.to_timedelta((6 - dc.index.dayofweek) % 7, unit="D")
    out["CPVm"] = -dc.groupby(dlab).mean(); out["CPVv"] = -dc.groupby(dlab).std()
    # trade-size distribution from 5m bars
    t = k[(k.volume > 0) & (k["count"] > 0)]
    lt = np.log(t.volume / t["count"]); buy = t.taker_buy_volume > 0.5 * t.volume
    d5 = t.index.floor("D")
    kurt = lt.groupby(d5).apply(lambda x: x.kurt() if len(x) >= 20 else np.nan)
    sk_b = lt[buy].groupby(d5[buy]).apply(lambda x: x.skew() if len(x) >= 20 else np.nan)
    sk_s = lt[~buy].groupby(d5[~buy]).apply(lambda x: x.skew() if len(x) >= 20 else np.nan)
    asym = (sk_b - sk_s)
    lk = lambda s: s.index + pd.to_timedelta((6 - s.index.dayofweek) % 7, unit="D")
    out["TKU"] = kurt.groupby(lk(kurt)).mean()
    ta = asym.groupby(lk(asym)).mean(); out["TSKD"] = ta.diff()
    # positioning
    m = B.metrics(coin).loc[:END]
    if len(m):
        ml = m.index.floor("D"); ml = ml + pd.to_timedelta((6 - ml.dayofweek) % 7, unit="D")
        top = m.sum_toptrader_long_short_ratio.groupby(ml).mean(); allr = m.count_long_short_ratio.groupby(ml).mean()
        oi = m.sum_open_interest.groupby(ml).last()
        out["WRspread"] = -(top - allr); out["TopChg"] = -top.diff()
        cw = h.close.groupby(lab).last()
        out["Quad"] = -np.sign(cw.pct_change()).reindex(oi.index) * np.log(oi).diff()
    df = pd.DataFrame(out)
    df = df[df.index <= pd.Timestamp(END)]
    return df.reindex(SUN)


def dhanya():
    raw = {}
    for coin in C:
        raw[coin] = raw_factors(coin); print("D factors", coin, flush=True)
    facs = ["AVOL", "Q", "RSJ", "OFI", "CPVm", "CPVv", "WRspread", "TopChg", "Quad", "TKU", "TSKD"]
    lw = listed.reindex(SUN)
    fw = FD.rolling(7).sum().reindex(SUN).where(lw)
    fr = fw.rank(axis=1, pct=True); fn = fw.notna().sum(axis=1)
    fscore = ((fr.mul(fn, axis=0) - 0.5).div(fn, axis=0) - 0.5) * 2

    def own_rank(s):
        vals = s.to_numpy(); out = np.full(len(vals), np.nan)
        for i in range(len(vals)):
            if not np.isfinite(vals[i]):
                continue
            win = vals[max(0, i - 52):i]; win = win[np.isfinite(win)]
            if len(win) < 26:
                continue
            n = len(win) + 1; rk = (win < vals[i]).sum() + 0.5 * (win == vals[i]).sum() + 1
            out[i] = ((rk - 0.5) / n - 0.5) * 2
        return pd.Series(out, index=s.index)

    books_ts, books_xs = {}, {}
    for f in facs:
        X = pd.DataFrame({c: raw[c][f] for c in C}).replace([np.inf, -np.inf], np.nan).where(lw)
        Xs = X.rolling(20, min_periods=20).mean()
        ts = Xs.apply(own_rank)
        xr = Xs.rank(axis=1, pct=True); xn = Xs.notna().sum(axis=1)
        xs = ((xr.mul(xn, axis=0) - 0.5).div(xn, axis=0) - 0.5) * 2
        books_ts[f] = book(ts - fscore.fillna(0).where(ts.notna()))
        books_xs[f] = book(xs - fscore.fillna(0).where(xs.notna()))

    def combine(books):
        br = {f: pnl_w(weekly_to_daily(w), cost=0).resample("W-SUN").sum() for f, w in books.items()}
        br = pd.DataFrame(br).reindex(SUN)
        active = pd.DataFrame({f: books[f].abs().sum(axis=1) > 0 for f in books})
        vol = br.where(active.shift(1).fillna(False)).rolling(26, min_periods=13).std()
        inv = (1 / vol).where(active)                      # lagged: vol from returns up to this Sunday, used for next week
        a = inv.div(inv.sum(axis=1), axis=0).fillna(0.0)
        tot = sum(books[f].mul(a[f], axis=0) for f in books)
        return pnl_w(weekly_to_daily(tot), cost=4)

    return combine(books_ts), combine(books_xs), pnl_w(weekly_to_daily(book(-fscore)), cost=4)


d1, d2, d3 = dhanya()
cands["D1 Dhanya own-history 11 factor books (PRIMARY)"] = d1
cands["D2 Dhanya cross-sectional control"] = d2
cands["D3 Dhanya funding-rank book alone"] = d3


# ---------------------------------------------------------------- C: CTREND (Fieberg et al.)
def indicators():
    Hh = B.panel("high", "1D", C).loc[:END]; Ll = B.panel("low", "1D", C).loc[:END]; Cc = P; V = QV
    ind = {}
    d = Cc.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn); ind["rsi"] = rsi
    l14, h14 = Ll.rolling(14).min(), Hh.rolling(14).max()
    ind["stochK"] = (Cc - l14) / (h14 - l14); ind["stochD"] = ind["stochK"].rolling(3).mean()
    ind["stochRSI"] = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min())
    tp = (Hh + Ll + Cc) / 3; ma = tp.rolling(20).mean(); md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    ind["cci"] = (tp - ma) / (0.015 * md)
    for n in (3, 5, 10, 20, 50, 100, 200):
        ind[f"sma_{n}"] = Cc.rolling(n).mean() / Cc
        ind[f"volsma_{n}"] = V.rolling(n).mean() / V
    e12, e26 = Cc.ewm(span=12, adjust=False).mean(), Cc.ewm(span=26, adjust=False).mean()
    ind["macd"] = (e12 - e26) / e12; ind["macd_sig"] = ind["macd"] - ind["macd"].ewm(span=9, adjust=False).mean()
    v12, v26 = V.ewm(span=12, adjust=False).mean(), V.ewm(span=26, adjust=False).mean()
    ind["volmacd"] = (v12 - v26) / v12; ind["volmacd_sig"] = ind["volmacd"] - ind["volmacd"].ewm(span=9, adjust=False).mean()
    mfm = ((Cc - Ll) - (Hh - Cc)) / (Hh - Ll); ind["chaikin"] = (mfm * V).rolling(20).sum() / V.rolling(20).sum()
    mid = Cc.rolling(20).mean(); sd = Cc.rolling(20).std()
    ind["boll_low"] = (mid - 2 * sd) / Cc; ind["boll_mid"] = mid / Cc; ind["boll_high"] = (mid + 2 * sd) / Cc
    ind["boll_width"] = 4 * sd / mid
    assert len(ind) == 28
    return {k: v.replace([np.inf, -np.inf], np.nan).reindex(SUN) for k, v in ind.items()}


def ctrend():
    from sklearn.linear_model import ElasticNet
    ind = indicators(); lw = listed.reindex(SUN)
    wv = QV.rolling(30, min_periods=20).mean().reindex(SUN).where(lw)
    Z = {}
    for k, X in ind.items():
        X = X.where(lw & wv.notna()); r_ = X.rank(axis=1, pct=True); n = X.notna().sum(axis=1)
        Z[k] = (r_.mul(n, axis=0) - 0.5).div(n, axis=0) - 0.5
    Pw = P.reindex(SUN); fwd = (Pw.shift(-1) / Pw - 1).clip(upper=1.0)        # next-week return (known one week later)
    keys = list(Z); nT = len(SUN)
    # weekly univariate WLS slopes: return over (s, s+1] on z at s
    coef = np.full((nT, len(keys), 2), np.nan)
    for t in range(nT - 1):
        y = fwd.iloc[t]; w = wv.iloc[t]
        for j, k in enumerate(keys):
            x = Z[k].iloc[t]; ok = y.notna() & x.notna() & w.notna()
            if ok.sum() < 10:
                continue
            X_ = np.c_[np.ones(ok.sum()), x[ok].to_numpy()]; W_ = w[ok].to_numpy() / w[ok].sum()
            coef[t, j] = np.linalg.lstsq(X_ * np.sqrt(W_)[:, None], y[ok].to_numpy() * np.sqrt(W_), rcond=None)[0]
    sig_c1 = pd.DataFrame(np.nan, index=SUN, columns=C); sig_c2 = sig_c1.copy(); nsel = {}
    for t in range(53, nT):
        # slopes estimated with returns fully known by t: s in [t-52, t-1]
        cw = coef[t - 52:t]
        if np.isnan(cw).all(axis=(1, 2)).sum() > 26:
            continue
        cbar = np.nanmean(cw, axis=0)                                       # (J, 2) smoothed alpha, beta
        rows, ys, ws = [], [], []
        for s in range(t - 52, t):
            fc = np.column_stack([cbar[j, 0] + cbar[j, 1] * Z[k].iloc[s].to_numpy() for j, k in enumerate(keys)])
            y = fwd.iloc[s].to_numpy(); w = wv.iloc[s].to_numpy()
            ok = np.isfinite(fc).all(axis=1) & np.isfinite(y) & np.isfinite(w)
            rows.append(fc[ok]); ys.append(y[ok]); ws.append(w[ok] / w[ok].sum())
        Xf, yf, wf = np.vstack(rows), np.concatenate(ys), np.concatenate(ws)
        if len(yf) < 200:
            continue
        mu, sdv = Xf.mean(axis=0), Xf.std(axis=0); sdv[sdv == 0] = 1
        Xs_ = (Xf - mu) / sdv                                               # scale-free penalty; signs of theta unchanged
        amax = np.max(np.abs((Xs_ - np.average(Xs_, axis=0, weights=wf)).T @ (wf * (yf - np.average(yf, weights=wf))))) / 0.5
        best = (np.inf, None); n = len(yf)
        for a in np.geomspace(amax, amax * 1e-4, 40):
            m_ = ElasticNet(alpha=a, l1_ratio=0.5, max_iter=5000).fit(Xs_, yf, sample_weight=wf * n)
            rss = np.sum(wf * n * (yf - m_.predict(Xs_)) ** 2); kk = int((m_.coef_ != 0).sum()) + 1
            aicc = n * np.log(rss / n) + 2 * kk + 2 * kk * (kk + 1) / max(n - kk - 1, 1)
            if aicc < best[0]:
                best = (aicc, m_.coef_.copy())
        sel = np.where(best[1] > 0)[0]; nsel[SUN[t]] = len(sel)
        fc_now = np.column_stack([cbar[j, 0] + cbar[j, 1] * Z[k].iloc[t].to_numpy() for j, k in enumerate(keys)])
        if len(sel):
            sig_c1.iloc[t] = fc_now[:, sel].mean(axis=1)
        sig_c2.iloc[t] = fc_now.mean(axis=1)
    print("CTREND mean number of selected forecasts:", round(np.mean(list(nsel.values())), 2), "weeks with none:",
          sum(v == 0 for v in nsel.values()), flush=True)
    return (pnl_w(weekly_to_daily(book(sig_c1, wts=wv)), cost=5), pnl_w(weekly_to_daily(book(sig_c2, wts=wv)), cost=5))


c1, c2 = ctrend()
cands["C1 CTREND CS-C-ENet, quintile, volume-weighted (PRIMARY)"] = c1
cands["C2 CTREND naive equal combination"] = c2

pd.DataFrame(cands).to_parquet(ROOT / "results/cache_gen70_daily.parquet")
for n, x in cands.items():
    T.report(n, x); T.ROWS[-1]["ret_2022"] = float((1 + x.loc["2022"]).prod() - 1)


# ---------------------------------------------------------------- portfolio check against v4
def port(df):
    """Daily v4 recipe: each sleeve 10% vol, mean, scaled to 15%, 30d vol targeting (cap 1.5), back to 15%."""
    z = df.loc["2021-12-01":END].fillna(0.0); z = z / (z.std() * np.sqrt(365)) * 0.10
    x = z.mean(axis=1); x = x * 0.15 / (x.loc["2022":].std() * np.sqrt(365))
    x = (x * (0.15 / (x.rolling(30).std().shift(1) * np.sqrt(365))).clip(upper=1.5)).loc["2022-01-01":].dropna()
    x = x * 0.15 / (x.std() * np.sqrt(365)); m = (1 + x).resample("ME").prod() - 1; eq = (1 + x).cumprod()
    return round(x.mean() / x.std() * np.sqrt(365), 3), round((m > 0).mean(), 3), round((eq / eq.cummax() - 1).min(), 3)


H = CS.all_sleeves(); D = H.groupby(H.index.floor("D")).sum()[["C*", "premium carry", "cascade limit strict", "trend 4h"]]
base = port(D); print("v4 (daily recipe) Sharpe 2022-26, pos months, maxDD:", base)
for r in T.ROWS:
    x = cands[r["strategy"]]
    r["corr_v4"] = float(pd.concat([x, D.mean(axis=1)], axis=1).loc["2022":END].corr().iloc[0, 1])
    r["v4_plus"] = port(pd.concat([D, x.rename("new")], axis=1))[0]; r["v4_base"] = base[0]
    print("+", r["strategy"], r["v4_plus"], flush=True)
pd.DataFrame(T.ROWS).to_csv(ROOT / "results/gen70_papers.csv", index=False)
