"""Gen295 (config/gen295_protocol.json): bf2 with the v8.3 ridge. Writes results/gen295.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import ridge_live as RL
w = RL.predictions(F.END, kb=True, volscale=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
out = {"reference bf2": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
F.judge("v8.3 ridge in bf2", F.cfd(w), out, dev_start="2021-01-01", replace_ridge=True)
json.dump(out, open(F.ROOT / "results/gen295.json", "w"), indent=1)
