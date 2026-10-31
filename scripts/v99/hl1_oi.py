"""v9.9 HL1 (research/v99/h2_protocol.json): Hyperliquid open-interest strategies on the hub's forward snapshots.
Writes results/v99/hl1_oi.json once >= 90 days of data exist; before that it only reports the data available."""
import glob
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
files = sorted(glob.glob(str(ROOT / "research_data/hyperliquid_live/*.csv")))
if not files:
    sys.exit("no Hyperliquid snapshots yet (hub job hl_snapshot; share research_data/hyperliquid_live)")
X = pd.concat(pd.read_csv(f) for f in files); X["ts"] = pd.to_datetime(X.ts_utc).dt.floor("h")
X = X.drop_duplicates(["ts", "coin"], keep="last")
days = (X.ts.max() - X.ts.min()).days
if days < 90 and "--force" not in sys.argv:
    print(json.dumps({"status": "waiting", "days of data": days, "needed": 90})); sys.exit(0)
P = X.pivot(index="ts", columns="coin", values="markPx").astype(float).sort_index()
OI = X.pivot(index="ts", columns="coin", values="openInterest").astype(float).sort_index()
FU = X.pivot(index="ts", columns="coin", values="funding").astype(float).sort_index()
by = set()
for f in (ROOT / "research_data/bybit_listings/instruments.json", ROOT / "paper_trading/v98/data/bybit_instruments.json"):
    if f.exists():
        by |= {x["symbol"][:-4] for x in json.loads(f.read_text()) if x["symbol"].endswith("USDT")}
cols = [c for c in P.columns if (c in by or f"1000{c}" in by or c.lstrip("k") in by) and P[c].notna().sum() >= 30 * 24]
P, OI, FU = P[cols], OI[cols], FU[cols]
Pd, OId = P.resample("1D").last(), OI.resample("1D").last(); R = Pd.pct_change().shift(-1)            # next-day return
fund_d = FU.resample("1D").sum().shift(-1)
def pnl(W, hold=1):
    W = W.fillna(0.0); Wh = W.rolling(hold, min_periods=1).mean()
    g = (Wh * R).sum(axis=1) - (Wh * fund_d).sum(axis=1) - Wh.diff().abs().sum(axis=1) * 6e-4
    return g.dropna()
ch7 = OId.pct_change(7); rk = ch7.rank(axis=1, pct=True)
WA = (rk <= 0.2).astype(float).div((rk <= 0.2).sum(axis=1), axis=0) - (rk > 0.8).astype(float).div((rk > 0.8).sum(axis=1), axis=0)
sig = (OId.pct_change(3) > 0.20) & (Pd.pct_change(3) < 0); WB = sig.astype(float).div(sig.sum(axis=1).replace(0, np.nan), axis=0)
paper = None
pf = ROOT / "paper_trading/v98/ledger_hourly.csv"
if pf.exists():
    L = pd.read_csv(pf); paper = pd.Series(L.port.astype(float).to_numpy(), index=pd.to_datetime(L.hour)).resample("1D").sum()
out = {"days of data": days, "coins": len(cols)}
for k, W, h in (("HL1-A crowding build-up fade", WA, 1), ("HL1-B squeeze setup", WB, 3)):
    g = pnl(W, h); sr = float(g.mean() / g.std() * np.sqrt(365)) if g.std() > 0 else None
    corr = float(g.corr(paper.reindex(g.index))) if paper is not None else None
    out[k] = {"days": len(g), "net Sharpe": round(sr, 2) if sr is not None else None, "corr with v9.8 paper": round(corr, 2) if corr is not None else None,
              "candidate": bool(sr is not None and sr >= 1.0 and (corr is None or corr < 0.3))}
(ROOT / "results/v99/hl1_oi.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
