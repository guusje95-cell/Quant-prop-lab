"""Gen343 (config/gen343_protocol.json): dollar / rates timing of BTC-ETH and ETH/BTC relative trend. Writes results/gen343.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import futures_db as F
END = L.END; ROOT = L.ROOT; days = pd.date_range("2019-01-01", END)
dk = lambda s: pd.read_parquet(ROOT / f"research_data/dukascopy/{s}_1h.parquet")["close"].pipe(lambda x: x[~x.index.duplicated()]).resample("1D").last()
usd = pd.concat([np.log(dk("USDJPY")).diff(), np.log(dk("USDCAD")).diff(), np.log(dk("USDCHF")).diff(),
                 -np.log(dk("EURUSD")).diff(), -np.log(dk("GBPUSD")).diff(), -np.log(dk("AUDUSD")).diff()], axis=1).mean(axis=1)
usd = usd[usd.index.weekday < 5].cumsum()
A_sig = (usd - usd.shift(21) < 0).astype(float).reindex(days, method="ffill")
zn = (1 + F.daily("ZN").r.fillna(0.0)).cumprod(); zn.index = pd.DatetimeIndex(zn.index)
B_sig = (zn / zn.shift(21) - 1 > 0).astype(float).reindex(days, method="ffill")
mk = lambda s: pd.DataFrame({"BTC": 0.5 * s, "ETH": 0.5 * s}).fillna(0.0)
P = CS.B.panel("close", "1D", ["BTC", "ETH"]).reindex(days); ratio = P["ETH"] / P["BTC"]
d = np.sign(ratio - ratio.rolling(50).mean()).fillna(0.0)
W = {"A dollar timing": mk(A_sig), "B rates timing": mk(B_sig), "C macro agreement": mk(A_sig * B_sig),
     "D ETH/BTC relative trend": pd.DataFrame({"BTC": -0.5 * d, "ETH": 0.5 * d})}
vd = L.V7.groupby(L.V7.index.floor("D")).sum(); out = {}
for nm, w in W.items():
    h = CS._from_daily_weights(w.loc["2019-06-01":], ["BTC", "ETH"], 5).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
    s = [round(x, 3) for x in L.per(h, "2020-01-01")]
    c = float(pd.concat([h.groupby(h.index.floor("D")).sum(), vd], axis=1).loc["2022-01-01":END].corr().iloc[0, 1])
    out[nm] = {"sleeve DEV / TEST / HOLD": s, "corr v8.6 2022-26": round(c, 3), "share of days invested": round(float((w.loc["2020":] != 0).any(axis=1).mean()), 2),
               "orthogonal candidate": bool(s[0] > 0 and s[1] >= 0.8 and s[2] >= 0.5 and abs(c) <= 0.2)}
    print(nm, out[nm], flush=True)
# buy-and-hold reference (not a trial): long BTC/ETH 0.5 each always
h = CS._from_daily_weights(mk(pd.Series(1.0, index=days)).loc["2019-06-01":], ["BTC", "ETH"], 5).loc[:END + " 23:00"].reindex(L.H6.index).fillna(0.0)
out["reference: buy and hold BTC/ETH"] = {"DEV / TEST / HOLD": [round(x, 3) for x in L.per(h, "2020-01-01")]}
print(out["reference: buy and hold BTC/ETH"])
json.dump(out, open(ROOT / "results/gen343.json", "w"), indent=1)
