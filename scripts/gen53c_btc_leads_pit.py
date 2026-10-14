"""Gen53 robustness: H5 'BTC leads' on the point-in-time universes (Yahoo data)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import importlib.util
spec = importlib.util.spec_from_file_location("g53", ROOT / "scripts/gen53_research.py")
src = (ROOT / "scripts/gen53_research.py").read_text().split("# ---------------- base C* (Binance)")[0]   # only the H1 part
g = {"__file__": str(ROOT / "scripts/gen53_research.py"), "__name__": "g53"}; exec(compile(src, "gen53_h1", "exec"), g)
rows = []
for n in (10, 20):
    mem = g["members"](n)
    for tag, sg in (("C*", g["ysig"]), ("C* + BTC leads", g["ysig"].where(g["ysig"]["BTC"] > 0, 0.0, axis=0).assign(BTC=g["ysig"]["BTC"]))):
        w, d = g["scale15"](g["yb"], g["own_size"](g["yb"], sg, mem, n))
        rows.append(g["summ"](f"PIT top {n}: {tag}", d["net"]))
pd.DataFrame(rows).to_csv(ROOT / "results/gen53_btc_leads_pit.csv", index=False)
