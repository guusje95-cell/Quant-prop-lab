"""Gen77 (config/gen77_protocol.json): FX fix pattern, month-end overlay, noise-area re-test on 5-minute data, crypto CFD check.
Writes results/gen77.csv and results/cache_gen77_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from qpl.lab import data as D, engine as EN
from qpl.lab.strategies_papers import NoiseAreaMomentum

warnings.filterwarnings("ignore")
DUK = ROOT / "research_data" / "dukascopy"
PER = {"DEV": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-09-30"),
       "FRESH": ("2023-10-01", "2026-10-15"), "ALL": ("2013-01-01", "2026-10-15")}
ROWS, CANDS = [], {}


def load(sym, tf="1h"):
    d = pd.read_parquet(DUK / f"{sym}_{tf}.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index); d = d[~d.index.duplicated()].sort_index()
    return d[d.close > 0]


def sharpe(x, ann=252):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(ann)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, daily, ann=252, note=""):
    daily = daily.sort_index(); r = {"test": name, "note": note, "days_active": int((daily != 0).sum())}
    for k, (a, b) in PER.items():
        r[f"{k}_sharpe"] = sharpe(daily.loc[a:b], ann)
    z = daily / (daily.std() * np.sqrt(ann)) * 0.10; r["worst_day_at_10pct_vol"] = float(z.min())
    ROWS.append(r); CANDS[name] = daily
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def local_open(sym, tz):
    d = load(sym); o = d.open.copy(); o.index = o.index.tz_localize("UTC").tz_convert(tz)
    return o


# ---------------------------------------------------------------- X1 FX fix pattern
PAIRS = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1, "USDJPY": 1, "USDCHF": 1, "USDCAD": 1}   # sign = USD-long
C_FX = 1.0 / 1e4


def fix_leg(sym, tz, h_pre, h_fix, h_post, s):
    o = local_open(sym, tz)
    days = pd.DatetimeIndex(sorted(set(o.index.normalize())))
    a = o.reindex(days + pd.Timedelta(hours=h_pre)).to_numpy(); f = o.reindex(days + pd.Timedelta(hours=h_fix)).to_numpy()
    b = o.reindex(days + pd.Timedelta(hours=h_post)).to_numpy()
    pnl = s * (f / a - 1) - s * (b / f - 1) - 4 * C_FX                 # entry, flip (2 sides), exit
    out = pd.Series(pnl, index=days.tz_localize(None)).dropna()
    return out[out.index.dayofweek < 5]


LON = pd.DataFrame({p: fix_leg(p, "Europe/London", 14, 16, 19, s) for p, s in PAIRS.items()}).mean(axis=1)
TOK = pd.DataFrame({p: fix_leg(p, "Asia/Tokyo", 8, 10, 13, s) for p, s in PAIRS.items()}).mean(axis=1)
report("X1 FX fix pattern, London + Tokyo (PRIMARY)", pd.concat([LON, TOK], axis=1).fillna(0).sum(axis=1))
report("X1 variant: London fix only", LON)


# ---------------------------------------------------------------- X2 month-end overlay
def px_at(sym, tz, hour):
    o = local_open(sym, tz); s = o[o.index.hour == hour]; s.index = s.index.tz_localize(None).normalize()
    return s[~s.index.duplicated()]


us = px_at("US500", "Europe/London", 12)
bask = {s: px_at(s, "Europe/London", 12) for s in ("UK100", "JP225", "EU50")}
bdays = pd.bdate_range("2013-01-01", "2026-09-30")
mends = pd.Series(bdays, index=bdays).groupby(bdays.to_period("M")).last()
x2 = {}
for i in range(1, len(mends)):
    d, d0 = mends.iloc[i], mends.iloc[i - 1]
    try:
        mu = us[d] / us[d0] - 1; mb = np.mean([bask[s][d] / bask[s][d0] - 1 for s in bask])
    except KeyError:
        continue
    side = -1 if mu > mb else 1                                          # short USD when US equities outperformed
    legs = []
    for p, s in PAIRS.items():
        o = local_open(p, "Europe/London")
        t0 = pd.Timestamp(d).tz_localize("Europe/London") + pd.Timedelta(hours=13); t1 = t0 + pd.Timedelta(hours=3)
        if t0 in o.index and t1 in o.index:
            legs.append(side * s * (o[t1] / o[t0] - 1) - 2 * C_FX)
    if legs:
        x2[d] = float(np.mean(legs))
x2 = pd.Series(x2).reindex(bdays).fillna(0.0)
report("X2 month-end equity overlay (PRIMARY)", x2)


# ---------------------------------------------------------------- X3 noise-area breakout on 5-minute data
def bars5(sym):
    d = load(sym, "5m"); w = {k: d[[k]].rename(columns={k: sym}) for k in ("open", "high", "low", "close", "volume")}
    return D.Bars(f"{sym} 5m", "5m", *(w[k] for k in ("open", "high", "low", "close", "volume")), periods_per_year=D.periods_per_year(d.index, "5m"))


for sym, orig in (("US100", 0.71), ("US500", 0.36)):
    b = bars5(sym); st = NoiseAreaMomentum(); sig = st.signal(b, st.defaults())
    cfg = EN.Config(cost_bps=1.0); r = EN.run(b, EN.size(b, sig, cfg, "raw"), cfg)
    dd = EN.to_daily(r["bars"], b.freq)["net"]; dd = dd[dd.index >= dd.index[0] + pd.Timedelta(days=21)]; dd = dd[dd.index.dayofweek < 5]
    report(f"X3 noise-area 5-min re-test, {sym}", dd, note=f"Gen47 original {orig:+.2f}")


# ---------------------------------------------------------------- X4 crypto CFD check (Dukascopy vs Binance)
from qpl.lab import binance_pack as B


def trend4h_close(c1, swap_bp=3.3, cost=5.0):
    c4 = c1.resample("4h").last().dropna(); h4 = c4; l4 = c4                                  # close-based channel on both sources
    hi, lo = c4.rolling(20).max().shift(1).to_numpy(), c4.rolling(20).min().shift(1).to_numpy()
    hx, lx = c4.rolling(10).max().shift(1).to_numpy(), c4.rolling(10).min().shift(1).to_numpy()
    cv = c4.to_numpy(); pos = np.zeros(len(cv)); p = 0
    for i in range(len(cv)):
        if p == 0:
            p = 1 if cv[i] > hi[i] else (-1 if cv[i] < lo[i] else 0)
        elif p == 1 and cv[i] < lx[i]:
            p = 0
        elif p == -1 and cv[i] > hx[i]:
            p = 0
        pos[i] = p
    r4 = c4.pct_change().fillna(0); lev = (0.10 / (r4.rolling(180).std().shift(1) * np.sqrt(6 * 365))).clip(upper=2.0).fillna(0)
    held = (pd.Series(pos, index=c4.index) * lev).shift(1).fillna(0)
    roll = pd.Series(c4.index.hour == 20, index=c4.index).astype(float)
    pnl = held * r4 - held.diff().abs().fillna(0) * cost / 1e4 - held.abs() * roll * swap_bp / 1e4
    return pnl.groupby(pnl.index.floor("D")).sum()


def weiss_from_open(o):
    days = pd.date_range("2017-05-05", "2026-09-30", freq="W-FRI"); days = days[(days + pd.Timedelta(days=7)).month != days.month]
    out = {}
    for d in days:
        t7, t8, t10 = (d + pd.Timedelta(hours=h) for h in (7, 8, 10))
        if t7 in o.index and t8 in o.index and t10 in o.index:
            pre = o[t8] / o[t7] - 1
            if pre != 0:
                out[d] = -np.sign(pre) * (o[t10] / o[t8] - 1) - 2 * 5 / 1e4
    return pd.Series(out)


TR_D, TR_B, WE_D, WE_B = [], [], [], []
for coin in ("BTC", "ETH"):
    d = load(f"{coin}USD"); k = B.k5(coin)
    TR_D.append(trend4h_close(d.close)); TR_B.append(trend4h_close(k.close.resample("1h").last().dropna()))
    WE_D.append(weiss_from_open(d.open)); WE_B.append(weiss_from_open(k.open))
for name, A, Bs in (("trend 4h BTC+ETH", TR_D, TR_B), ("Weiss expiry BTC+ETH", WE_D, WE_B)):
    a = pd.concat(A, axis=1).fillna(0).mean(axis=1); b = pd.concat(Bs, axis=1).fillna(0).mean(axis=1)
    j = pd.concat([a, b], axis=1).dropna()
    corr = float(j.corr().iloc[0, 1])
    for lab, s in (("Dukascopy CFD", a), ("Binance", b)):
        r = {"test": f"X4 {name}, {lab}", "note": f"corr Dukascopy vs Binance {corr:.3f}"}
        for k_, (x0, x1) in (("2018-22", ("2018-01-01", "2022-12-31")), ("2023-26", ("2023-01-01", "2026-09-30"))):
            r[f"{k_}_sharpe"] = sharpe(s.loc[x0:x1], 365) if "trend" in name else sharpe(s.loc[x0:x1].reindex(pd.date_range(x0, x1)).fillna(0), 365)
        ROWS.append(r); print(r, flush=True)

pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen77_daily.parquet")
T = pd.DataFrame(ROWS); T.to_csv(ROOT / "results/gen77.csv", index=False)
pd.set_option("display.width", 250); print(T.round(2).to_string())
