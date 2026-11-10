"""H4 (protocol research/v99/h4_protocol.json): account risk on the 5-minute path with the hybrid stop. Writes results/v99/h4_risk_5min.json."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/v99"))
import stop1_design as S1  # noqa: E402

CACHE = ROOT / "data/lab"; CACHE.mkdir(parents=True, exist_ok=True)


def p5(name):
    f = CACHE / f"p5_{name}.parquet"
    if f.exists():
        return pd.read_parquet(f)["r"]
    if name == "hyro":
        g = S1.run("cn1_crypto_netting.py", "book = ph.loc"); scale = json.loads((ROOT / "config/paper_v98.json").read_text())["frozen"]["v98_scale"]
        x = S1.path5(pd.read_parquet(ROOT / "results/v99/v99e_series.parquet")["v9.9e"], g["net"] * scale)
    else:
        g = S1.run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
        x = S1.path5(pd.read_parquet(ROOT / "results/v99/bf28_series.parquet")["bf2.8"], g["net"].reindex(columns=g["coins"]).fillna(0.0))
    x.to_frame("r").to_parquet(f); return x


out = {}
for name, preset, levels in (("hyro", "HyroTrader Two-Step $200k", (1.9, 1.6)), ("bf", "BrightFunded Two-Step Classic $200k", (1.45, 1.15))):
    x = p5(name); res = {}
    for sr in levels:
        u = S1.to_sharpe(x, sr, 288)
        res[f"Sharpe {sr}"] = {str(r): S1.sim(u, preset, r, sr, 0.5, S1.hybrid) for r in (1.0, 1.25, 1.5, 1.75, 2.0)}
    out[preset] = res; (ROOT / "results/v99/h4_risk_5min.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
