"""Gen281 (config/gen281_protocol.json): CME basis level vs Coinbase spot (BTC, ETH), vs v8.1. Writes results/gen281.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
END = L.END; days = pd.date_range("2020-01-01", END)


def last_friday(y, m):
    d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
    return d - pd.Timedelta(days=(d.weekday() - 4) % 7)


W = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"]); info = {}
for c in ("BTC", "ETH"):
    d = pd.read_parquet(L.ROOT / f"research_data/databento/{c}_1h.parquet"); d = d[d["symbol"] == f"{c}.v.0"].copy()
    d.index = pd.DatetimeIndex(d["ts_event"]).tz_convert("UTC").tz_localize(None); f = d["close"].astype(float); f = f[~f.index.duplicated()]
    s = pd.read_parquet(L.ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"]; s.index = pd.DatetimeIndex(s.index)
    j = pd.concat([f.rename("F"), s.rename("S")], axis=1).dropna(); j = j.groupby(j.index.floor("D")).last().loc[:END]
    exp = pd.Series([last_friday(t.year, t.month) for t in j.index], index=j.index)
    nxt = pd.Series([last_friday((t + pd.offsets.MonthBegin(1)).year, (t + pd.offsets.MonthBegin(1)).month) for t in j.index], index=j.index)
    exp = exp.where(j.index < exp, nxt); dte = (exp - j.index.to_series()).dt.days.clip(lower=3)
    b = (j["F"] / j["S"] - 1) * 365 / dte; z = ((b - b.rolling(90, min_periods=60).mean()) / b.rolling(90, min_periods=60).std()).reindex(days)
    W[c] = np.where(z > 1, 0.25, np.where(z < -1, -0.25, 0.0)); info[c] = {"basis median %/yr": round(float(b.median() * 100), 2), "days": int(len(b))}
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "basis": info}
L.judge("CME basis level", L.perp(W), out); json.dump(out, open(L.ROOT / "results/gen281.json", "w"), indent=1)
