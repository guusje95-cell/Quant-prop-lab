"""Gen474 (config/gen474_protocol.json): four user TA ideas (EMA ribbon, HMA slope turn +/- TEMA, pin bar, slow-EMA pullback)
on crypto, futures and CFDs. Writes results/gen474.json (and results/gen474_sleeves_*.parquet)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
VARIANTS = ["ribbon", "hma", "hma_tema", "pinbar", "pullback"]


# ------------------------------------------------------------------------------------------------------------- signals
ema = lambda x, n: x.ewm(span=n, adjust=False).mean()


def wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n).apply(lambda v: np.dot(v, w) / w.sum(), raw=True)


def hma(x, n=21):
    return wma(2 * wma(x, n // 2) - wma(x, n), int(np.sqrt(n)))


def tema(x, n=21):
    e1 = ema(x, n); e2 = ema(e1, n); e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3


def signal(o, h, l, c, kind):
    """-1 / 0 / +1 decided at the close of each bar (one instrument, NaN-free daily OHLC)."""
    if kind == "ribbon":
        a, b, d = ema(c, 8), ema(c, 21), ema(c, 55)
        return pd.Series(np.where((a > b) & (b > d), 1.0, np.where((a < b) & (b < d), -1.0, 0.0)), index=c.index)
    if kind in ("hma", "hma_tema"):
        hm = hma(c); up = hm.diff()
        s = pd.Series(np.where(up > 0, 1.0, np.where(up < 0, -1.0, 0.0)), index=c.index)
        if kind == "hma_tema":
            t = tema(c); s = s.where(((s > 0) & (c > t)) | ((s < 0) & (c < t)), 0.0)
        return s
    if kind == "pinbar":
        rng = (h - l).replace(0, np.nan); body = (c - o).abs()
        bull = ((np.minimum(o, c) - l) >= 0.6 * rng) & (body <= 0.3 * rng) & (l <= l.shift(1).rolling(10).min())
        bear = ((h - np.maximum(o, c)) >= 0.6 * rng) & (body <= 0.3 * rng) & (h >= h.shift(1).rolling(10).max())
        ev = pd.Series(np.where(bull, 1.0, np.where(bear, -1.0, np.nan)), index=c.index)
        return ev.ffill(limit=4).fillna(0.0)                                     # signal bar + 4 more = held 5 bars
    if kind == "pullback":
        e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
        upt = (e50 > e200) & (c > e200); dnt = (e50 < e200) & (c < e200)
        le = upt & (c.shift(1) <= e20.shift(1)) & (c > e20); se = dnt & (c.shift(1) >= e20.shift(1)) & (c < e20)
        cv, e50v, lev, sev = c.to_numpy(), e50.to_numpy(), le.to_numpy(), se.to_numpy()
        out = np.zeros(len(c)); pos = 0.0; age = 0
        for i in range(200, len(c)):
            if pos > 0 and (cv[i] < e50v[i] or age >= 20):
                pos = 0.0
            elif pos < 0 and (cv[i] > e50v[i] or age >= 20):
                pos = 0.0
            if lev[i]:
                pos, age = 1.0, 0
            elif sev[i]:
                pos, age = -1.0, 0
            out[i] = pos; age += 1
        return pd.Series(out, index=c.index)
    raise ValueError(kind)


def sized(sig, ret, periods=252):
    vol = ret.rolling(60, min_periods=40).std() * np.sqrt(periods)
    return (sig * (0.10 / vol).clip(upper=3.0)).where(vol > 0).fillna(0.0)    # decided at the close of the bar; caller lags


def shp(x, a, z, periods):
    x = x.loc[a:z]; return round(float(x.mean() / x.std() * np.sqrt(periods)), 3) if x.std() > 0 else float("nan")


out = {"protocol": "config/gen474_protocol.json", "trials": 15}

# ------------------------------------------------------------------------------------------------------------- crypto
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
COINS = ["BTC", "ETH", "LTC", "XRP", "ADA", "DOGE", "SOL", "DOT", "AVAX", "LINK", "BCH"]
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
ddc = lambda hh: hh.groupby(hh.index.floor("D")).sum()
unit = lambda hh: hh * 0.15 / (ddc(hh.loc["2022":"2024"]).std() * np.sqrt(365))
cper = lambda hh: [shp(ddc(hh), "2022", "2022", 365), shp(ddc(hh), "2023", "2024", 365), shp(ddc(hh), "2025", END, 365)]
s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
ref = unit(CS.portfolio_v5(V8)[0]); REF = [shp(ddc(ref), "2022", END, 365), cper(ref)]
D = {f: B.panel(f, "1D", COINS).loc[:END] for f in ("open", "high", "low", "close")}
H1 = B.panel("close", "1h", COINS).loc[:END + " 23:00"]; RH = H1.pct_change(fill_method=None).fillna(0.0).reindex(idx).fillna(0.0)
FUND = B.funding_panel(COINS).reindex(columns=COINS)
crypto = {}; csleeves = {}
for k in VARIANTS:
    W = {}
    for cn in COINS:
        x = pd.DataFrame({f: D[f][cn] for f in D}).dropna()
        if len(x) < 260:
            continue
        s = signal(x.open, x.high, x.low, x.close, k)
        W[cn] = sized(s, x.close.pct_change(), 365)
    W = pd.DataFrame(W).reindex(columns=COINS).fillna(0.0) / len(COINS)
    Wn = W.reindex(W.index.append(pd.DatetimeIndex([W.index[-1] + pd.Timedelta(days=1)])))
    P = Wn.shift(1).reindex(idx.floor("D")).set_axis(idx).fillna(0.0)          # decided at day d close -> held during day d+1
    turn = P.diff().abs().fillna(P.abs()).sum(axis=1) * 7.5e-4
    fund = (P.reindex(FUND.index.intersection(idx)) * FUND.reindex(FUND.index.intersection(idx)).fillna(0.0)).sum(axis=1).reindex(idx).fillna(0.0)
    pnl = (P * RH).sum(axis=1) - turn - fund
    csleeves[k] = pnl
    b = unit(CS.portfolio_v5(V8.assign(**{f"ta {k}": pnl}))[0]); r = [shp(ddc(b), "2022", END, 365), cper(b)]
    crypto[k] = {"sleeve 2022 / 2023-24 / 2025-26": cper(pnl), "sleeve gross of costs+funding": cper(pnl + turn + fund),
                 "corr with v9.8 book": round(float(ddc(pnl).loc["2022":].corr(ddc(ref).loc["2022":])), 2),
                 "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
out["crypto"] = {"reference v9.8": REF, **crypto}
pd.DataFrame(csleeves).to_parquet(ROOT / "results/gen474_sleeves_crypto.parquet")
print(json.dumps(out["crypto"], indent=1), flush=True)

# ------------------------------------------------------------------------------------------------------------- futures
import fbook
import futures_db as F


def fut_ohlc(root):
    f = F.front(root); td = F.trade_date(f.index); f = f.assign(td=td)
    last_id = f.groupby("td").instrument_id.transform("last")
    g = f[f.instrument_id == last_id].groupby("td")                              # the day's final contract only (roll days)
    d = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})
    dr = F.daily(root); d = d.reindex(dr.index)
    adj = (1 + dr.r).cumprod(); k = adj / d.close                                 # back-adjust: scale the day's bar to the adjusted close
    return pd.DataFrame({c: d[c] * k for c in d}).dropna(), dr


futures = {}; fsleeves = {}
base = fbook.sleeves(); fb = fbook.build(base); FREF = [round(F.sharpe(fb, *s), 3) for s in F.SPLITS]
FD = {r: fut_ohlc(r) for r in F.NONCRYPTO}
for k in VARIANTS:
    P = {}
    for r, (x, dr) in FD.items():
        s = signal(x.open, x.high, x.low, x.close, k)
        w = sized(s, dr.r.reindex(x.index), 252).reindex(dr.index).fillna(0.0).shift(1).fillna(0.0)
        P[r] = w * dr.r - w.diff().abs().fillna(w.abs()) * dr.cost
    pnl = pd.DataFrame(P).fillna(0.0).mean(axis=1)
    fsleeves[k] = pnl
    b = fbook.build(base.assign(**{f"ta {k}": pnl})); r = [round(F.sharpe(b, *s), 3) for s in F.SPLITS]
    futures[k] = {"sleeve 2010-17 / 2018-22 / 2023-26": list(F.splits(pnl)), "stand-alone pass": F.passes(F.splits(pnl)),
                  "ES/NQ beta appraisal 2010-22": round(fbook.appraisal(pnl), 3),
                  "corr with futures book 2023-26": round(float(pd.concat([pnl, fb], axis=1).loc["2023":].corr().iloc[0, 1]), 2),
                  "book": r, "pass": bool(r[2] >= FREF[2] + 0.05 and r[0] >= FREF[0] and r[1] >= FREF[1])}
out["futures"] = {"reference 15-sleeve book": FREF, **futures}
pd.DataFrame(fsleeves).to_parquet(ROOT / "results/gen474_sleeves_futures.parquet")
print(json.dumps(out["futures"], indent=1), flush=True)

# ------------------------------------------------------------------------------------------------------------- CFDs
DUKA = ROOT / "research_data/dukascopy"
INDEX = ["AUS200", "CH20", "DE40", "ES35", "EU50", "FR40", "HK50", "JP225", "UK100", "US100", "US2000", "US30", "US500"]
COST = {**{s: 1.5 for s in INDEX}, "XAUUSD": 2.0, "XAGUSD": 4.0, "WTI": 4.0, "BRENT": 4.0, "NATGAS": 8.0, "COPPER": 5.0, "BUND": 2.0, "USTBOND": 2.0}
syms = sorted(p.name[:-11] for p in DUKA.glob("*_1h.parquet") if p.name[:-11] not in ("BTCUSD", "ETHUSD"))
for s in syms:
    COST.setdefault(s, 1.0 if ("JPY" in s and s != "USDJPY") else 0.7)
CP = (("2018-07-01", "2020-12-31"), ("2021-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30"))
g201 = pd.read_parquet(ROOT / "results/gen201_book.parquet").book
g201 = g201[g201.index.weekday < 5]
def mix(book, sl):
    x = pd.concat([book, sl], axis=1).dropna(); fit = x.loc["2020":"2022"]; w = 1 / fit.std(); w = w / w.sum()
    raw = (x * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
    return (raw * lvl).dropna()
GREF = [shp(g201, a, z, 252) for a, z in CP]
CD = {}
for s in syms:
    x = pd.read_parquet(DUKA / f"{s}_1h.parquet").loc[:END + " 23:00"]
    d = x.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    CD[s] = d[d.index.weekday < 5]
cfd = {}; xsleeves = {}
for k in VARIANTS:
    P = {}; G = {}
    for s, x in CD.items():
        sig = signal(x.open, x.high, x.low, x.close, k); r = x.close.pct_change().fillna(0.0)
        w = sized(sig, r, 252).shift(1).fillna(0.0)
        P[s] = w * r - w.diff().abs().fillna(w.abs()) * COST[s] / 1e4; G[s] = w.abs()
    pnl = pd.DataFrame(P).fillna(0.0).mean(axis=1).loc["2018-07-01":]
    swap = pd.DataFrame(G).fillna(0.0).mean(axis=1).loc["2018-07-01":] * 0.03 / 252
    xsleeves[k] = pnl
    per = [shp(pnl, a, z, 252) for a, z in CP]
    b = mix(g201, pnl); bk = [shp(b, a, z, 252) for a, z in CP]
    cfd[k] = {"sleeve 2018-20 / 2021-22 / 2023-26 (swap-free)": per, "with 3%/yr financing": [shp(pnl - swap, a, z, 252) for a, z in CP],
              "stand-alone pass": bool(per[0] > 0 and per[1] >= 0.5 and per[2] >= 0.3),
              "corr with index-CFD book 2023-26": round(float(pd.concat([pnl, g201], axis=1).loc["2023":].corr().iloc[0, 1]), 2),
              "with Gen201 book": bk}
    cfd[k]["pass"] = bool(cfd[k]["stand-alone pass"] and bk[2] >= GREF[2] + 0.05 and bk[1] >= GREF[1])
out["cfd"] = {"instruments": syms, "reference Gen201 index-CFD book": GREF, **cfd}
pd.DataFrame(xsleeves).to_parquet(ROOT / "results/gen474_sleeves_cfd.parquet")
print(json.dumps(out["cfd"], indent=1), flush=True)
out["passed"] = [f"{m}:{k}" for m in ("crypto", "futures", "cfd") for k in VARIANTS if out[m][k]["pass"]]
(ROOT / "results/gen474.json").write_text(json.dumps(out, indent=1)); print("PASSED:", out["passed"])
