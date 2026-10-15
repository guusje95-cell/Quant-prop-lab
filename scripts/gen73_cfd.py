"""Gen73 (config/gen73_protocol.json): first CFD-firm tests on Dukascopy hourly data. Writes results/gen73_cfd.csv and
results/cache_gen73_daily.parquet."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

DUK = ROOT / "research_data" / "dukascopy"
COST = {"US100": 1.0, "US500": 1.0, "US30": 1.0, "DE40": 1.0, "XAUUSD": 2.0, "EURUSD": 1.0}      # bp per side
FIN = 0.03 / 365                                                                                    # per night held over 22:00 UTC
PER = {"DEV": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-09-30"),
       "FRESH": ("2023-10-01", "2026-09-30"), "ALL": ("2013-01-01", "2026-09-30")}
ROWS, CANDS = [], {}


def load(sym):
    d = pd.read_parquet(DUK / f"{sym}_1h.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index); d = d[~d.index.duplicated()].sort_index()
    return d[d.close > 0]


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, daily, note=""):
    """daily: P&L per trading day (weekdays with any activity)."""
    daily = daily.sort_index()
    r = {"test": name, "note": note}
    for k, (a, b) in PER.items():
        y = daily.loc[a:b]
        r[f"{k}_sharpe"] = sharpe(y); r[f"{k}_ann"] = float(y.mean() * 252) if len(y) else np.nan
    eq = (1 + daily / (daily.std() * np.sqrt(252)) * 0.10).cumprod()
    r["worst_day_at_10pct_vol"] = float((daily / (daily.std() * np.sqrt(252)) * 0.10).min())
    r["maxdd_at_10pct_vol"] = float((eq / eq.cummax() - 1).min())
    ROWS.append(r); CANDS[name] = daily
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def to_day(pnl):
    s = pnl.groupby(pnl.index.floor("D")).sum()
    return s[s.index.dayofweek < 5]


def window(sym, tz, start_h, end_h, side=1.0, swap_nights=0):
    """Hold from the open of the start_h bar to the open of the end_h bar (local tz hours; end may be next day)."""
    d = load(sym); o = d.open
    loc = o.index.tz_localize("UTC").tz_convert(tz)
    ser = pd.Series(o.to_numpy(), index=loc)
    days = pd.DatetimeIndex(sorted(set(loc.normalize())))
    t0 = days + pd.Timedelta(hours=start_h)
    t1 = days + pd.Timedelta(hours=end_h + (24 if end_h <= start_h else 0))
    p0 = ser.reindex(t0).to_numpy(); p1 = ser.reindex(t1).to_numpy()
    g = side * (p1 / p0 - 1) - 2 * COST[sym] / 1e4 - swap_nights * FIN
    out = pd.Series(g, index=t0.tz_convert("UTC").tz_localize(None).floor("D")).dropna()
    return out[out.index.dayofweek < 5]


# ---------------------------------------------------------------- T1 gold session split (UTC)
def gold_split(long_only=False):
    d = load("XAUUSD"); o = d.open
    days = pd.DatetimeIndex(sorted(set(o.index.normalize())))
    c = COST["XAUUSD"] / 1e4
    a0, a1 = o.reindex(days - pd.Timedelta(hours=1)).to_numpy(), o.reindex(days + pd.Timedelta(hours=7)).to_numpy()   # 23:00 prev -> 07:00
    b1 = o.reindex(days + pd.Timedelta(hours=16)).to_numpy()                                                         # 07:00 -> 16:00
    longleg = a1 / a0 - 1 - 2 * c
    shortleg = -(b1 / a1 - 1) - 2 * c
    tot = pd.Series(np.nan_to_num(longleg) + (0 if long_only else np.nan_to_num(-0) + np.nan_to_num(shortleg)), index=days)
    tot[np.isnan(longleg) & np.isnan(shortleg)] = np.nan
    return tot.dropna()[lambda s: s.index.dayofweek < 5]


g = gold_split(); report("T1 gold session split (Gen60 D2) (PRIMARY)", g)
for a, b in (("2013-02-01", "2015-02-28"), ("2015-03-01", "2026-09-30")):
    print("   T1 sub-period", a, b, "Sharpe", round(sharpe(g.loc[a:b]), 2), flush=True)
report("T1 variant: long leg only", gold_split(long_only=True))

# ---------------------------------------------------------------- T2 European open (Gen48c re-test)
for sym in ("US500", "DE40"):
    report(f"T2 re-test European-open long, {sym}", window(sym, "America/New_York", 0, 4), "original US500 -0.18 at 1bp")

# ---------------------------------------------------------------- T3 overnight (Liu & Tse re-test)
for sym in ("US500", "US100", "US30"):
    report(f"T3 re-test overnight 16:00->09:00 NY, {sym}", window(sym, "America/New_York", 16, 9, swap_nights=1), "original: negative after costs")


# ---------------------------------------------------------------- T4 noise-area breakout, hourly checks (US100)
def noise_area(sym, look=14, target=0.02, maxlev=4.0):
    d = load(sym)
    loc = d.index.tz_localize("UTC").tz_convert("America/New_York")
    df = pd.DataFrame({"o": d.open.to_numpy(), "h": d.high.to_numpy(), "l": d.low.to_numpy(), "c": d.close.to_numpy()}, index=loc)
    df["date"] = df.index.normalize(); df["hr"] = df.index.hour
    ses = df[(df.hr >= 10) & (df.hr <= 15)].copy()                       # bars 10:00..15:00 NY; day open = open of the 10:00 bar
    op = ses[ses.hr == 10].groupby("date")["o"].first()
    ses["dopen"] = ses["date"].map(op)
    ses["move"] = (ses["c"] / ses["dopen"] - 1).abs()
    piv = ses.pivot_table(index="date", columns="hr", values="move", aggfunc="last")
    sig = piv.rolling(look, min_periods=look).mean().shift(1)
    ses["sigma"] = [sig.at[dd, hh] if (dd in sig.index and hh in sig.columns) else np.nan for dd, hh in zip(ses["date"], ses["hr"])]
    prev_close = ses.groupby("date")["c"].last().shift(1)
    ses["pclose"] = ses["date"].map(prev_close)
    ses["ub"] = np.maximum(ses["dopen"], ses["pclose"]) * (1 + ses["sigma"]); ses["lb"] = np.minimum(ses["dopen"], ses["pclose"]) * (1 - ses["sigma"])
    ses["tp"] = (ses["h"] + ses["l"] + ses["c"]) / 3
    ses["vwap"] = ses.groupby("date")["tp"].cumsum() / ses.groupby("date").cumcount().add(1)
    dret = ses.groupby("date")["c"].last().pct_change()
    lev = (target / dret.rolling(14).std().shift(1)).clip(upper=maxlev)
    out = {}
    cost = COST[sym] / 1e4
    for dd, gday in ses.groupby("date"):
        L = lev.get(dd, np.nan)
        if not np.isfinite(L) or gday["sigma"].isna().all():
            continue
        pos = 0; pnl = 0.0; cv = gday["c"].to_numpy()
        for i in range(len(gday)):
            row = gday.iloc[i]
            if i > 0:
                pnl += pos * L * (cv[i] / cv[i - 1] - 1)
            if i == len(gday) - 1:                                        # 15:00 bar close = 16:00: flat
                break
            new = pos
            if pos == 1 and cv[i] < max(row.lb if np.isfinite(row.lb) else -np.inf, row.vwap):
                new = 0
            if pos == -1 and cv[i] > min(row.ub if np.isfinite(row.ub) else np.inf, row.vwap):
                new = 0
            if new == 0 and np.isfinite(row.ub):
                new = 1 if cv[i] > row.ub else (-1 if cv[i] < row.lb else 0)
            pnl -= abs(new - pos) * L * cost; pos = new
        pnl -= abs(pos) * L * cost
        out[pd.Timestamp(dd).tz_localize(None)] = pnl
    return pd.Series(out)


report("T4 re-test noise-area breakout US100 (hourly checks)", noise_area("US100"), "original US100 +0.71 (15-min)")


# ---------------------------------------------------------------- T5 4h breakout trend on the CFDs
def trend4h_cfd(sym, n_in=20, n_out=10):
    d = load(sym)
    c4 = d.close.resample("4h").last().dropna(); h4 = d.high.resample("4h").max().reindex(c4.index); l4 = d.low.resample("4h").min().reindex(c4.index)
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
    lev = (0.10 / (r4.rolling(6 * 30).std().shift(1) * np.sqrt(6 * 252))).clip(upper=2.0).fillna(0)
    held = (pd.Series(pos, index=c4.index) * lev).shift(1).fillna(0)          # decided at the bar close, held next bar
    nights = (pd.Series(c4.index.hour, index=c4.index) == 20).astype(float)  # the 20:00-24:00 bar spans 22:00 UTC
    pnl = held * r4 - held.diff().abs().fillna(0) * COST[sym] / 1e4 - held.abs() * nights * FIN
    return to_day(pnl)


T5 = {s: trend4h_cfd(s) for s in COST}
P5 = pd.DataFrame(T5).fillna(0.0)
for s in COST:
    print("   T5 single", s, "ALL", round(sharpe(P5[s]), 2), "TEST", round(sharpe(P5[s].loc["2020":"2023"]), 2), "HOLD", round(sharpe(P5[s].loc["2024":]), 2), flush=True)
report("T5 4h breakout trend, 6 CFDs (PRIMARY)", P5.mean(axis=1))
report("T5 variant: indices + gold", P5[["US100", "US500", "US30", "DE40", "XAUUSD"]].mean(axis=1))

# ---------------------------------------------------------------- correlation with crypto v5
v5 = pd.read_parquet(ROOT / "results/cache_gen72_final.parquet")["portfolio"]
v5d = v5.groupby(v5.index.floor("D")).sum()
for r in ROWS:
    x = CANDS[r["test"]]
    j = pd.concat([x, v5d], axis=1).dropna()
    r["corr_v5"] = float(j.corr().iloc[0, 1]) if len(j) > 50 else np.nan
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen73_daily.parquet")
pd.DataFrame(ROWS).to_csv(ROOT / "results/gen73_cfd.csv", index=False)
print(pd.DataFrame(ROWS)[["test", "DEV_sharpe", "TEST_sharpe", "HOLD_sharpe", "FRESH_sharpe", "ALL_sharpe", "corr_v5"]].round(2).to_string())
