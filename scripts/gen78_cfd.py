"""Gen78 (config/gen78_protocol.json): XS momentum within asset classes, pairs mean reversion, intraday FX seasonality on the 35
Dukascopy CFDs. Writes results/gen78.csv and results/cache_gen78_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
warnings.filterwarnings("ignore")
DUK = ROOT / "research_data" / "dukascopy"
FX = {"EURUSD": 1, "GBPUSD": 1, "AUDUSD": 1, "NZDUSD": 1, "USDJPY": -1, "USDCHF": -1, "USDCAD": -1}   # +1: pair = currency vs USD
IDX = ["US500", "US100", "US30", "US2000", "DE40", "UK100", "JP225", "EU50", "FR40", "AUS200", "HK50", "CH20", "ES35"]
COM = ["XAUUSD", "XAGUSD", "WTI", "BRENT", "NATGAS", "COPPER"]
COST = {**{s: 1.0 for s in list(FX) + IDX}, "XAUUSD": 2.0, "XAGUSD": 4.0, "WTI": 4.0, "BRENT": 4.0, "COPPER": 4.0, "NATGAS": 6.0,
        "BUND": 2.0, "USTBOND": 2.0}
FIN = 0.03 / 365
PER = {"DEV": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-09-30"), "ALL": ("2013-01-01", "2026-09-30")}
ROWS, CANDS = [], {}


def load(sym):
    d = pd.read_parquet(DUK / f"{sym}_1h.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index); d = d[~d.index.duplicated()].sort_index()
    return d[d.close > 0]


def sharpe(x):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, daily, note=""):
    daily = daily.sort_index(); r = {"test": name, "note": note}
    for k, (a, b) in PER.items():
        r[f"{k}_sharpe"] = sharpe(daily.loc[a:b])
    z = daily / (daily.std() * np.sqrt(252)) * 0.10; eq = (1 + z).cumprod()
    r["worst_day_at_10pct_vol"] = float(z.min()); r["maxdd_at_10pct_vol"] = float((eq / eq.cummax() - 1).min())
    ROWS.append(r); CANDS[name] = daily
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


ALLSYM = list(FX) + IDX + COM
C = pd.DataFrame({s: load(s).close.resample("1D").last() for s in ALLSYM})
C = C[C.index.dayofweek < 5].ffill(limit=3).loc["2013-01-01":"2026-09-30"]
R = C.pct_change(fill_method=None).fillna(0.0)
NIGHTS = pd.Series(C.index, index=C.index).diff().dt.days.fillna(1)


def pnl(W):
    """W: daily weights per instrument decided at the close (held from the next day)."""
    W = W.reindex(C.index).fillna(0.0); held = W.shift(1).fillna(0.0)
    cost = W.diff().abs().fillna(W.abs()).mul(pd.Series(COST), axis=1).sum(axis=1) / 1e4
    return (held * R).sum(axis=1) - cost - held.abs().sum(axis=1) * NIGHTS * FIN


# ---------------------------------------------------------------- M1 cross-sectional momentum
def xs_mom(look=252, skip=21):
    asset = C.copy()
    for p, s in FX.items():
        if s == -1:
            asset[p] = 1.0 / C[p]                                  # currency price in USD
    mom = asset.shift(skip) / asset.shift(look) - 1
    vol = (R.rolling(60).std() * np.sqrt(252)).where(lambda v: v > 0.01)       # no weight without a real vol estimate
    me = C.index[C.index.to_period("M") != pd.Series(C.index.to_period("M"), index=C.index).shift(-1).values]   # last day of each month
    W = pd.DataFrame(np.nan, index=C.index, columns=ALLSYM)
    for d in me:
        row = pd.Series(0.0, index=ALLSYM)
        for cls in (list(FX), IDX, COM):
            m = mom.loc[d, cls][vol.loc[d, cls].notna()].dropna()
            if len(m) < 5:
                continue
            k = max(1, len(m) // 3); top, bot = m.nlargest(k).index, m.nsmallest(k).index
            for s in top:
                row[s] = (FX.get(s, 1)) / vol.at[d, s] / k
            for s in bot:
                row[s] = -(FX.get(s, 1)) / vol.at[d, s] / k
        W.loc[d] = row
    W = W.ffill().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    # classes at equal risk: scale each class by 0.10 / trailing-1y vol of its own unscaled P&L (known at the rebalance)
    out = []
    for cls in (list(FX), IDX, COM):
        Wc = W[cls]; pc = pnl(Wc.reindex(columns=ALLSYM).fillna(0.0))
        sc = (0.10 / (pc.rolling(252, min_periods=120).std() * np.sqrt(252))).replace([np.inf, -np.inf], np.nan).shift(1)
        sc_m = sc.where(C.index.isin(me)).ffill()
        out.append(Wc.mul(sc_m, axis=0).fillna(0.0))
    Wall = pd.concat(out, axis=1).reindex(columns=ALLSYM).fillna(0.0) / 3      # no scale yet (first year) -> flat
    return pnl(Wall), {c: pnl(W[cls].reindex(columns=ALLSYM).fillna(0.0)) for c, cls in (("FX", list(FX)), ("indices", IDX), ("commodities", COM))}


m1, parts = xs_mom()
for k, v in parts.items():
    print("   M1 class", k, "ALL", round(sharpe(v), 2), "TEST", round(sharpe(v.loc["2020":"2023"]), 2), "HOLD", round(sharpe(v.loc["2024":]), 2), flush=True)
report("M1 XS momentum 12-1, 3 classes (PRIMARY)", m1)
report("M1 variant 6-1", xs_mom(126, 21)[0])


# ---------------------------------------------------------------- M2 pairs mean reversion
PAIRS = [("WTI", "BRENT"), ("XAUUSD", "XAGUSD"), ("AUDUSD", "NZDUSD"), ("EU50", "DE40"), ("FR40", "EU50"), ("US500", "US30")]


def pair_book(entry=2.0):
    W = pd.DataFrame(0.0, index=C.index, columns=ALLSYM)
    for a, b in PAIRS:
        la, lb = np.log(C[a]), np.log(C[b])
        beta = la.rolling(120).cov(lb) / lb.rolling(120).var()
        spr = la - beta * lb
        z = (spr - spr.rolling(60).mean()) / spr.rolling(60).std()
        pos = 0; age = 0; wa = wb = 0.0
        for i, d in enumerate(C.index):
            zi, bi = z.iloc[i], beta.iloc[i]
            if not (np.isfinite(zi) and np.isfinite(bi)):
                continue
            if pos != 0:
                age += 1
                if (pos == 1 and zi >= 0) or (pos == -1 and zi <= 0) or age >= 20 or abs(zi) > 4:
                    pos = 0; wa = wb = 0.0
            if pos == 0 and abs(zi) > entry:
                pos = -1 if zi > 0 else 1                          # z > 0: spread rich -> short a, long b
                g = 1 + abs(bi); wa, wb = pos / g, -pos * bi / g; age = 0
            W.at[d, a] += wa / len(PAIRS); W.at[d, b] += wb / len(PAIRS)
    return pnl(W)


report("M2 pairs mean reversion, 6 pairs (PRIMARY)", pair_book(2.0))
report("M2 variant entry 1.5", pair_book(1.5))


# ---------------------------------------------------------------- M3 intraday FX seasonality
def fx_season(us_leg=False):
    legs = []
    for p, sgn in (("EURUSD", -1), ("GBPUSD", -1), ("USDCHF", 1)):          # sell EUR/GBP/CHF vs USD in European hours
        o = load(p).open; days = pd.DatetimeIndex(sorted(set(o.index.normalize())))
        a, b = o.reindex(days + pd.Timedelta(hours=7)).to_numpy(), o.reindex(days + pd.Timedelta(hours=12)).to_numpy()
        x = sgn * (b / a - 1) - 2 * COST[p] / 1e4
        if us_leg:
            c_, d_ = o.reindex(days + pd.Timedelta(hours=13)).to_numpy(), o.reindex(days + pd.Timedelta(hours=20)).to_numpy()
            x = x + (-sgn) * (d_ / c_ - 1) - 2 * COST[p] / 1e4
        s = pd.Series(x, index=days).dropna(); legs.append(s[s.index.dayofweek < 5])
    return pd.concat(legs, axis=1).mean(axis=1)


report("M3 FX seasonality, Europe hours (PRIMARY)", fx_season())
report("M3 variant + US-hours leg", fx_season(True))

cfd = pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")["swap 3.3 (base)"]; cfd = cfd.groupby(cfd.index.floor("D")).sum()


def combo(a, b):
    j = pd.concat([a, b], axis=1).loc["2022-01-01":"2026-09-30"].fillna(0.0); j = j / (j.std() * np.sqrt(365)); x = j.mean(axis=1)
    return float(x.mean() / x.std() * np.sqrt(365))


for r in ROWS:
    x = CANDS[r["test"]]
    r["corr_crypto_cfd_book"] = float(pd.concat([x, cfd], axis=1).dropna().corr().iloc[0, 1])
    r["book_alone"] = float(cfd.loc["2022":].mean() / cfd.loc["2022":].std() * np.sqrt(365)); r["book_plus"] = combo(cfd, x)
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen78_daily.parquet")
T = pd.DataFrame(ROWS); T.to_csv(ROOT / "results/gen78.csv", index=False)
pd.set_option("display.width", 250); print(T.drop(columns=["note"]).round(2).to_string())
