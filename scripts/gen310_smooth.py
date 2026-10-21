"""Gen310 (config/gen310_protocol.json): two-day smoothed ridge positions. Writes results/gen310.json."""
import json
import numpy as np
import ridge_live as RL
import v7lab as L
import bf2lab as F
END = L.END
out = {"reference v8.4": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.3": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
wv = RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0)
wb = RL.predictions(END, spot=True, vrp=True, cal=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0)
sm = lambda w: 0.5 * (w + w.shift(1).fillna(0.0)) * 0.5
out["turnover v8.4 raw / smoothed"] = [float((wv * 0.5).diff().abs().sum().sum()), float(sm(wv).diff().abs().sum().sum())]
L.judge("smoothed ridge v8.4", L.perp(sm(wv)), out, dev_start="2021-01-01", replace_ridge=True)
F.judge("smoothed ridge bf2.3", F.cfd(sm(wb)), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen310.json", "w"), indent=1)
