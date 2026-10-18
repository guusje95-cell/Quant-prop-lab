"""Gen96 helper: dump the CFD-book signals computed with data cut at QPL_CUTOFF (run once per cutoff in a fresh process)."""
import os
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); tag = os.environ.get("QPL_CUTOFF", "full").replace(":", "").replace(" ", "_")
cw = CS.cstar_weights().copy(); a = cw.abs(); m = a.where(a > 0).mean(axis=1); cw = cw.where(a.ge(m * 0.5, axis=0), 0.0)
cw.to_parquet(out / f"cstar_{tag}.parquet")
CS.delev_bounce_weights().to_parquet(out / f"bounce_{tag}.parquet")
CS.weiss_expiry(positions=True)[1].to_parquet(out / f"weiss_{tag}.parquet")
print("dumped", tag, flush=True)
