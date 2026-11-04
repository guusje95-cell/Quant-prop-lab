"""Point-in-time selftest of dailyflat_targets.build (0 trials): for 6 sessions in 2026, targets built with data cut at 17:00 ET of
the previous day (+ placeholder bar) must equal the full-data positions x fbook weights x research level. Child process per cutoff.
Writes results/v99/dailyflat_targets_selftest.json."""
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("QPL_DF_SIGNALS", "true")                            # DF-1c: true-price signals
SESS = ["2026-03-17", "2026-05-29", "2026-06-30", "2026-08-03", "2026-09-11", "2026-09-30"]

if len(sys.argv) > 1 and sys.argv[1] == "child":
    sys.path.insert(0, str(ROOT / "scripts/v99")); import dailyflat_targets as DT
    s = pd.Timestamp(sys.argv[2]); prev = s - pd.Timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= pd.Timedelta(days=1)
    at = pd.Timestamp(prev + pd.Timedelta(hours=17)).tz_localize("America/New_York").tz_convert("UTC")
    sys.argv.append("--research"); print(json.dumps(DT.build(at, write=False)["targets_before_14et"])); sys.exit(0)

sys.path.insert(0, str(ROOT / "scripts/v99")); sys.argv.append("--research")
import dailyflat_positions as DP
pos = DP.session_positions(); EQ = DP.EQ8
Q = pd.read_parquet(ROOT / "results/v99/df1c_sleeves.parquet")[EQ]; Q = Q[Q.index.weekday < 5].loc["2010-06-01":"2026-09-30"].fillna(0.0)
T = Q.loc[:"2022-12-31"]; w = (1 / T.std()).where(T.mean() / T.std() > 0, 0.0); w = w / w.sum()
raw = (Q * w).sum(axis=1); lvl = (0.10 / (raw.rolling(60, min_periods=40).std() * np.sqrt(252))).clip(upper=3).shift(1)
out, worst = {}, 0.0
for s in SESS:
    d = pd.Timestamp(s); ref = {}
    for r, c in {"ES": "US500", "NQ": "US100", "RTY": "US2000", "YM": "US30"}.items():
        v = 0.0
        for n in EQ:
            P = pos["R1 until 14:00"] if n == "R1" else pos[n]
            if r in P and d in P.index:
                v += w[n] * lvl.loc[d] * float(P.loc[d, r])
        ref[c] = round(v, 6)
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    pr = subprocess.run([sys.executable, __file__, "child", s], capture_output=True, text=True, env=env, timeout=1500)
    live = json.loads(pr.stdout.strip().splitlines()[-1]) if pr.returncode == 0 else {"error": pr.stderr[-500:]}
    diff = max(abs(live.get(k, np.nan) - v) for k, v in ref.items()) if "error" not in live else float("nan")
    worst = max(worst, diff if np.isfinite(diff) else 9.0); out[s] = {"point-in-time": live, "full data": ref, "max abs diff": diff}
    print(s, out[s], flush=True)
out["PASS"] = bool(worst < 1e-4)
(ROOT / ("results/v99/dailyflat_targets_selftest_cfd1655.json" if os.environ.get("QPL_FLAT_FROM") == "17" else "results/v99/dailyflat_targets_selftest.json")).write_text(json.dumps(out, indent=1)); print("PASS", out["PASS"])
