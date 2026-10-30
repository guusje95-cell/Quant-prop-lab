"""Hub agenda item 'event_short_vol_regime' (FLAGGED post hoc: the effect was seen in the Gen473 regime table).
Hypothesis: new-coin short squeezes are more violent when the whole market is volatile, so the event short earns less per unit of
risk then; halving it when BTC's 30-day volatility (known before the day) is above its trailing-365-day median should raise the
book's Sharpe. Decision rule (pre-registered in research/hub/agenda.json): book +0.05 and no period lower than v9.8.
Writes results/hub_research/event_regime_scaling.json."""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = "2026-09-30"
H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:END + " 23:00"]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
btc = B.k5("BTC").close.resample("1D").last(); vol = btc.pct_change().rolling(30).std()
hi = (vol > vol.rolling(365, min_periods=180).median()).shift(1).fillna(False)       # decided with data up to the previous day
scale = hi.map({True: 0.5, False: 1.0}).reindex(H.index.floor("D")).set_axis(H.index).fillna(1.0)
b0 = unit(CS.portfolio_v5(H)[0]); H1 = H.copy(); H1["listing short"] = H["listing short"] * scale; b1 = unit(CS.portfolio_v5(H1)[0])
ref, new = [shp(b0), per(b0)], [shp(b1), per(b1)]
out = {"reference_v98": ref, "candidate": new, "share_of_days_scaled": round(float(hi.loc["2022":END].mean()), 3),
       "pass": bool(new[0] >= ref[0] + 0.05 and all(new[1][i] >= ref[1][i] for i in range(3))), "flag": "post hoc (regime effect seen in Gen473)"}
OUTD = Path(os.environ.get("QPL_AGENT_OUT", ROOT / "results/hub_research")); OUTD.mkdir(parents=True, exist_ok=True)   # hub agent: hub_data/agent_results
(OUTD / "event_regime_scaling.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
