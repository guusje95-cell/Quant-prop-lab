"""Gen82 (config/gen82_protocol.json): 5-minute Opening Range Breakout on US100 / US500 CFDs. Writes results/gen82.csv and
results/cache_gen82_daily.parquet."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PER = {"DEV": ("2018-01-01", "2020-12-31"), "TEST": ("2021-01-01", "2023-12-31"), "HOLD": ("2024-01-01", "2026-10-15"), "ALL": ("2018-01-01", "2026-10-15")}
ROWS, CANDS = [], {}


def orb(sym, risk=0.005, cost_bp=1.0, maxlev=4.0, target_r=10.0):
    d = pd.read_parquet(ROOT / f"research_data/dukascopy/{sym}_5m.parquet").astype("float64")
    d.index = pd.DatetimeIndex(d.index).tz_localize("UTC").tz_convert("America/New_York")
    d = d[~d.index.duplicated()].sort_index()
    d = d[(d.index.dayofweek < 5) & (d.close > 0)]
    tod = d.index.hour * 60 + d.index.minute
    ses = d[(tod >= 570) & (tod <= 955)]                                   # 09:30 .. 15:55 bars
    out, trades = {}, []
    for day, g in ses.groupby(ses.index.normalize()):
        t = g.index.hour * 60 + g.index.minute
        if t[0] != 570 or len(g) < 60:
            continue
        b1 = g.iloc[0]
        side = 1 if b1.close > b1.open else (-1 if b1.close < b1.open else 0)
        if side == 0:
            out[day.tz_localize(None)] = 0.0; continue
        entry = g.iloc[1].open; stop = b1.low if side == 1 else b1.high
        dist = abs(entry - stop) / entry
        if dist <= 0 or (side == 1 and stop >= entry) or (side == -1 and stop <= entry):
            out[day.tz_localize(None)] = 0.0; continue
        lev = min(risk / dist, maxlev); tgt = entry * (1 + side * target_r * dist)
        exit_px = g.iloc[-1].close; why = "eod"
        for i in range(1, len(g)):
            bar = g.iloc[i]
            if side == 1:
                if bar.low <= stop:
                    exit_px = min(stop, bar.open); why = "stop"; break
                if bar.high >= tgt:
                    exit_px = max(tgt, bar.open); why = "target"; break
            else:
                if bar.high >= stop:
                    exit_px = max(stop, bar.open); why = "stop"; break
                if bar.low <= tgt:
                    exit_px = min(tgt, bar.open); why = "target"; break
        pnl = lev * side * (exit_px / entry - 1) - lev * 2 * cost_bp / 1e4
        out[day.tz_localize(None)] = pnl; trades.append((day, side, why, pnl, lev))
    s = pd.Series(out).sort_index()
    tr = pd.DataFrame(trades, columns=["day", "side", "exit", "pnl", "lev"])
    return s, tr


def sharpe(x):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 20 and x.std() > 0 else np.nan


def report(name, s, tr, note=""):
    r = {"test": name, "note": note, "trades": len(tr), "win_rate": float((tr.pnl > 0).mean()), "target_hits": float((tr.exit == "target").mean()),
         "avg_lev": float(tr.lev.mean())}
    for k, (a, b) in PER.items():
        r[f"{k}_sharpe"] = sharpe(s.loc[a:b])
    z = s / (s.std() * np.sqrt(252)) * 0.10; eq = (1 + z).cumprod()
    r["worst_day_at_10pct_vol"] = float(z.min()); r["maxdd_at_10pct_vol"] = float((eq / eq.cummax() - 1).min()); r["ann_ret_raw"] = float(s.mean() * 252)
    ROWS.append(r); CANDS[name] = s; print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


for sym, tag in (("US100", "(PRIMARY)"), ("US500", "")):
    s, tr = orb(sym); report(f"ORB 5-min {sym} {tag}".strip(), s, tr)
    s2, tr2 = orb(sym, cost_bp=2.0); report(f"ORB 5-min {sym}, 2 bp stress", s2, tr2)
s, tr = orb("US100", risk=0.01); report("ORB 5-min US100, 1% risk variant", s, tr)

book = pd.read_parquet(ROOT / "results/cache_gen74_hourly.parquet")["swap 3.3 (base)"]; bookd = book.groupby(book.index.floor("D")).sum()
for r in ROWS:
    x = CANDS[r["test"]]
    j = pd.concat([bookd, x], axis=1).loc["2022":"2026-09"].fillna(0.0); j = j / j.std(); comb = j.mean(axis=1)
    r["corr_book"] = float(pd.concat([bookd, x], axis=1).dropna().corr().iloc[0, 1])
    r["book_alone"] = float(bookd.loc["2022":"2026-09"].mean() / bookd.loc["2022":"2026-09"].std() * np.sqrt(365))
    r["book_plus"] = float(comb.mean() / comb.std() * np.sqrt(365))
pd.DataFrame(CANDS).to_parquet(ROOT / "results/cache_gen82_daily.parquet")
T = pd.DataFrame(ROWS); T.to_csv(ROOT / "results/gen82.csv", index=False)
pd.set_option("display.width", 250); print(T.drop(columns=["note"]).round(3).to_string())
