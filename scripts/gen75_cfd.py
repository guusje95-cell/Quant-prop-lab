"""Gen75 (config/gen75_protocol.json): index / gold / EURUSD ideas batch 2 on Dukascopy hourly data.
Writes results/gen75_cfd.csv and results/cache_gen75_daily.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

DUK = ROOT / "research_data" / "dukascopy"
COST = {"US100": 1.0, "US500": 1.0, "US30": 1.0, "DE40": 1.0, "XAUUSD": 2.0, "EURUSD": 1.0}
FIN = 0.03 / 365
PER = {"DEV": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-09-30"),
       "ALL": ("2013-01-01", "2026-09-30")}
ROWS, CANDS = [], {}
FOMC = """2013-01-30 2013-03-20 2013-05-01 2013-06-19 2013-07-31 2013-09-18 2013-10-30 2013-12-18
2014-01-29 2014-03-19 2014-04-30 2014-06-18 2014-07-30 2014-09-17 2014-10-29 2014-12-17
2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16""".split()


def load(sym):
    d = pd.read_parquet(DUK / f"{sym}_1h.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index); d = d[~d.index.duplicated()].sort_index()
    return d[d.close > 0]


def local(sym, tz):
    d = load(sym); d.index = d.index.tz_localize("UTC").tz_convert(tz); return d


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, daily, note=""):
    daily = daily.sort_index(); daily.index = pd.DatetimeIndex(daily.index).tz_localize(None) if getattr(daily.index, "tz", None) else daily.index
    r = {"test": name, "note": note, "days_active": int((daily != 0).sum())}
    for k, (a, b) in PER.items():
        y = daily.loc[a:b]; r[f"{k}_sharpe"] = sharpe(y); r[f"{k}_ann"] = float(y.mean() * 252) if len(y) else np.nan
    z = daily / (daily.std() * np.sqrt(252)) * 0.10
    r["worst_day_at_10pct_vol"] = float(z.min()); eq = (1 + z).cumprod(); r["maxdd_at_10pct_vol"] = float((eq / eq.cummax() - 1).min())
    ROWS.append(r); CANDS[name] = daily
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def daily_close(sym):
    """(close series by local date, tz): US indices close of the 15:00 NY bar, DE40 close of the 17:00 Berlin bar."""
    tz, hr = ("Europe/Berlin", 17) if sym == "DE40" else ("America/New_York", 15)
    d = local(sym, tz); c = d.close[d.index.hour == hr]
    c.index = c.index.tz_localize(None).normalize()
    return c[~c.index.duplicated()]


def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


# ---------------------------------------------------------------- H1 RSI(2) pullback
def h1(sym, thr=10):
    c = daily_close(sym); sma200 = c.rolling(200).mean(); sma5 = c.rolling(5).mean(); r2 = rsi(c)
    pos = np.zeros(len(c)); p = 0
    for i in range(len(c)):
        if p == 0 and c.iloc[i] > sma200.iloc[i] and r2.iloc[i] < thr:
            p = 1
        elif p == 1 and c.iloc[i] > sma5.iloc[i]:
            p = 0
        pos[i] = p
    pos = pd.Series(pos, index=c.index); held = pos.shift(1).fillna(0)
    nights = pd.Series(c.index, index=c.index).diff().dt.days.fillna(1)
    return held * c.pct_change().fillna(0) - pos.diff().abs().fillna(0) * COST[sym] / 1e4 - held * nights * FIN


IDX = ["US500", "US100", "US30", "DE40"]
H1 = pd.DataFrame({s: h1(s) for s in IDX}).fillna(0)
for s in IDX:
    print("   H1 single", s, round(sharpe(H1[s]), 2), flush=True)
report("H1 RSI(2) pullback, 4 indices (PRIMARY)", H1.mean(axis=1))
report("H1 variant RSI(2) < 5", pd.DataFrame({s: h1(s, 5) for s in IDX}).fillna(0).mean(axis=1))


# ---------------------------------------------------------------- H2 pre-FOMC drift
def h2(sym, exit_h=14):
    d = local(sym, "America/New_York"); o = d.open
    out = {}
    for ds in FOMC:
        day = pd.Timestamp(ds).tz_localize("America/New_York")
        prev = day - pd.offsets.BDay(1)
        t0 = prev + pd.Timedelta(hours=14); t1 = day + pd.Timedelta(hours=exit_h)
        if t0 in o.index and t1 in o.index:
            out[pd.Timestamp(ds)] = o[t1] / o[t0] - 1 - 2 * COST[sym] / 1e4 - FIN
    s = pd.Series(out)
    bd = pd.bdate_range("2013-01-01", "2026-09-30")
    return s.reindex(bd).fillna(0.0)


report("H2 pre-FOMC drift, US500+US100 (PRIMARY)", (h2("US500") + h2("US100")) / 2)
report("H2 variant: hold to 16:00 ET", (h2("US500", 16) + h2("US100", 16)) / 2)


# ---------------------------------------------------------------- H3 gold London fix
def window_ldn(sym, h0, h1_, side):
    d = local(sym, "Europe/London"); o = d.open
    days = pd.DatetimeIndex(sorted(set(o.index.normalize())))
    p0 = o.reindex(days + pd.Timedelta(hours=h0)).to_numpy(); p1 = o.reindex(days + pd.Timedelta(hours=h1_)).to_numpy()
    s = pd.Series(side * (p1 / p0 - 1) - 2 * COST[sym] / 1e4, index=days.tz_localize(None)).dropna()
    return s[s.index.dayofweek < 5]


report("H3 gold PM-fix dip, short 14-15 London (PRIMARY)", window_ldn("XAUUSD", 14, 15, -1))
report("H3 variant: AM fix, short 09-10 London", window_ldn("XAUUSD", 9, 10, -1))


# ---------------------------------------------------------------- H4 Asian-range breakout
def h4(sym):
    d = load(sym); c = COST[sym] / 1e4; out = {}
    for day, g in d.groupby(d.index.normalize()):
        if day.dayofweek >= 5:
            continue
        asia = g[g.index.hour < 7]; sess = g[(g.index.hour >= 7) & (g.index.hour <= 15)]
        if len(asia) < 5 or len(sess) < 8:
            continue
        hi, lo = asia.high.max(), asia.low.min(); pnl = 0.0; side = 0; entry = None
        for t, row in sess.iterrows():
            if side == 0 and t.hour <= 11:
                if row.close > hi:
                    side, entry, stop = 1, row.close, lo
                elif row.close < lo:
                    side, entry, stop = -1, row.close, hi
                continue
            if side != 0:
                if (side == 1 and row.low <= stop) or (side == -1 and row.high >= stop):
                    pnl = side * (stop / entry - 1); side = 9; break
        if side in (1, -1):
            ex = g[g.index.hour == 16].open
            px = ex.iloc[0] if len(ex) else sess.close.iloc[-1]
            pnl = side * (px / entry - 1); side = 9
        if side == 9:
            out[day] = pnl - 2 * c
        else:
            out[day] = 0.0
    return pd.Series(out)


E, X = h4("EURUSD"), h4("XAUUSD")
report("H4 Asian-range breakout, EURUSD+XAUUSD (PRIMARY)", pd.concat([E, X], axis=1).fillna(0).mean(axis=1))
report("H4 variant: EURUSD only", E)


# ---------------------------------------------------------------- H5 volatility-managed equity sleeve
def h5(sym, managed=True):
    c = daily_close(sym); r = c.pct_change().fillna(0)
    rv = (r ** 2).groupby(r.index.to_period("M")).sum()
    cbar = rv.expanding().mean()
    w_m = (cbar / rv).clip(upper=1.5).shift(1) if managed else rv * 0 + 1.0           # weight for month m from month m-1
    w = pd.Series(r.index.to_period("M").map(w_m).to_numpy(), index=r.index).astype(float).fillna(0.0)
    nights = pd.Series(c.index, index=c.index).diff().dt.days.fillna(1)
    held = w.shift(1).fillna(0)
    return held * r - w.diff().abs().fillna(0) * COST[sym] / 1e4 - held * nights * FIN


VM = pd.DataFrame({s: h5(s) for s in ("US500", "US100")}).fillna(0).mean(axis=1)
BH = pd.DataFrame({s: h5(s, managed=False) for s in ("US500", "US100")}).fillna(0).mean(axis=1)
report("H5 vol-managed US500+US100 (beta sleeve)", VM)
report("H5 reference: buy-and-hold US500+US100", BH)

# ---------------------------------------------------------------- portfolio checks
cfd = pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")["swap 3.3 (base)"]
cfd = cfd.groupby(cfd.index.floor("D")).sum()
v5 = pd.read_parquet(ROOT / "results/cache_gen72_final.parquet")["portfolio"]; v5 = v5.groupby(v5.index.floor("D")).sum()


def combo_sharpe(a, b):
    j = pd.concat([a, b], axis=1).loc["2022-01-01":"2026-09-30"].fillna(0.0)
    j = j / (j.std() * np.sqrt(365)); x = j.mean(axis=1)
    return float(x.mean() / x.std() * np.sqrt(365))


base = combo_sharpe(cfd, cfd * 0) if False else float(cfd.loc["2022":].mean() / cfd.loc["2022":].std() * np.sqrt(365))
for r in ROWS:
    x = CANDS[r["test"]]
    r["corr_v5"] = float(pd.concat([x, v5], axis=1).dropna().corr().iloc[0, 1])
    r["corr_cfd_portfolio"] = float(pd.concat([x, cfd], axis=1).dropna().corr().iloc[0, 1])
    r["cfd_portfolio_alone"] = base; r["cfd_portfolio_plus"] = combo_sharpe(cfd, x)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen75_daily.parquet")
T = pd.DataFrame(ROWS); T.to_csv(ROOT / "results/gen75_cfd.csv", index=False)
pd.set_option("display.width", 250)
print(T[["test", "days_active", "DEV_sharpe", "TEST_sharpe", "HOLD_sharpe", "ALL_sharpe", "worst_day_at_10pct_vol", "corr_v5",
         "cfd_portfolio_alone", "cfd_portfolio_plus"]].round(2).to_string())
