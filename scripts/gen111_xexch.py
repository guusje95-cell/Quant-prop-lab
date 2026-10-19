"""Gen111 (config/gen111_protocol.json): cross-exchange funding divergence and OKX perp premium. Writes results/gen111.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, B, H6, B0, k0, per, sh, cst = (g[k] for k in ("CS", "B", "H6", "B0", "k0", "per", "sh", "cst"))
f = {"__file__": str(ROOT / "scripts/gen106_intraday.py")}
exec(open(ROOT / "scripts/gen106_intraday.py").read().split("\nb0, H0 = book(pos); k0")[0], f)
CB, Rbf, pos, IDXbf, book, sleeve = (f[k] for k in ("CB", "R", "pos", "IDX", "book", "sleeve"))
bb0, HB0 = book(pos); kb0 = per(bb0, "2022-01-01"); BB0 = sh(bb0, "2022-01-01", "2026-09-30")
END = "2026-09-30"; days = pd.date_range("2020-01-01", END); rows = []


def evaluate(name, w):
    hp = CS._from_daily_weights(w, ["BTC", "ETH"], 5).loc[:END + " 23:00"]
    p = per(hp, "2020-01-01"); v = CS.portfolio_v5(pd.concat([H6, hp.rename(name)], axis=1).fillna(0.0))[0]; k1 = per(v, "2022-01-01")
    hb = sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))))
    vb = CS.portfolio_v5(pd.concat([HB0, hb.rename(name)], axis=1).fillna(0.0))[0]; kb1 = per(vb, "2022-01-01")
    r = {"test": name, "DEV": p[0], "TEST": p[1], "HOLD": p[2], "corr C*": float(pd.concat([cst, hp.groupby(hp.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]),
         "v6 before/after": [round(B0, 3), round(sh(v, "2022-01-01", "2026-09-30"), 3)], "v6 TEST/HOLD after": np.round(k1[1:], 3).tolist(),
         "bf before/after": [round(BB0, 3), round(sh(vb, "2022-01-01", "2026-09-30"), 3)], "bf TEST/HOLD before/after": [np.round(kb0[1:], 3).tolist(), np.round(kb1[1:], 3).tolist()]}
    r["pass v6"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v6 before/after"][1] > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    r["pass bf"] = bool(p[0] > 0 and p[1] >= 0.5 and p[2] >= 0.3 and r["bf before/after"][1] > BB0 and kb1[1] >= kb0[1] and kb1[2] >= kb0[2])
    rows.append(r); print({k: (round(v_, 3) if isinstance(v_, float) else v_) for k, v_ in r.items()}, flush=True)


w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    fb = B.funding(c); fbd = fb.groupby((fb.index - pd.Timedelta(seconds=1)).floor("D")).mean().reindex(days)
    dr = pd.read_parquet(ROOT / f"data/raw/deribit/{c}-PERPETUAL_funding.parquet")["interest_8h"]
    drd = dr.groupby(dr.index.floor("D")).mean().reindex(days)              # hourly values of day d (to 23:00 bar end)
    div = fbd.rolling(7).mean() - drd.rolling(7).mean()
    z = (div - div.rolling(90, min_periods=60).mean()) / div.rolling(90, min_periods=60).std()
    w[c] = np.where(z > 1, -0.5, np.where(z < -1, 0.5, 0.0))
evaluate("F1 funding divergence Binance-Deribit, contrarian", w)
w = pd.DataFrame(0.0, index=days, columns=["BTC", "ETH"])
for c in ("BTC", "ETH"):
    ok = pd.read_parquet(ROOT / f"data/raw/okx/{c}-USDT-SWAP_1H.parquet")["close"]
    bn = B.k5(c).close.resample("1h").last()
    p = (ok / bn.reindex(ok.index) - 1).dropna().loc[:END + " 23:00"]
    p24 = p.rolling(24, min_periods=20).mean(); z = ((p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std())
    zd = z[z.index.hour == 23]; zd.index = zd.index.floor("D"); zd = zd.reindex(days)
    w[c] = np.where(zd > 1, 0.5, np.where(zd < -1, -0.5, 0.0))
evaluate("F2 OKX-Binance perp premium momentum", w)
pd.DataFrame(rows).to_csv(ROOT / "results/gen111.csv", index=False)
print("done", flush=True)
