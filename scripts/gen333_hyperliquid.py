"""Gen333 (config/gen333_protocol.json): v8.6 on Hyperliquid for Propr - coin-list and leverage scenarios. Also saves the
platform P&L series used by Gen332 (results/gen333_series.parquet). Writes results/gen333.json."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen327_bybit_reality.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("tgtB = net.copy()")], str(_p), "exec"))      # net, r, fund, fund_by, cost, ev_pnl, U, sharpe(), ACCT
from qpl.lab import propfirms as PF
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
MAJ = ["BTC", "ETH"]; UNVER = ["ALGO", "CHZ", "EGLD", "ENJ", "IOTA", "KSM", "THETA", "XTZ", "ZIL"]
CORE = ["AAVE", "ADA", "ATOM", "AVAX", "BCH", "BNB", "BTC", "DOGE", "DOT", "ETC", "ETH", "FIL", "LINK", "LTC", "NEAR", "SOL", "TRX", "UNI", "XLM", "XRP"]
half = cost - 5.5


def sim(T, fin_h, cost_bp, band_usd=1000.0, risk=2.0):
    usd = ACCT * risk; A = T.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1]); b = band_usd / usd
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b; ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    E = pd.DataFrame(E, index=T.index, columns=T.columns); dE = E.diff().fillna(E)
    return (E * r.reindex(E.index)).sum(axis=1) - (E * fin_h.reindex(E.index)).sum(axis=1) - (dE.abs() * cost_bp).sum(axis=1) / 1e4 + ev_pnl


def capped(T, alt_lev, risk=1.5):
    m = (T[MAJ].abs().sum(axis=1) / 5 + T.drop(columns=MAJ).abs().sum(axis=1) / alt_lev) * risk
    return T.mul((0.9 / m).clip(upper=1.0).fillna(1.0), axis=0), float((m > 0.9).mean())


out = {}; S = {"Bybit": sim(net, fund_by, cost)}
for nm, drop in (("H1 all 60", []), ("H2 51 coins", UNVER), ("H3 core 20", [c for c in U if c not in CORE])):
    T = net.copy(); T[drop] = 0.0
    for lev in (2, 3):
        Tc, bind = capped(T, lev); p = sim(Tc, fund, 4.5 + half)
        k = f"{nm}, altcoin cap {lev}x"; S[k] = p
        out[k] = {"sharpe D/T/H": sharpe(p), "hours the cap binds at risk 1.5": round(bind, 4),
                  "annual return 15%-vol units": round(float(p.mean() * 24 * 365), 3)}
        print(k, out[k], flush=True)
pd.DataFrame(S).to_parquet(ROOT / "results/gen333_series.parquet")

HY = PF.PRESETS["HyroTrader Two-Step $200k"]
PROPR = replace(HY, name="Propr 2-Step 100k", account=100000, fee=749.0, targets=(0.05, 0.10), daily_loss=0.05, max_loss=0.08,
                max_type="trailing_lock", trailing_intraday=True, min_days=0, split=0.90, payout_min=0)


def scaled(p, haircut):
    d = p.groupby(p.index.floor("D")).sum(); p = p - haircut * d.std() / np.sqrt(365) / 24
    dd = p.loc[:"2024-12-31 23:00"]; dd = dd.groupby(dd.index.floor("D")).sum()
    return p * 0.15 / (dd.std() * np.sqrt(365))


for k in [k for k in S if k != "Bybit" and "2x" in k]:
    for lvl, hc in (("realistic", 0.0), ("planning", 1.25)):
        x = scaled(S[k], hc).loc["2025-01-01":"2026-09-30 23:00"]
        pb = PF.pipeline(to_daily_stop(x * 1.0, 0.6 * 0.05), PROPR, 5, 2, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.6 * 0.05),
                         horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
        out[k][f"Propr 2 x $100k, 2025-26, {lvl}"] = {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3),
                                                      "days_to_funded": pb["days_to_funded_median"]}
        print(k, lvl, out[k][f"Propr 2 x $100k, 2025-26, {lvl}"], flush=True)
json.dump(out, open(ROOT / "results/gen333.json", "w"), indent=1, default=float)
