"""Gen306 (config/gen306_protocol.json). Writes results/gen306.json."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import ridge_live as RL
import alt_kimchi as AK
import v7lab as L
import bf2lab as F
import cfd_book as CB
from qpl.lab import binance_pack as B
END = L.END
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
cfdr = lambda D: F.cfd(D.pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5)
F.judge("A bf2.2 + kimchi breadth", cfdr(RL.predictions(END, spot=True, vrp=True, cal=True, kb=True)), out, dev_start="2021-01-01", replace_ridge=True)
F.judge("B bf2.2 vol-scaled target", cfdr(RL.predictions(END, spot=True, vrp=True, cal=True, volscale=True)), out, dev_start="2021-01-01", replace_ridge=True)
# C: Gen270 sleeve (CB.SPREAD already at measured costs via bf2lab)
spec = pd.read_csv(sorted((F.ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
w = AK.weights(END + " 23:00"); coins = [c for c in w.columns if meas.get(c, 1e9) <= 50]; w = w[coins]
cost = pd.Series({c: 0.5 * meas[c] + 1.2 for c in coins}) / 1e4
H = B.panel("close", "1h", coins).loc[:END + " 23:00"]; r = H.pct_change(fill_method=None).fillna(0.0)
held = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
h = ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)
F.judge("C bf2.2 + alt kimchi", h, out)
# D: ridge forecast on an altcoin basket
D = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True)
p = D.pivot(index="day", columns="coin", values="ridge").fillna(0.0).mean(axis=1)
alts = [c for c in B.coins() if c not in ("BTC", "ETH")]
wd = pd.DataFrame({c: p * (2 * 0.5 / len(alts)) for c in alts})
L.judge("D ridge on altcoin basket", L.perp(wd), out, dev_start="2021-01-01")
json.dump(out, open(L.ROOT / "results/gen306.json", "w"), indent=1)
