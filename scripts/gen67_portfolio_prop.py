"""Gen67: crypto-firm portfolio v2 (C* + premium carry + cascade with -0.5% limit entries), equal risk, 15% vol, hourly path
2022-01..2026-09; S50 daily stop vs none; historical and bootstrapped prop paths. Writes results/gen67_portfolio_prop.csv and
results/gen67_portfolio.png."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen55_firms as G55
from qpl.lab import propfirms as PF
g = {"__file__": "x", "__name__": "x"}
exec(compile((ROOT / "scripts/gen66_prop_tools.py").read_text().split("H = CS.all_sleeves()")[0] + "\n" +
             (ROOT / "scripts/gen66_prop_tools.py").read_text().split("def to_daily_stop")[1].join(["def to_daily_stop", ""]).split("FIRMS = [")[0], "g", "exec"), g) if False else None


def to_daily_stop(h, stop):
    rows = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            rows.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            rows.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")


Hall = CS.all_sleeves()
def build(cols):
    H = Hall[cols].loc["2021-12-01":]; D = H.groupby(H.index.floor("D")).sum()
    p = H.mul(pd.Series({c: 0.10 / (D[c].std() * np.sqrt(365)) for c in D})).mean(axis=1).loc["2022-01-01":"2026-09-30 23:00"]
    return p * 0.15 / (p.groupby(p.index.floor("D")).sum().std() * np.sqrt(365))


ports = {"v1 (cascade market entry)": build(["C*", "premium carry", "cascade"]), "v2 (cascade limit entry)": build(["C*", "premium carry", "cascade limit"])}
rows = []
for pn, port in ports.items():
    for key in ("HyroTrader One-Step $100k", "HyroTrader Two-Step $100k", "Crypto Fund Trader 1-Phase $100k", "SizeProp One-Step $100k"):
        f = PF.PRESETS[key]
        for stop in (0.0, 0.5):
            hc, hf = to_daily_stop(port, stop * f.daily_loss), to_daily_stop(port * 0.6, stop * f.daily_loss)
            a = PF.attempts(hc, f, 1.0)
            ph = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
            pb = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, method="bootstrap", n_boot=1000, block=20, seed=11)
            mi, am = G55.months_with_income(hc, hf, f)
            rows.append({"portfolio": pn, "firm": f.name, "daily_stop": "S50" if stop else "none", "pass": a["P_pass"], "fail_daily": a["P_fail_daily"],
                         "hist_net": ph["net_mean"], "hist_p10": ph["net_p10"], "boot_net": pb["net_mean"], "boot_p10": pb["net_p10"], "boot_p_profit": pb["P_profit"],
                         "months_with_income": mi, "avg_month": am})
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen67_portfolio_prop.csv", index=False)

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
c_star = build(["C*"])
for (n, s), col in zip(list(ports.items()) + [("C* alone", c_star)], ("#9db8e8", "#2a6fdb", "#e07b39")):
    x = s.groupby(s.index.floor("D")).sum(); eq = (1 + x).cumprod()
    ax[0].plot(eq.index, eq, color=col, lw=1.6, label=f"{n}  (Sharpe {x.mean() / x.std() * np.sqrt(365):.2f})")
    ax[1].plot(eq.index, eq / eq.cummax() - 1, color=col, lw=1)
ax[0].set_yscale("log"); ax[0].legend(frameon=False); ax[0].grid(alpha=.25); ax[0].set_ylabel("growth of 1 (log)")
ax[0].set_title("Crypto-firm portfolio, 15% volatility, 2022-01 to 2026-09 (descriptive)"); ax[1].grid(alpha=.25); ax[1].set_ylabel("drawdown")
fig.tight_layout(); fig.savefig(ROOT / "results/gen67_portfolio.png", dpi=130)
