"""Gen118 (config/gen118_protocol.json): on-chain exchange flows, exchange supply, fee mania, hash ribbons. Writes results/gen118.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen111_xexch.py")}
exec(open(ROOT / "scripts/gen111_xexch.py").read().split("\nw = pd.DataFrame(0.0, index=days")[0], g)
evaluate, rows, days = g["evaluate"], g["rows"], g["days"]
CMD = ROOT / "data/raw/ext/coinmetrics-data/csv"


def cm(c):
    d = pd.read_csv(CMD / f"{c.lower()}.csv", parse_dates=["time"]).set_index("time").sort_index()
    return d.reindex(pd.date_range("2018-01-01", d.index[-1])).shift(2)        # 2-day publication lag (row d uses date d-2)


def hold(ind, n):                                                              # 1 on signal day, kept n days
    return ind.astype(float).rolling(n, min_periods=1).max()


M = {c: cm(c) for c in ("BTC", "ETH")}
W = {k: pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]) for k in ("O1", "O2", "O3", "O4")}
for c, d in M.items():
    n = ((d.FlowInExNtv - d.FlowOutExNtv) / d.SplyCur).rolling(7).sum()
    z = (n - n.rolling(365, min_periods=200).mean()) / n.rolling(365, min_periods=200).std()
    W["O1"][c] = (0.5 * hold(z < -1.5, 3) - 0.5 * hold(z > 1.5, 3)).reindex(days).fillna(0.0)
    e = d.SplyExNtv / d.SplyCur
    W["O2"][c] = (-0.25 * np.sign(e - e.shift(30))).reindex(days).fillna(0.0)
    f = (d.FeeTotNtv * d.PriceUSD).rolling(7).mean()
    zf = (f - f.rolling(365, min_periods=200).mean()) / f.rolling(365, min_periods=200).std()
    W["O3"][c] = (-0.5 * hold(zf > 2, 5)).reindex(days).fillna(0.0)
h = M["BTC"].HashRate; a, b = h.rolling(30).mean(), h.rolling(60).mean(); below = (a < b)
cross = (~below) & below.shift(1, fill_value=False) & (below.astype(int).groupby((~below).cumsum()).cumsum().shift(1) >= 10)
W["O4"]["BTC"] = (0.5 * hold(cross, 30)).reindex(days).fillna(0.0)
print({k: int((v != 0).any(axis=1).sum()) for k, v in W.items()}, "active days", flush=True)
for k, name in (("O1", "O1 exchange net flow"), ("O2", "O2 exchange supply trend"), ("O3", "O3 fee mania"), ("O4", "O4 hash ribbons")):
    evaluate(name, W[k])
pd.DataFrame(rows).to_csv(ROOT / "results/gen118.csv", index=False)
