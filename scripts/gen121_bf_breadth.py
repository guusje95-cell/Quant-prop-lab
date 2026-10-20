"""Gen121 (config/gen121_protocol.json): premium carry on all BrightFunded-listed coins in the bf CFD book. Writes results/gen121.json."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen80_112_breadth.py")}
exec(open(ROOT / "scripts/gen80_112_breadth.py").read().split("ref = book(")[0], g)
CS, per, sh, prem_w, HC = (g[k] for k in ("CS", "per", "sh", "prem_w", "HC"))
import cfd_book as CB
NEW = ["AAVE", "ATOM", "BNB", "ETC", "FIL", "NEAR", "TRX", "UNI", "XLM", "ALGO", "APT", "ARB", "COMP", "CRV", "DASH", "DYDX", "EGLD", "GRT", "HBAR",
       "ICP", "INJ", "LDO", "MANA", "NEO", "OP", "RUNE", "SAND", "SNX", "STX", "SUI", "XTZ"]
U = CB.CFD + NEW
R0, pos0, _ = CB.positions(); END = "2026-09-30 23:00"; R0 = R0.loc[:END]; IDX = R0.index
RU = HC[U].reindex(IDX).pct_change(fill_method=None).fillna(0.0)
RU[CB.CFD] = R0[CB.CFD]                                              # identical returns for the current coins
SPR = pd.Series({c: (0.4 if c == "BTC" else 2.7 if c == "ETH" else 10.0) for c in U})


def pnl(p, spread_mult=1.0):
    p = p.reindex(index=IDX, columns=U).fillna(0.0)
    turn = p.diff().abs().fillna(p.abs()).mul((SPR * spread_mult + CB.COMM) / 1e4, axis=1).sum(axis=1)
    return (p * RU).sum(axis=1) - turn


def book(pos, spread_mult=1.0):
    H = pd.DataFrame({s: pnl(pos[s], spread_mult) for s in CB.SLEEVES}).fillna(0.0)
    ph, W, m = CS.portfolio_v5(H); idx = ph.index
    Wh = W.reindex(idx.floor("D")).set_axis(idx); mh = m.reindex(idx.floor("D")).set_axis(idx)
    net = sum(pos[s].reindex(index=idx, columns=U).fillna(0.0) * Wh[s].to_numpy()[:, None] for s in CB.SLEEVES).mul(mh * 0.885, axis=0)
    capf = ((5 / 1.5) / net.abs().sum(axis=1)).clip(upper=1).fillna(1.0)
    return ph * capf, H


idx1 = IDX.append(pd.DatetimeIndex([IDX[-1] + pd.Timedelta(hours=1)]))
posU = {s: p.reindex(columns=U).fillna(0.0) for s, p in pos0.items()}
b0, H0 = book(posU)
wU = prem_w(U); wU = wU.reindex(columns=U).fillna(0.0)
pos1 = dict(posU); pos1["premium carry"] = CB.d2h.__wrapped__(wU, idx1) if hasattr(CB.d2h, "__wrapped__") else \
    wU.reindex(wU.index.append(pd.DatetimeIndex([wU.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(idx1.floor("D")).set_axis(idx1).fillna(0.0)
b1, H1 = book(pos1)
b2, H2 = book(pos1, 2.0); b02, H02 = book(posU, 2.0)
k0, k1 = per(b0, "2022-01-01"), per(b1, "2022-01-01")
s0, s1 = H0["premium carry"], H1["premium carry"]
out = {"current bf 2022-26": round(sh(b0, "2022-01-01", "2026-09-30"), 3), "breadth bf 2022-26": round(sh(b1, "2022-01-01", "2026-09-30"), 3),
       "current bf D/T/H": np.round(k0, 3).tolist(), "breadth bf D/T/H": np.round(k1, 3).tolist(),
       "sleeve current 2020/T/H": np.round(per(s0, "2020-01-01"), 3).tolist(), "sleeve breadth 2020/T/H": np.round(per(s1, "2020-01-01"), 3).tolist(),
       "sleeve current 2023-26": round(sh(s0, "2023-01-01", "2026-09-30"), 3), "sleeve breadth 2023-26": round(sh(s1, "2023-01-01", "2026-09-30"), 3),
       "2x spreads: bf current / breadth 2022-26": [round(sh(b02, "2022-01-01", "2026-09-30"), 3), round(sh(b2, "2022-01-01", "2026-09-30"), 3)],
       "2x spreads: breadth D/T/H": np.round(per(b2, "2022-01-01"), 3).tolist()}
out["pass"] = bool(out["sleeve breadth 2023-26"] >= out["sleeve current 2023-26"] and k1[2] >= k0[2] and per(s1, "2020-01-01")[2] >= per(s0, "2020-01-01")[2]
                   and out["breadth bf 2022-26"] > out["current bf 2022-26"] and k1[1] >= k0[1])
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen121.json", "w"), indent=1)
