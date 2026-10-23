"""Gen330 (config/gen330_protocol.json): v8.6 per prop firm with each firm's platform (costs, financing, coins, leverage) and its
published rules; per-firm risk and daily stop chosen on 2022-24, judged on 2025-26. Writes results/gen330.json."""
import itertools
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen327_bybit_reality.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("tgtB = net.copy()")], str(_p), "exec"))      # net, r, fund, fund_by, cost, ev_pnl, ev_pos, U, sharpe(), ACCT
import cfd_book as CB
from qpl.lab import propfirms as PF
assert HAVE
MAJ = ["BTC", "ETH"]


def sim(T, fin_h, cost_bp, band_usd=1000.0, risk=2.0):
    usd = ACCT * risk; A = T.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1]); b = band_usd / usd
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b; ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    E = pd.DataFrame(E, index=T.index, columns=T.columns); dE = E.diff().fillna(E)
    return (E * r.reindex(E.index)).sum(axis=1) - (E * fin_h.reindex(E.index)).sum(axis=1) - (dE.abs() * cost_bp).sum(axis=1) / 1e4 + ev_pnl


half_spread = cost - 5.5
zero = fund_by * 0.0
out = {"platform Sharpe D/T/H (2022-26 / 2022 / 2023-24 / 2025-26)": {}}
S = {}
S["Bybit"] = sim(net, fund_by, cost)
for sw in (0.0, 0.10, 0.20):                                                 # CFD: no funding; swap charged on |notional| both sides
    sw_h = net.abs() * 0.0 + sw / (365 * 24)
    fin = np.sign(net) * sw_h                                                # long pays +, short pays: P&L - E*fin -> use |E|
    p = sim(net, zero, 3.25 + half_spread) - (net.abs() * sw / (365 * 24)).sum(axis=1)
    S[f"CFT CFD all 60, swap {sw:.0%}"] = p
    Tb = net.copy(); Tb[[c for c in U if c not in CB.CARRY_CFD]] = 0.0
    S[f"CFT CFD 35 coins, swap {sw:.0%}"] = sim(Tb, zero, 3.25 + half_spread) - (Tb.abs() * sw / (365 * 24)).sum(axis=1)
# Hyperliquid leverage cap: margin at risk 1.5 (the funded risk) <= 90% of equity
for rk in (1.0, 1.5, 2.0):
    m = (net[MAJ].abs().sum(axis=1) / 5 + net.drop(columns=MAJ).abs().sum(axis=1) / 2) * rk
    out[f"Hyperliquid margin use at risk {rk}: median / p99 / share of hours > 90%"] = [round(float(m.median()), 2), round(float(m.quantile(0.99)), 2), round(float((m > 0.9).mean()), 4)]
m15 = (net[MAJ].abs().sum(axis=1) / 5 + net.drop(columns=MAJ).abs().sum(axis=1) / 2) * 1.5
S["Propr Hyperliquid (cap at risk 1.5)"] = sim(net.mul((0.9 / m15).clip(upper=1.0), axis=0), fund, 4.5 + half_spread)
for k, p in S.items():
    out["platform Sharpe D/T/H (2022-26 / 2022 / 2023-24 / 2025-26)"][k] = sharpe(p); print(k, sharpe(p), flush=True)

src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
CFT = replace(PF.PRESETS["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))
PROPR = replace(HY, name="Propr 2-Step 100k", account=100000, fee=749.0, targets=(0.05, 0.10), daily_loss=0.05, max_loss=0.08,
                max_type="trailing_lock", trailing_intraday=True, min_days=0, split=0.90, payout_min=0)
MFP = replace(HY, name="MFP Signature 100k", account=100000, fee=696.0, targets=(0.10,), daily_loss=0.03, max_loss=0.06, max_type="static",
              min_days=0, payout_min=0)
FIRMS = {"HyroTrader 2-Step $200k (Bybit)": (HY, "Bybit", 1, 0), "CFT 2-Phase $200k (Bybit route)": (CFT, "Bybit", 1, 0),
         "CFT 2-Phase $200k (MT5 CFDs, 35 coins, swap 10%)": (CFT, "CFT CFD 35 coins, swap 10%", 1, 0),
         "Propr 2-Step 2 x $100k (Hyperliquid)": (PROPR, "Propr Hyperliquid (cap at risk 1.5)", 2, 0),
         "MyFundedPerps Signature 2 x $100k": (MFP, "Bybit", 2, 4)}
G = list(itertools.product((1.0, 1.5, 2.0, 2.5), (1.0, 1.5, 2.0), (0.4, 0.5, 0.6, 0.75)))
DEFL = 3.027 - 1.78


def scaled(p, haircut):
    d = p.groupby(p.index.floor("D")).sum(); p = p - haircut * d.std() / np.sqrt(365) / 24
    dd = p.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    return p * 0.15 / (dd.std() * np.sqrt(365))


def run(h, f, n, reset, sc, sf, st, a, z):
    x = h.loc[a:z]; x.index = x.index - pd.Timedelta(hours=reset)
    pb = PF.pipeline(to_daily_stop(x * sc, st * f.daily_loss), f, 5, n, 1.0, 1.0, daily_fd=to_daily_stop(x * sf, st * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=300, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "P_funded": round(pb["P_funded"], 3),
            "days_to_funded": pb["days_to_funded_median"], "challenges": round(pb["bought"], 2)}


for lvl, hc in (("realistic (platform Sharpe)", 0.0), ("planning (minus 1.25 Sharpe)", DEFL)):
    out[lvl] = {}
    for fn, (f, plat, n, reset) in FIRMS.items():
        h = scaled(S[plat], hc)
        rows = [{"sc": sc, "sf": sf, "st": st, **run(h, f, n, reset, sc, sf, st, "2022-01-01", "2024-12-31 23:00")} for sc, sf, st in G]
        T = pd.DataFrame(rows); ok = T[T.P_profit >= 0.9]; c = (ok if len(ok) else T).sort_values("net", ascending=False).iloc[0]
        base = T[(T.sc == 2.0) & (T.sf == 1.5) & (T.st == 0.5)].iloc[0]
        res = {"chosen (challenge risk, funded risk, stop fraction)": [float(c.sc), float(c.sf), float(c.st)],
               "2025-26 chosen": run(h, f, n, reset, float(c.sc), float(c.sf), float(c.st), "2025-01-01", "2026-09-30 23:00"),
               "2025-26 default 2.0 / 1.5 / 0.5": run(h, f, n, reset, 2.0, 1.5, 0.5, "2025-01-01", "2026-09-30 23:00"),
               "2022-24 chosen vs default net": [int(c.net), int(base.net)]}
        out[lvl][fn] = res; print(lvl, fn, res, flush=True)
json.dump(out, open(ROOT / "results/gen330.json", "w"), indent=1, default=float)
