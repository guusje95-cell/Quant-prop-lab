"""VAL-8 (protocol research/v99/val8_protocol.json): the daily stop and the firm's daily limit on the 5-minute equity path vs the
hourly path. Writes results/v99/val8_intrahour_stop.json."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
run = g0["run"]
STOP, LIMIT = 0.025, 0.05
PER = (("2022", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))


def bars(coins):
    c, lo, hi = {}, {}, {}
    for k in coins:
        f = ROOT / f"research_data/binance/{k}USDT_5m.parquet"
        if f.exists():
            x = pd.read_parquet(f, columns=["high", "low", "close"]); x = x[~x.index.duplicated()]
            c[k], lo[k], hi[k] = x.close, x.low, x.high
    return pd.DataFrame(c), pd.DataFrame(lo), pd.DataFrame(hi)


def analyse(net: pd.DataFrame, risk: float):
    net = net.loc["2022-01-01":"2026-09-30 23:00"]; coins = list(net.columns); C, LO, HI = bars(coins)
    ix5 = pd.date_range(net.index[0], net.index[-1] + pd.Timedelta(minutes=55), freq="5min")
    C = C.reindex(ix5).ffill(); prev = C.shift(1)
    P = net.reindex(ix5.floor("h")).set_axis(ix5).fillna(0.0)[C.columns] * risk
    r = (C / prev - 1).fillna(0.0); pnl = (P * r).sum(axis=1).to_numpy()
    adv = (P.clip(lower=0) * (LO.reindex(ix5) / prev - 1).fillna(0.0) + P.clip(upper=0) * (HI.reindex(ix5) / prev - 1).fillna(0.0)).sum(axis=1).to_numpy()
    gross = P.abs().sum(axis=1).to_numpy()
    n = len(ix5) // 288; pnl = pnl[:n * 288].reshape(n, 288); adv = adv[:n * 288].reshape(n, 288); gross = gross[:n * 288].reshape(n, 288)
    days = pd.date_range(net.index[0].normalize(), periods=n)
    cum = pnl.cumsum(axis=1); before = np.c_[np.zeros(n), cum[:, :-1]]; worst = before + adv           # equity at each bar's adverse extreme
    out = {}
    def rule(step, name):
        d = np.zeros(n); stops = 0; br_close = 0; br_ext = 0
        for i in range(n):
            chk = cum[i, step - 1::step]; hit = np.flatnonzero(chk <= -STOP)
            if len(hit):
                j = (hit[0] + 1) * step - 1; d[i] = cum[i, j] - 0.001 * gross[i, j]; stops += 1
            else:
                j = 287; d[i] = cum[i, -1]
            br_close += cum[i, :j + 1].min() <= -LIMIT; br_ext += worst[i, :j + 1].min() <= -LIMIT
        s = pd.Series(d, index=days); sh = lambda x: float(x.mean() / x.std() * np.sqrt(365))
        out[name] = {"sharpe (gross)": round(sh(s), 3), "periods": [round(sh(s.loc[a:b]), 3) for a, b in PER], "annual return %": round(float(s.mean() * 36500), 1),
                     "stop days": stops, "worst day %": round(float(s.min() * 100), 2), "breach days (5-min close <= -5% before the stop)": int(br_close),
                     "breach days (adverse extremes, upper bound)": int(br_ext)}
    full = pd.Series(cum[:, -1], index=days)
    out["no stop"] = {"sharpe (gross)": round(float(full.mean() / full.std() * np.sqrt(365)), 3), "worst day %": round(float(full.min() * 100), 2),
                      "days with a 5-min close <= -2.5% / <= -5%": [int((cum.min(axis=1) <= -STOP).sum()), int((cum.min(axis=1) <= -LIMIT).sum())],
                      "days ending <= -2.5%": int((cum[:, -1] <= -STOP).sum())}
    rule(12, "A: stop on hourly closes (research)"); rule(1, "B: stop on 5-minute closes (live)")
    return out


res = {}
g1 = run("cn1_crypto_netting.py", "book = ph.loc")
scale = json.loads((ROOT / "config/paper_v98.json").read_text())["frozen"]["v98_scale"]
for risk in (1.5, 2.0):
    res[f"crypto v9.8 non-event sleeves, risk {risk}"] = analyse(g1["net"] * scale, risk)
(ROOT / "results/v99/val8_intrahour_stop.json").write_text(json.dumps(res, indent=1))
g2 = run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
res["CFD bf2.8 crypto sleeves, risk 1.75"] = analyse(g2["net"].reindex(columns=g2["coins"]).fillna(0.0), 1.75)
print(json.dumps(res, indent=1)); (ROOT / "results/v99/val8_intrahour_stop.json").write_text(json.dumps(res, indent=1))
