"""C1 live selftest: the cfd_extra sleeves computed with only the data known at a cutoff (fresh process, QPL_CUTOFF / QPL_END set) must
equal the full-history run for the hours before that cutoff (no look-ahead). Writes results/v99/c1_selftest.json."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
CUTS = ["2026-09-10 00:00", "2026-09-17 13:00", "2026-09-25 08:00", "2026-09-30 00:00"]
CHILD = """
import sys, pandas as pd
from qpl.live import cfd_extra as X
cut = pd.Timestamp(sys.argv[1]); S = X.sleeves(pd.date_range('2021-01-01', cut - pd.Timedelta(hours=1), freq='h'))
pd.DataFrame(S).loc[cut - pd.Timedelta(hours=48):].to_parquet(sys.argv[2])
"""


def main():
    tmp = ROOT / "results/v99/_c1_selftest"; tmp.mkdir(exist_ok=True); out = {}
    full = tmp / "full.parquet"
    for c in CUTS:
        f = tmp / f"{c[:10]}_{c[11:13]}.parquet"
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), QPL_CUTOFF=c, QPL_END=str(pd.Timestamp(c) - pd.Timedelta(hours=1)))
        env.pop("QPL_LIVE_PACK", None)
        subprocess.run([sys.executable, "-c", CHILD, c, str(f)], env=env, check=True, cwd=ROOT)
        out[c] = {"hours": len(pd.read_parquet(f))}
    # compare each cutoff run with one run on the full history (no cutoff)
    subprocess.run([sys.executable, "-c", CHILD.replace(".loc[cut - pd.Timedelta(hours=48):]", ""), "2026-09-30 12:00", str(full)],
                   env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), check=True, cwd=ROOT)
    F = pd.read_parquet(full); mx = 0.0
    for c in CUTS:
        P = pd.read_parquet(tmp / f"{c[:10]}_{c[11:13]}.parquet"); d = (P - F.reindex(P.index)).abs().max().max(); mx = max(mx, float(d))
        out[c]["max abs diff vs full history"] = float(d)
    out["PASSED"] = mx < 1e-12
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    (ROOT / "results/v99/c1_selftest.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
