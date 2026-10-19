"""Gen117 (config/gen117_protocol.json): Gen115 intraday ideas on Dukascopy CFDs at CFD costs. Writes results/gen117.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; DK = ROOT / "research_data/dukascopy"
END = "2026-09-30 23:00"
COST = {"US500": 1.0, "US100": 1.0, "WTI": 4.0, "EURUSD": 1.0, "GBPUSD": 1.0, "AUDUSD": 1.0, "USDJPY": 1.0}
SYMS = list(COST) + ["USTBOND"]


def load(s):
    x = pd.read_parquet(DK / f"{s}_1h.parquet")["close"].astype("float64"); x = x[~x.index.duplicated()].sort_index()
    return x.loc["2013-01-01":END]


PX = pd.DataFrame({s: load(s) for s in SYMS}); PX = PX.reindex(pd.date_range(PX.index[0], END, freq="1h"))
R = PX.pct_change(fill_method=None)                                  # move during bar h (bar-start label)
ET = PX.index.tz_localize("UTC").tz_convert("America/New_York")
H = pd.Series(ET.hour, index=PX.index); D = pd.Series(pd.DatetimeIndex(ET.date), index=PX.index); WD = pd.Series(ET.weekday, index=PX.index)


def sh(p, a, b):
    d = p.groupby(p.index.floor("D")).sum().reindex(pd.date_range(a, b)).fillna(0.0); return float(d.mean() / d.std() * np.sqrt(365))


def run(name, P):
    P = P.reindex(index=PX.index).fillna(0.0)
    pnl = sum(P[s] * R[s].fillna(0.0) - P[s].diff().abs().fillna(0.0) * COST[s] / 1e4 for s in P.columns)
    k = (sh(pnl, "2013-01-01", "2018-12-31"), sh(pnl, "2019-01-01", "2022-12-31"), sh(pnl, "2023-01-01", "2026-09-30"))
    r = {"test": name, "DEV": round(k[0], 3), "TEST": round(k[1], 3), "HOLD": round(k[2], 3), "pass": bool(k[0] > 0 and k[1] >= 0.5 and k[2] >= 0.3),
         "active bars": int((P.abs().sum(axis=1) > 0).sum())}
    print(r, flush=True); return r, pnl


def by_date(sig, mask):
    return D[mask].map(sig).fillna(0.0).to_numpy()


rows = []
# X1
s = np.sign(R["USTBOND"][H == 9]).groupby(D[H == 9]).first()
P = pd.DataFrame(0.0, index=PX.index, columns=["US500"]); m = H.between(10, 15); P.loc[m, "US500"] = -by_date(s, m)
rows.append(run("X1 bond-equity lead", P)[0])
# X2
s = np.sign(R["WTI"][(H == 10) & (WD == 2)]).groupby(D[(H == 10) & (WD == 2)]).first()
P = pd.DataFrame(0.0, index=PX.index, columns=["WTI"]); m = H.between(11, 13) & (WD == 2); P.loc[m, "WTI"] = by_date(s, m)
rows.append(run("X2 EIA crude day", P)[0])
# X3
c9 = PX["US500"][H == 9].groupby(D[H == 9]).first().dropna()
days = c9.index; last = days[days.to_series().groupby(days.to_period("M")).transform("max") == days]
mclose = PX["US500"].groupby(D).last().dropna(); mclose = mclose.groupby(mclose.index.to_period("M")).last()
sgn = pd.Series({d: np.sign(c9[d] / mclose.get(d.to_period("M") - 1, np.nan) - 1) for d in last}).dropna()
P = pd.DataFrame(0.0, index=PX.index, columns=["EURUSD", "GBPUSD", "AUDUSD", "USDJPY"]); m = H == 10
v = by_date(sgn, m)
for c, sign in (("EURUSD", 1), ("GBPUSD", 1), ("AUDUSD", 1), ("USDJPY", -1)):
    P.loc[m, c] = 0.25 * sign * v                                    # equities up -> sell USD
rows.append(run("X3 FX month-end fix", P)[0])
# X4
P = pd.DataFrame(0.0, index=PX.index, columns=["US500", "US100"]); m = H.between(10, 15)
for c in ("US500", "US100"):
    c8 = PX[c][H == 8].groupby(D[H == 8]).first(); c17 = PX[c][H == 16].groupby(D[H == 16]).first()   # no 17:00 ET bar (daily break): last price before the 18:00 reopen
    night = np.sign(c8 / c17.shift(1, freq="D").reindex(c8.index) - 1)    # 18:00 previous day -> 09:00
    P.loc[m, c] = -0.5 * by_date(night.dropna(), m)
rows.append(run("X4 overnight-intraday reversal", P)[0])
pd.DataFrame(rows).to_csv(ROOT / "results/gen117.csv", index=False)
