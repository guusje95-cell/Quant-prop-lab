"""Gen56 (config/gen56_protocol.json): five crypto papers on the data we already have.
A intraday hour pairs (Wen et al. 2022) | B basis / momentum / basis-momentum (Chi et al. 2023) | C funding predictability (Inan 2025).
Writes results/gen56_A_pairs.csv, gen56_A_explore.csv, gen56_B_factors.csv, gen56_B_xsmom.csv, gen56_C_funding.csv."""
import itertools, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import strategies as S

OKX = G.SRC["OKX USDT perps (hourly, 2020+)"]()
BSH = G.SRC["Binance spot majors (hourly, 2022+)"]()
OOS0, DEV_END, TEST0 = "2020-06-01", "2022-12-31", "2023-01-01"
cs = S.CStarTrend(); W, CD = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0)
CSTAR = CD["net"]


def st(x, ppy=365):
    x = x.dropna()
    if len(x) < 30 or x.std() == 0:
        return dict(n=len(x), sharpe=np.nan, ann=np.nan, t=np.nan, pos_months=np.nan)
    m = (1 + x).resample("ME").prod() - 1
    return dict(n=len(x), sharpe=x.mean() / x.std() * np.sqrt(ppy), ann=x.mean() * ppy, t=x.mean() / x.std() * np.sqrt(len(x)),
                pos_months=(m > 0).mean())


def corr_cstar(x):
    a = pd.concat([x, CSTAR], axis=1).dropna()
    return a.corr().iloc[0, 1] if len(a) > 30 else np.nan


# ============================================================ A: intraday hour pairs
def hour_matrix(close, vol=None):
    idx = pd.date_range(close.index.min().floor("D"), close.index.max().floor("D") + pd.Timedelta(hours=23), freq="h")
    c = close.reindex(idx); r = c.pct_change(fill_method=None)
    R = pd.DataFrame(r.to_numpy().reshape(-1, 24), index=idx[::24])
    V = pd.DataFrame(vol.reindex(idx).to_numpy().reshape(-1, 24), index=idx[::24]) if vol is not None else None
    return R, V


def pair_pnl(R, V, i, j, sgn, cost_bps, variant=None):
    ri, rj = R[i - 1], R[j - 1]
    pos = sgn * np.sign(ri)
    if variant == "no-jump":
        pos = pos.where(~(ri.abs() > ri.abs().rolling(60, min_periods=30).quantile(0.95).shift(1)), 0.0)
    if variant == "low-liquidity" and V is not None:
        vi = V[i - 1]
        pos = pos.where(vi < vi.rolling(60, min_periods=30).median().shift(1), 0.0)
    pnl = pos * rj - 2 * cost_bps / 1e4 * (pos != 0)
    return pnl[ri.notna() & rj.notna()]


PAIRS = [(3, 5, -1), (3, 15, -1), (3, 17, 1), (8, 22, 1), (10, 11, -1), (12, 13, -1), (22, 23, -1)]
EFFECTIVE = [p for p in PAIRS if (p[0], p[1]) not in ((3, 17), (10, 11))]


def part_a():
    rows = []
    venues = {f"OKX perp {s}": (OKX.close[s], OKX.volume[s]) for s in ("BTC", "ETH", "LTC", "XRP")}
    venues.update({f"Binance spot {s}": (BSH.close[s], BSH.volume[s]) for s in ("BTC", "ETH", "XRP")})
    for vn, (c, v) in venues.items():
        R, V = hour_matrix(c.dropna(), v)
        R = R.loc[OOS0:]; V = V.loc[OOS0:]
        for variant in (None, "no-jump", "low-liquidity"):
            for cost in (0, 2, 5):
                legs = {}
                for i, j, sg in PAIRS:
                    p = pair_pnl(R, V, i, j, sg, cost, variant); legs[(i, j)] = p
                    for per, sl in (("2020-06..2022", slice(OOS0, DEV_END)), ("2023+", slice(TEST0, None))):
                        rows.append(dict(venue=vn, variant=variant or "as published", cost_bps=cost, pair=f"r{i}->r{j} ({'+' if sg > 0 else '-'})",
                                         period=per, **st(p.loc[sl])))
                combo = pd.concat([legs[(i, j)] for i, j, _ in EFFECTIVE], axis=1).mean(axis=1)
                for per, sl in (("2020-06..2022", slice(OOS0, DEV_END)), ("2023+", slice(TEST0, None))):
                    rows.append(dict(venue=vn, variant=variant or "as published", cost_bps=cost, pair="COMBO 5 effective pairs", period=per,
                                     corr_cstar=corr_cstar(combo.loc[sl]), **st(combo.loc[sl])))
    out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen56_A_pairs.csv", index=False)
    # exploratory: all 276 pairs on BTC
    R, V = hour_matrix(OKX.close["BTC"].dropna(), OKX.volume["BTC"]); R = R.loc[OOS0:]
    ex = []
    for i, j in itertools.combinations(range(1, 25), 2):
        d = R.loc[OOS0:DEV_END, [i - 1, j - 1]].dropna()
        b = np.polyfit(d[i - 1], d[j - 1], 1)[0]
        g = pair_pnl(R, None, i, j, 1, 0).loc[OOS0:DEV_END]                         # sign(r_i) * r_j
        t = g.mean() / g.std() * np.sqrt(len(g))
        sg = 1 if t > 0 else -1
        test = pair_pnl(R, None, i, j, sg, 2).loc[TEST0:]
        ex.append(dict(i=i, j=j, dev_t=t, dev_beta=b, sign=sg, selected=abs(t) >= 3, **{f"test_{k}": v for k, v in st(test).items()}))
    ex = pd.DataFrame(ex); ex.to_csv(ROOT / "results/gen56_A_explore.csv", index=False)
    sel = ex[ex.selected]
    if len(sel):
        port = pd.concat([pair_pnl(R, None, r.i, r.j, r.sign, 2).loc[TEST0:] for r in sel.itertuples()], axis=1).mean(axis=1)
        print("A exploratory: selected", len(sel), "pairs", list(zip(sel.i, sel.j, sel.sign)), "TEST combo", st(port), "corr C*", corr_cstar(port))
    return out, ex


# ============================================================ B: basis / momentum / basis-momentum
MAJ = list(G.CR.close.columns)


def daily_at(close_h, lag_h):
    """price at (day d + 1) 00:00 + lag, indexed by day d (OKX bars are labelled by their open time)."""
    t = close_h.index
    sel = close_h[(t.hour == (23 + lag_h) % 24)]
    sel.index = (sel.index - pd.Timedelta(hours=23 + lag_h)).floor("D") if lag_h == 0 else (sel.index - pd.Timedelta(hours=24)).floor("D")
    return sel


def ls_weights(sig, valid, k_frac=1 / 3):
    w = pd.DataFrame(0.0, index=sig.index, columns=sig.columns)
    for d in sig.index:
        s = sig.loc[d][valid.loc[d]].dropna()
        if len(s) < 3:
            continue
        k = max(1, int(round(len(s) * k_frac)))
        o = s.sort_values()
        w.loc[d, o.index[-k:]] = 1.0 / k; w.loc[d, o.index[:k]] = -1.0 / k
    return w


def run_ls(w, ret, hold, cost_bps=5):
    if hold > 1:
        keep = np.arange(len(w)) % hold == 0
        w = w.where(pd.Series(keep, index=w.index), np.nan).ffill().fillna(0.0)
    pnl = (w * ret.reindex(w.index)).sum(axis=1) - w.diff().abs().sum(axis=1) * cost_bps / 1e4
    return pnl


def part_b():
    Sd = G.CR.close[MAJ]
    rows = []
    for lag in (0, 1):
        F0 = daily_at(OKX.close[MAJ], 0)                                          # perp at 00:00, same instant as the spot close
        P = daily_at(OKX.close[MAJ], lag)                                         # entry price after the lag
        idx = F0.index.intersection(Sd.index).intersection(P.index)
        B = np.log(Sd.loc[idx]) - np.log(F0.loc[idx])
        B = B.where(B.abs() < 0.05)                                               # drop bad prints (>5% basis)
        ret = P.loc[idx].pct_change(fill_method=None).shift(-1)                   # return from day d+1 00:00+lag to d+2 00:00+lag
        fut_r = F0.loc[idx].pct_change(fill_method=None)
        for J in (1, 3, 5, 7):
            sigs = {"basis": B, "momentum": (1 + fut_r).rolling(J).apply(np.prod, raw=True) - 1, "basis_momentum": B - B.shift(J + 1)}
            for name, sg in sigs.items():
                valid = sg.notna() & ret.notna()
                w = ls_weights(sg, valid)
                for hold in (1, 7):
                    pnl = run_ls(w, ret, hold)
                    pnl = pnl[pnl.index >= "2020-01-01"]
                    for per, sl in (("DEV 2020-22", slice("2020-01-01", DEV_END)), ("TEST 2023+", slice(TEST0, None))):
                        rows.append(dict(signal=name, J=J, hold=hold, lag_h=lag, period=per, corr_cstar=corr_cstar(pnl.loc[sl]), **st(pnl.loc[sl])))
    out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen56_B_factors.csv", index=False)
    # cross-sectional momentum / reversal on all OKX perps (no spot needed)
    allc = OKX.close
    F0 = daily_at(allc, 0); P = daily_at(allc, 1)
    idx = F0.index.intersection(P.index)
    ret = P.loc[idx].pct_change(fill_method=None).shift(-1).clip(-0.9, 3)
    fr = F0.loc[idx].pct_change(fill_method=None)
    age = F0.loc[idx].notna().cumsum()
    xs = []
    for J in (1, 3, 5, 7, 14, 30):
        mom = (1 + fr).rolling(J).apply(np.prod, raw=True) - 1
        valid = mom.notna() & ret.notna() & (age >= 60)
        w = ls_weights(mom, valid)
        for hold in (1, 7):
            for direction in (1, -1):
                pnl = run_ls(w * direction, ret, hold)
                for per, sl in (("DEV 2020-22", slice("2020-06-01", DEV_END)), ("TEST 2023+", slice(TEST0, None))):
                    xs.append(dict(signal="momentum" if direction > 0 else "reversal", J=J, hold=hold, period=per, corr_cstar=corr_cstar(pnl.loc[sl]),
                                   **st(pnl.loc[sl])))
    xs = pd.DataFrame(xs); xs.to_csv(ROOT / "results/gen56_B_xsmom.csv", index=False)
    return out, xs


# ============================================================ C: funding
def load_funding(coin):
    f = ROOT / f"data/raw/ext/historical-funding-rates-fetcher/data/{coin}-USDT/{coin}-USDT_binance_2020-01-01_2024-01-01_funding_history.csv"
    d = pd.read_csv(f); t = pd.to_datetime(d["Date"]) - pd.Timedelta(hours=3)          # source is UTC+3
    return pd.Series(d["Funding Rate"].to_numpy(), index=t.dt.round("h")).sort_index()


def part_c():
    rows = []
    for coin in ("BTC", "ETH"):
        f = load_funding(coin); x = f.to_numpy(); n = len(x); win = 500
        fc = np.full(n, np.nan)
        for t in range(win, n - 1):
            b, a = np.polyfit(x[t - win:t], x[t - win + 1:t + 1], 1)
            fc[t + 1] = a + b * x[t]
        ok = ~np.isnan(fc); ok[0] = False
        prev = np.r_[np.nan, x[:-1]]
        mspe_ar = np.nanmean((x[ok] - fc[ok]) ** 2); mspe_rw = np.nanmean((x[ok] - prev[ok]) ** 2)
        dch = np.sign(x[ok] - prev[ok]); pch = np.sign(fc[ok] - prev[ok]); nz = dch != 0
        rows.append(dict(coin=coin, test="forecast", mspe_ratio_vs_no_change=mspe_ar / mspe_rw, direction_accuracy=(dch[nz] == pch[nz]).mean(), n=int(ok.sum())))
        # trading: forecast for the next print is known at settlement t; hold the perp from t+1h to t+8h+1h
        fcs = pd.Series(fc, index=f.index).shift(-1)                              # forecast of print t+1, available at t
        px = OKX.close[coin]
        p0 = px.reindex(f.index); p1 = px.reindex(f.index + pd.Timedelta(hours=8))   # bar opening at t closes at t+1h
        r = pd.Series(p1.to_numpy() / p0.to_numpy() - 1, index=f.index)
        pos = pd.Series(np.where(fcs > 0.0003, -1.0, np.where(fcs < 0, 1.0, 0.0)), index=f.index)
        pnl = (pos * r - pos.diff().abs().fillna(0) * 5 / 1e4).dropna()
        daily = pnl.groupby(pnl.index.floor("D")).sum()
        rows.append(dict(coin=coin, test="contrarian trade on forecast", frac_in_market=(pos != 0).mean(), corr_cstar=corr_cstar(daily), **st(daily)))
        # C* funding drag if BTC/ETH positions were held as perps
        wd = W[coin].shift(1).reindex(pd.date_range(f.index.min().floor("D"), f.index.max().floor("D"))).ffill()
        fd = f.groupby(f.index.floor("D")).sum()
        drag = (wd * fd).dropna()
        rows.append(dict(coin=coin, test="C* + BTC leads funding drag (fraction of equity per year)", ann=drag.mean() * 365, n=len(drag)))
    out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen56_C_funding.csv", index=False)
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
    a, ex = part_a()
    print(a[(a.pair.str.startswith("COMBO"))].round(3).to_string())
    b, xs = part_b()
    print(b.round(3).to_string()); print(xs.round(3).to_string())
    print(part_c().round(5).to_string())
