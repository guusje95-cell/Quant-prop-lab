"""Gen125 (config/gen125_protocol.json): noise-area breakout and 5-minute ORB on real ES/NQ futures, month-end pension rebalancing.
Writes results/gen125.csv and results/gen125_daily.parquet."""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
import futures_db as F
from qpl.lab import data as D, engine as EN
from qpl.lab.strategies_papers import NoiseAreaMomentum
warnings.filterwarnings("ignore")
SPL = (("2018-01-01", "2020-12-31"), ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-09-30"))
rows, PNL = [], {}


def sharpe(p, a, b):
    x = p.loc[a:b]; x = x[x.index.weekday < 5]
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else float("nan")


def report(name, p, splits=SPL, extra=None):
    p = p.sort_index(); k = tuple(round(sharpe(p, a, b), 3) for a, b in splits)
    r = {"test": name, "DEV": k[0], "TEST": k[1], "HOLD": k[2], "pass": bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3), **(extra or {})}
    rows.append(r); PNL[name] = p; print(r, flush=True)


def bars5(root):
    """5-minute bars (UTC-naive, labelled by start) from the 1-minute front contract, back-adjusted proportionally at rolls."""
    d = pd.read_parquet(F.DB / f"{root}_1m.parquet")
    d.index = pd.to_datetime(d["ts_event"], utc=True).dt.tz_localize(None); d = d[~d.index.duplicated()].sort_index().loc[:"2026-09-30 23:59"]
    px = d[["open", "high", "low", "close"]].astype("float64")
    roll = d.instrument_id.ne(d.instrument_id.shift(1)) & d.instrument_id.shift(1).notna()
    ratio = pd.Series(1.0, index=d.index)
    ratio[roll] = (px.open[roll] / px.close.shift(1)[roll]).to_numpy()     # new contract's first open / old contract's last close
    adj = ratio[::-1].cumprod()[::-1].shift(-1).fillna(1.0)                   # factor applied to all earlier bars
    px = px.mul(adj, axis=0)
    o = px.open.resample("5min").first(); h = px.high.resample("5min").max(); lo = px.low.resample("5min").min(); c = px.close.resample("5min").last()
    v = d.volume.astype(float).resample("5min").sum()
    out = pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": v}).dropna(subset=["close"])
    return out


def med_cost(root, half_tick=False):
    dd = F.daily(root).loc["2018":"2026-09"]; tick, mult, micro = F.SPEC[root][:3]
    c = (0.5 * tick / dd.close + F.COMMISSION["micro"] / (dd.close * micro)) if half_tick else F.cost_frac(root, dd.close)
    return float(c.median() * 1e4)


def noise(root, cost_bp):
    d = B5[root]; w = {k: d[[k]].rename(columns={k: root}) for k in ("open", "high", "low", "close", "volume")}
    b = D.Bars(f"{root} 5m", "5m", *(w[k] for k in ("open", "high", "low", "close", "volume")), periods_per_year=D.periods_per_year(d.index, "5m"))
    st = NoiseAreaMomentum(); sig = st.signal(b, st.defaults())
    cfg = EN.Config(cost_bps=cost_bp); r = EN.run(b, EN.size(b, sig, cfg, "raw"), cfg)
    dd = EN.to_daily(r["bars"], b.freq)["net"]; dd = dd[dd.index >= dd.index[0] + pd.Timedelta(days=21)]
    return dd[dd.index.dayofweek < 5]


def orb(root, cost_bp, risk=0.005, maxlev=4.0, target_r=10.0):
    d = B5[root].copy(); d.index = pd.DatetimeIndex(d.index).tz_localize("UTC").tz_convert("America/New_York")
    d = d[(d.index.dayofweek < 5) & (d.close > 0)]
    tod = d.index.hour * 60 + d.index.minute; ses = d[(tod >= 570) & (tod <= 955)]
    out = {}
    for day, g in ses.groupby(ses.index.normalize()):
        t = g.index.hour * 60 + g.index.minute
        if t[0] != 570 or len(g) < 60:
            continue
        b1 = g.iloc[0]; side = 1 if b1.close > b1.open else (-1 if b1.close < b1.open else 0)
        if side == 0:
            out[day.tz_localize(None)] = 0.0; continue
        entry = g.iloc[1].open; stop = b1.low if side == 1 else b1.high; dist = abs(entry - stop) / entry
        if dist <= 0 or (side == 1 and stop >= entry) or (side == -1 and stop <= entry):
            out[day.tz_localize(None)] = 0.0; continue
        lev = min(risk / dist, maxlev); tgt = entry * (1 + side * target_r * dist); exit_px = g.iloc[-1].close
        for i in range(1, len(g)):
            bar = g.iloc[i]
            if side == 1:
                if bar.low <= stop:
                    exit_px = min(stop, bar.open); break
                if bar.high >= tgt:
                    exit_px = max(tgt, bar.open); break
            else:
                if bar.high >= stop:
                    exit_px = max(stop, bar.open); break
                if bar.low <= tgt:
                    exit_px = min(tgt, bar.open); break
        out[day.tz_localize(None)] = lev * side * (exit_px / entry - 1) - lev * 2 * cost_bp / 1e4
    return pd.Series(out).sort_index()


B5 = {r: bars5(r) for r in ("ES", "NQ")}
COST = {r: med_cost(r) for r in B5}; HALF = {r: med_cost(r, True) for r in B5}
print("cost bp/side:", {k: round(v, 2) for k, v in COST.items()}, "half-tick:", {k: round(v, 2) for k, v in HALF.items()}, flush=True)
avg = lambda xs: pd.concat(xs, axis=1).fillna(0.0).mean(axis=1)
k1 = {r: noise(r, COST[r]) for r in B5}
report("K1 noise-area breakout ES+NQ (PRIMARY)", avg(k1.values()))
for r in B5:
    report(f"K1 noise-area {r} (component)", k1[r])
report("K1 at half-tick cost (report only)", avg([noise(r, HALF[r]) for r in B5]))
k2 = {r: orb(r, COST[r]) for r in B5}
report("K2 5-minute ORB ES+NQ", avg(k2.values()))
for r in B5:
    report(f"K2 ORB {r} (component)", k2[r])
report("K2 at half-tick cost (report only)", avg([orb(r, HALF[r]) for r in B5]))
# K3 pension rebalancing
es, zn = F.daily("ES"), F.daily("ZN"); R = pd.DataFrame({"ES": es.r, "ZN": zn.r}).dropna()
vol = R.ES.rolling(60).std() * np.sqrt(252); W = pd.Series(0.0, index=R.index)
for _, g in R.groupby(R.index.to_period("M")):
    if len(g) < 6:
        continue
    d4 = g.index[-4]; mtd = (1 + g.loc[:d4]).prod() - 1
    W.loc[g.index[-3:]] = (-1.0 if mtd.ES > mtd.ZN else 1.0) * 0.15 / vol.loc[d4]
cst = es.cost.reindex(R.index).ffill(); roll = es.roll.reindex(R.index).fillna(0)
turn = W.diff().abs().fillna(W.abs()) + 2 * W.abs() * roll
report("K3 month-end pension rebalancing (ES)", W * R.ES - turn * cst,
       splits=(("2010-06-01", "2017-12-31"), ("2018-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30")))
pd.DataFrame(rows).to_csv(ROOT / "results/gen125.csv", index=False)
pd.DataFrame(PNL).to_parquet(ROOT / "results/gen125_daily.parquet")
