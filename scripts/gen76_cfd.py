"""Gen76 (config/gen76_protocol.json): option-expiration week and cross-index weekly reversal. Writes results/gen76_cfd.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("g75h", ROOT / "scripts/gen75_cfd.py")
# reuse only helpers: re-define to avoid running gen75
COST = {"US100": 1.0, "US500": 1.0, "US30": 1.0, "DE40": 1.0}
FIN = 0.03 / 365
DUK = ROOT / "research_data" / "dukascopy"
PER = {"DEV": ("2013-01-01", "2019-12-31"), "TEST": ("2020-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-09-30"), "ALL": ("2013-01-01", "2026-09-30")}
ROWS, CANDS = [], {}


def daily_close(sym):
    tz, hr = ("Europe/Berlin", 17) if sym == "DE40" else ("America/New_York", 15)
    d = pd.read_parquet(DUK / f"{sym}_1h.parquet").astype("float64"); d.index = pd.DatetimeIndex(d.index).tz_localize("UTC").tz_convert(tz)
    c = d.close[(d.index.hour == hr) & (d.close > 0)]; c.index = c.index.tz_localize(None).normalize()
    return c[~c.index.duplicated()]


def sharpe(x):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, daily):
    r = {"test": name, "days_active": int((daily != 0).sum())}
    for k, (a, b) in PER.items():
        r[f"{k}_sharpe"] = sharpe(daily.loc[a:b])
    z = daily / (daily.std() * np.sqrt(252)) * 0.10; r["worst_day_at_10pct_vol"] = float(z.min())
    ROWS.append(r); CANDS[name] = daily; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


def pnl_from_pos(sym, pos):
    c = daily_close(sym); pos = pos.reindex(c.index).fillna(0.0); held = pos.shift(1).fillna(0)
    nights = pd.Series(c.index, index=c.index).diff().dt.days.fillna(1)
    return held * c.pct_change().fillna(0) - pos.diff().abs().fillna(0) * COST[sym] / 1e4 - held.abs() * nights * FIN


def third_fridays(idx):
    m = pd.period_range(idx.min(), idx.max(), freq="M")
    out = []
    for p in m:
        d = pd.Timestamp(p.start_time); fr = d + pd.offsets.Week(weekday=4) if d.dayofweek != 4 else d
        out.append(fr + pd.Timedelta(days=14))
    return pd.DatetimeIndex(out)


def opex(sym, after=False):
    c = daily_close(sym); pos = pd.Series(0.0, index=c.index)
    for f in third_fridays(c.index):
        a, b = (f, f + pd.Timedelta(days=7)) if after else (f - pd.Timedelta(days=7), f)
        # position decided at the close of day a (held from a's close to b's close): pos=1 on trading days in [a, b)
        days = c.index[(c.index >= a) & (c.index < b)]
        pos.loc[days] = -1.0 if after else 1.0
    return pnl_from_pos(sym, pos)


report("O1 OPEX week long, US500+US100 (PRIMARY)", pd.concat([opex("US500"), opex("US100")], axis=1).fillna(0).mean(axis=1))
report("O1 variant: short the week after", pd.concat([opex("US500", True), opex("US100", True)], axis=1).fillna(0).mean(axis=1))

IDX = ["US500", "US100", "US30", "DE40"]


def xrev(weeks=1):
    C = pd.DataFrame({s: daily_close(s) for s in IDX})
    fri = C.index[C.index.dayofweek == 4]
    wk = C.loc[fri]; ret = wk / wk.shift(weeks) - 1
    pos = pd.DataFrame(0.0, index=C.index, columns=IDX)
    for i, d in enumerate(fri):
        r = ret.loc[d].dropna()
        if len(r) < 4:
            continue
        nxt = fri[i + 1] if i + 1 < len(fri) else C.index[-1] + pd.Timedelta(days=1)
        days = C.index[(C.index >= d) & (C.index < nxt)]
        pos.loc[days, r.idxmin()] = 1.0; pos.loc[days, r.idxmax()] = -1.0
    return pd.concat([pnl_from_pos(s, pos[s]) for s in IDX], axis=1).fillna(0).sum(axis=1) / 2


report("O2 cross-index weekly reversal (PRIMARY)", xrev(1))
report("O2 variant: 2-week ranking", xrev(2))

cfd = pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")["swap 3.3 (base)"]; cfd = cfd.groupby(cfd.index.floor("D")).sum()


def combo(a, b):
    j = pd.concat([a, b], axis=1).loc["2022-01-01":"2026-09-30"].fillna(0.0); j = j / (j.std() * np.sqrt(365)); x = j.mean(axis=1)
    return float(x.mean() / x.std() * np.sqrt(365))


for r in ROWS:
    r["cfd_portfolio_alone"] = float(cfd.loc["2022":].mean() / cfd.loc["2022":].std() * np.sqrt(365)); r["cfd_portfolio_plus"] = combo(cfd, CANDS[r["test"]])
T = pd.DataFrame(ROWS); T.to_csv(ROOT / "results/gen76_cfd.csv", index=False); print(T.round(2).to_string())
