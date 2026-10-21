"""Gen303 (config/gen303_protocol.json): v8.3 ridge + VRP + calendar (A), + spot flow (B). Writes results/gen303.json."""
import json
import numpy as np
import v7lab as L
import ridge_live as RL
END = L.END
out = {"reference v8.3": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
for k, spot in (("A VRP + calendar", False), ("B VRP + calendar + spot flow", True)):
    w = RL.predictions(END, spot=spot, kb=True, volscale=True, vrp=True, cal=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
    L.judge(k, L.perp(w), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(L.ROOT / "results/gen303.json", "w"), indent=1)
