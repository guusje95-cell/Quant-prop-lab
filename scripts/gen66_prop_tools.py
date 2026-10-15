"""Gen66 (config/gen66_protocol.json): prop risk tools on the crypto-firm portfolio. Writes results/gen66_prop_tools.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import propfirms as PF

H = CS.all_sleeves()[["C*", "premium carry", "cascade"]].loc["2021-12-01":]
D = H.groupby(H.index.floor("D")).sum()
port = H.mul(pd.Series({c: 0.10 / (D[c].std() * np.sqrt(365)) for c in D})).mean(axis=1).loc["2022-01-01":"2026-09-30 23:00"]
port = port * 0.15 / (port.groupby(port.index.floor("D")).sum().std() * np.sqrt(365))


def to_daily_stop(h, stop):
    rows = []
    for d, g in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + g.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


FIRMS = ["HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "Crypto Fund Trader 1-Phase $100k", "SizeProp One-Step $100k"]
TOOLS = {"baseline": (0.0, False), "S50": (0.5, False), "S75": (0.75, False), "CUSH": (0.0, True), "S75+CUSH": (0.75, True)}
rows = []
for key in FIRMS:
    f0 = PF.PRESETS[key]
    for tool, (sf, cush) in TOOLS.items():
        lim = f0.daily_loss
        hc, hf = to_daily_stop(port * 1.0, sf * lim), to_daily_stop(port * 0.6, sf * lim)
        f = PF.replace(f0, cushion_scale=cush)
        a = PF.attempts(hc, f, 1.0); p = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
        mi, am = G55.months_with_income(hc, hf, f)
        rows.append({"firm": f0.name, "tool": tool, "pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "net_2y": p["net_mean"], "net_2y_p10": p["net_p10"],
                     "p_profit": p["P_profit"], "months_with_income": mi})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
out = pd.DataFrame(rows); out.to_csv(ROOT / "results/gen66_prop_tools.csv", index=False)
