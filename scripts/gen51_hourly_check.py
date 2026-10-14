"""Gen51 validation: replay frozen daily C* weights on HOURLY prices, apply the -3% daily equity stop on the real hourly
path (fill at the hourly close where it triggers, minus 0.1% slippage), and compare prop outcomes with the daily-candle
approximation over the same period."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, propfirms as PF, scorecard as SC, strategies as S

src = D.list_sources()
cd = src["Binance spot majors (daily, 2017+)"]()
ch = src["Binance spot majors (hourly, 2022+)"]()
cfg = EN.Config(cost_bps=7.5, leverage=0.79)
st = S.CStarTrend(); w = EN.size(cd, st.signal(cd, st.defaults()), cfg)        # daily weights decided at the daily close
held_d = w.shift(1).fillna(0.0)                                                  # held during day t
hc = ch.close[cd.symbols].sort_index()
hret = hc.pct_change(fill_method=None).fillna(0.0)
day = hret.index.floor("D")
H = pd.DataFrame(held_d.reindex(day).to_numpy(), index=hret.index, columns=cd.symbols).fillna(0.0)
turn = held_d.diff().abs().sum(axis=1) * 7.5 / 1e4                              # daily rebalancing cost, paid at the day start
port = (H * hret).sum(axis=1)
out = []
for stop in (None, 0.03):
    rows = []
    for dd, g in port.groupby(day):
        if dd not in turn.index:
            continue
        eq = np.cumprod(1 + g.to_numpy()) * (1 - turn.loc[dd])
        path = np.concatenate([[1 - turn.loc[dd]], eq])
        if stop is not None and (path <= 1 - stop).any():
            k = int(np.argmax(path <= 1 - stop))
            close = path[k] - 0.001                                              # out at that hour's close, 0.1% slippage
            rows.append((dd, close - 1, min(path[:k + 1].min(), close) - 1, path[:k + 1].max() - 1))
        else:
            rows.append((dd, path[-1] - 1, path.min() - 1, path.max() - 1))
    out.append(pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day"))
plain_h, stop_h = out
daily = SC.run(S.CStarTrend, cd, SC.SETUPS["C* trend + breakout (E2)"])["daily"].loc[plain_h.index[0]:plain_h.index[-1]]
f = PF.PRESETS["Crypto Fund Trader 1-Phase $100k"]
print("period", plain_h.index[0].date(), plain_h.index[-1].date(), "days", len(plain_h))
print("worst day plain hourly path", round(plain_h['worst'].min(), 3), "| daily-candle approx", round(daily['worst'].min(), 3))
print("days breaching -3% intraday: hourly", int((plain_h['worst'] <= -0.03).sum()), "daily-candle", int((daily['worst'] <= -0.03).sum()))
print("stop days: realised loss on those days (hourly fills):", stop_h.loc[stop_h['net'] <= -0.029, 'net'].describe().round(4).to_dict())
for tag, dd_, ff in (("daily candles, no stop", daily, f), ("daily candles + stop approx", daily, PF.replace(f, stop_frac=0.75)),
                     ("HOURLY path, no stop", plain_h, f), ("HOURLY path + real stop", stop_h, f)):
    a = PF.attempts(dd_, ff, 1.0); p = PF.pipeline(dd_, ff, 5, 1, 1.0, 0.4, horizon_days=730, method="bootstrap", n_boot=400)
    print(f"{tag:30s} pass {a['P_pass']:.0%} (daily {a['P_fail_daily']:.0%} max {a['P_fail_max']:.0%}) | funded {p['P_funded']:.0%} "
          f"net {p['net_mean']:7.0f} p50 {p['net_p50']:7.0f} P(profit) {p['P_profit']:.0%}")
