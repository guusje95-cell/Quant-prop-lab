"""Gen93 robustness checks for M1 stablecoin mint spike (descriptive; no selection). Writes results/gen93_check.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen92_capit.py")}
exec(open(ROOT / "scripts/gen92_capit.py").read().split("# L1 DVOL spike")[0], g)
B, CFD, fhp, d2h, IDX, dsh, hold_w, P = (g[k] for k in ("B", "CFD", "fhp", "d2h", "IDX", "dsh", "hold_w", "P"))
from qpl.lab.data import stablecoin_caps
caps = stablecoin_caps(); caps = caps.where(caps > 0); caps.index = pd.DatetimeIndex(caps.index).normalize()
raw = caps / caps.shift(1) - 1
print("largest daily growth days:\n", raw.loc["2019":].sort_values().tail(8).round(4), flush=True)
print("signal days per year:", (raw.loc["2020":] > 0.005).groupby(raw.loc["2020":].index.year).sum().to_dict(), flush=True)


def run(th=0.005, hold=3, lag=2, coins=("BTC", "ETH"), cost=5.0, cap_jump=None):
    gr = raw.copy()
    if cap_jump:
        gr = gr.where(gr < cap_jump, np.nan)
    gr = gr.shift(lag).reindex(P.index)
    w = pd.DataFrame(0.0, index=P.index, columns=CFD)
    for c in coins:
        w[c] = hold_w(gr > th, hold=hold).to_numpy()
    w.loc["2026-05-25":] = 0.0
    if cost != 5.0:
        g["g"]["ns"]["SPREAD"].update({"BTC": cost, "ETH": cost})
    h = fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0)
    g["g"]["ns"]["SPREAD"].update({"BTC": 5.0, "ETH": 5.0})
    return h


rows = []
for nm, kw in (("base 0.5% hold 3 lag 2", {}), ("th 0.3%", {"th": 0.003}), ("th 0.75%", {"th": 0.0075}), ("th 1.0%", {"th": 0.01}),
               ("hold 2", {"hold": 2}), ("hold 5", {"hold": 5}), ("lag 3 days", {"lag": 3}), ("lag 4 days", {"lag": 4}),
               ("BTC only", {"coins": ("BTC",)}), ("ETH only", {"coins": ("ETH",)}), ("2x spread", {"cost": 10.0}),
               ("drop days with jump > 3% (data breaks)", {"cap_jump": 0.03})):
    h = run(**kw)
    rows.append({"variant": nm, "DEV": dsh(h, "2020-01-01", "2022-12-31"), "TEST": dsh(h, "2023-01-01", "2024-12-31"), "HOLD": dsh(h, "2025-01-01", "2026-05-24"),
                 "2020-26": dsh(h, "2020-01-01", "2026-05-24")})
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
# always-long benchmark: same exposure share, random? -> compare with buy-and-hold BTC/ETH at the same average exposure
h = run(); d = h.groupby(h.index.floor("D")).sum().loc["2020":"2026-05-24"]
w = pd.DataFrame(0.0, index=P.index, columns=CFD); w[["BTC", "ETH"]] = 0.5
bh = fhp(d2h(w), 3.3).reindex(IDX).fillna(0.0)
rows.append({"variant": "reference: always long BTC/ETH 0.5 each", "DEV": dsh(bh, "2020-01-01", "2022-12-31"), "TEST": dsh(bh, "2023-01-01", "2024-12-31"),
             "HOLD": dsh(bh, "2025-01-01", "2026-05-24"), "2020-26": dsh(bh, "2020-01-01", "2026-05-24")}); print(rows[-1], flush=True)
act = d != 0; print("share of days in market", round(act.mean(), 3), flush=True)
# compare with random entry days at the same frequency (500 draws) -> where does M1 rank?
rng = np.random.default_rng(1); sigdays = int((raw.shift(2).reindex(P.index) > 0.005).loc["2020":"2026-05-24"].sum())
base_sh = dsh(h, "2020-01-01", "2026-05-24"); sims = []
days = P.loc["2020":"2026-05-24"].index
for _ in range(300):
    s = pd.Series(False, index=P.index); s.loc[rng.choice(days, sigdays, replace=False)] = True
    ww = pd.DataFrame(0.0, index=P.index, columns=CFD)
    for c in ("BTC", "ETH"):
        ww[c] = hold_w(s, hold=3).to_numpy()
    sims.append(dsh(fhp(d2h(ww), 3.3).reindex(IDX).fillna(0.0), "2020-01-01", "2026-05-24"))
sims = np.array(sims); print("random-entry Sharpe: mean", round(sims.mean(), 2), "95th pct", round(np.percentile(sims, 95), 2), "M1", round(base_sh, 2),
                             "p-value", round((sims >= base_sh).mean(), 3), flush=True)
rows.append({"variant": "random entry days, same count (300 draws)", "2020-26": float(sims.mean()), "p95": float(np.percentile(sims, 95)), "p-value": float((sims >= base_sh).mean())})
pd.DataFrame(rows).to_csv(ROOT / "results/gen93_check.csv", index=False)
