"""Gen278 (config/gen278_protocol.json): one alt-kimchi sleeve on 44 coins replacing v8.1's 16-coin sleeve. Writes results/gen278.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
import alt_kimchi as AK
B, END = L.B, L.END; MORE = L.ROOT / "research_data/more"; X = L.ROOT / "research_data/binance_extra"
days = pd.date_range("2020-01-01", END); fx = RL.usdkrw(); k = 16 / 44
w16 = AK.weights(END + " 23:00") * k
h16 = L.perp(w16)                                                   # 5 bp + funding
W = {}; closes = {}
for p in sorted(X.glob("*USDT_1h.parquet")):
    perp = p.name.split("USDT_")[0]; c = perp.replace("1000", ""); mult = 1000.0 if perp.startswith("1000") else 1.0
    f = MORE / f"upbit_KRW-{c}_1h.parquet"
    if not f.exists():
        continue
    up = pd.read_parquet(f)["close"]; up.index = pd.DatetimeIndex(up.index)
    bn = pd.read_parquet(p)["close"]; bn.index = pd.DatetimeIndex(bn.index); bn = bn[~bn.index.duplicated()].loc[:END + " 23:00"]
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up * mult / fxh / bn.reindex(up.index) - 1).dropna(); kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    z = ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
    W[perp] = np.where(z > 1, 0.1 * k, np.where(z < -1, -0.1 * k, 0.0)); closes[perp] = bn
W = pd.DataFrame(W, index=days); H = pd.DataFrame(closes).sort_index(); r = H.pct_change(fill_method=None).fillna(0.0)
held = W.reindex(W.index.append(pd.DatetimeIndex([W.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
h28 = (held * r).sum(axis=1) - held.diff().abs().sum(axis=1).where(r.index.hour == 0, 0.0) * 10 / 1e4
h = (h16.reindex(L.H6.index).fillna(0.0) + h28.reindex(L.H6.index).fillna(0.0)).rename("alt kimchi")
bk = L.CS.portfolio_v5(pd.concat([L.H6, L.RIDGE, h], axis=1).fillna(0.0))[0]
B1, k1 = L.sh(bk, "2022-01-01", END), L.per(bk, "2022-01-01")
out = {"reference v8.1": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "coins": 16 + W.shape[1],
       "44-coin sleeve D/T/H": np.round(L.per(h, "2020-01-01"), 3).tolist(), "16-coin sleeve D/T/H": np.round(L.per(L.ALTK[0], "2020-01-01"), 3).tolist(),
       "book": [round(B1, 3), np.round(k1, 3).tolist()], "pass": bool(B1 > L.REF[0] and k1[1] >= L.REF[1][1] and k1[2] >= L.REF[1][2])}
print(out); json.dump(out, open(L.ROOT / "results/gen278.json", "w"), indent=1)
