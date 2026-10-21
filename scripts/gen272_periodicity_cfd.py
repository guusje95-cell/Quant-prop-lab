"""Gen272 (config/gen272_protocol.json): intraday periodicity on US index CFDs at BrightFunded costs, in bf2. Writes results/gen272.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
END = F.END; COST = {"US100": 0.31e-4, "US500": 0.66e-4, "US30": 0.19e-4}


def prep(s):
    x = F.hourly(s).loc[:END + " 23:00"]; et = x.index.tz_localize("UTC").tz_convert("America/New_York")
    r = x.close.pct_change(fill_method=None)
    r[(x.index.to_series().diff() > pd.Timedelta(hours=1)).to_numpy()] = np.nan          # no return across data gaps / closes
    df = pd.DataFrame({"r": r.to_numpy(), "h": et.hour, "d": pd.DatetimeIndex(et.date)}, index=x.index)
    df["vol"] = df.r.rolling(24 * 60, min_periods=24 * 20).std().shift(1)
    return df


def pnl(df, N, k, cost):
    piv = df.pivot_table(index="d", columns="h", values="r", aggfunc="sum")
    m = piv.rolling(N, min_periods=int(N * 0.8)).mean().shift(1); sd = piv.rolling(N, min_periods=int(N * 0.8)).std().shift(1)
    tt = m / (sd / np.sqrt(N)); sig = np.sign(tt).where(tt.abs() > k, 0.0)
    x = df.join(sig.stack().rename("sig"), on=["d", "h"])
    w = (x.sig.fillna(0.0) * 0.10 / (x.vol * np.sqrt(24 * 252)) / 3).where(lambda z: np.isfinite(z), 0.0)
    return w * x.r.fillna(0.0) - w.diff().abs().fillna(0.0) * cost


P = {s: prep(s) for s in COST}; rep = []; best = None
for N in (20, 60, 250):
    for k in (0, 1, 2):
        h = sum(pnl(P[s], N, k, COST[s]).reindex(F.IDXbf.union(P[s].index)).fillna(0.0) for s in COST)
        d = h.groupby(h.index.floor("D")).sum().loc["2014-01-01":"2022-12-31"]; d = d[d.index.weekday < 5]
        st = float(d.mean() / d.std() * np.sqrt(252)); rep.append({"N": N, "k": k, "2014-22": round(st, 3)}); print(rep[-1], flush=True)
        if best is None or st > best[0]:
            best = (st, N, k, h)
out = {"grid (selection 2014-22)": rep, "chosen": {"N": best[1], "k": best[2], "2014-22": round(best[0], 3)}, "enters": bool(best[0] > 0.3)}
if out["enters"]:
    r = F.judge(f"periodicity N={best[1]} k={best[2]}", best[3].reindex(F.IDXbf).fillna(0.0), out)
print(json.dumps(out)[:600]); json.dump(out, open(F.ROOT / "results/gen272.json", "w"), indent=1)
