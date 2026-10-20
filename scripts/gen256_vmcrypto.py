"""Gen256 (config/gen256_protocol.json): vol-managed long BTC/ETH in v7 and bf2. Writes results/gen256.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END
out = {}
P = B.panel("close", "1D", ["BTC", "ETH"]).loc[:END]; vol = P.pct_change(fill_method=None).rolling(20).std() * np.sqrt(365)
w = (0.5 * (0.40 / vol).clip(upper=1.0)).fillna(0.0)
L.judge("vol-managed long BTC/ETH (v7)", L.perp(w), out)
g = {"__file__": str(L.ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(L.ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, CB, IDXbf, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
q = {"__file__": str(L.ROOT / "scripts/gen232_bf_p1.py")}; exec(open(L.ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
IS0 = (P6 + R1 + q["p1"]()).rename("vol-managed indices")
bk = lambda extra: CS.portfolio_v5(pd.concat([HB0, IS0, hb.rename("ridge ML")] + extra, axis=1).fillna(0.0))[0]
b0 = bk([]); B0, k0 = sh(b0, "2022-01-01", END), per(b0, "2022-01-01")
hc = sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))))
s = per(hc, "2020-01-01"); b1 = bk([hc.rename("vm crypto")]); B1, k1 = sh(b1, "2022-01-01", END), per(b1, "2022-01-01")
out["bf2"] = {"reference": [round(B0, 3), np.round(k0, 3).tolist()], "sleeve D/T/H": np.round(s, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
              "pass": bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
print(out["bf2"]); json.dump(out, open(L.ROOT / "results/gen256.json", "w"), indent=1)
