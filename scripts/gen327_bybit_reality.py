"""Gen327 (config/gen327_protocol.json): v8.6 under Bybit conditions, on the Gen323 net-position reconstruction (every coin netted;
cascade and Weiss as their own orders).
  A  Gen323 baseline (Binance funding, flat 5 bp)                         = 3.158 in Gen323
  B  coins Bybit does not list: positions removed
  C  B + Bybit funding (Binance funding where Bybit has no history yet)
  D  C + per-coin cost = 5.5 bp taker + half the measured Bybit spread
  E  D with the $1,000 no-trade band (the planned execution)
Without research_data/bybit it runs a code check with Binance funding / 5 bp everywhere (A..D must all equal 3.158).
Writes results/gen327.json (results/gen327_codecheck.json without the Bybit data)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
_p = Path(__file__).resolve().parent / "gen323_execution.py"; _s = _p.read_text()
exec(compile(_s[:_s.index("base, pnl0, E0 = run(net)")], str(_p), "exec"))      # net, r, fund, ev_pnl, U, idx, sharpe(), ACCT, RISK
BY = ROOT / "research_data/bybit"; HAVE = (BY / "instruments.csv").exists()


def sim(target, fund_h, cost_bp, band_usd=0.0):
    usd = ACCT * RISK; A = target.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1]); b = band_usd / usd
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b if b > 0 else np.ones(A.shape[1], bool)
        ch |= (A[i] == 0) & (cur != 0); cur = np.where(ch, A[i], cur); E[i] = cur
    E = pd.DataFrame(E, index=target.index, columns=target.columns); dE = E.diff().fillna(E)
    pnl = (E * r.reindex(E.index)).sum(axis=1) - (E * fund_h.reindex(E.index)).sum(axis=1) - (dE.abs() * cost_bp).sum(axis=1) / 1e4 + ev_pnl
    trades = (dE.abs() * usd > 1.0); per_day = trades.groupby(trades.index.floor("D")).sum().sum(axis=1)
    return {"sharpe D/T/H": sharpe(pnl), "orders per day": round(float(per_day.mean()), 1)}


out = {"Bybit data": HAVE}
flat = pd.Series(5.0, index=U)
if HAVE:
    I = pd.read_csv(BY / "instruments.csv"); I = I[I.coin.isin(U)]
    listed = set(I.loc[I.listed.astype(bool), "coin"]); sym = dict(zip(I.coin, I.symbol))
    out["coins not on Bybit"] = sorted(set(U) - listed)
    S = pd.read_csv(BY / "spreads.csv").set_index("symbol")["spread_bp_median"]
    cost = pd.Series({c: 5.5 + 0.5 * float(S.get(sym.get(c, ""), np.nan)) if c in listed else 5.0 for c in U}).fillna(5.5 + 0.5 * float(S.median()))
    fb = {}
    for c in listed:
        f = BY / "funding" / f"{sym[c]}.parquet"
        if f.exists():
            x = pd.read_parquet(f)["funding_rate"]; x.index = pd.DatetimeIndex(x.index) - pd.Timedelta(hours=1)
            fb[c] = x.groupby(level=0).sum()
    FB = pd.DataFrame(fb).reindex(fund.index)
    first = {c: (FB[c].first_valid_index() if c in FB else None) for c in U}
    fund_by = fund.copy()
    for c in FB.columns:
        st = first[c]
        if st is not None:
            fund_by.loc[st:, c] = FB.loc[st:, c].fillna(0.0)
    out["Bybit funding history starts (median)"] = str(pd.Series([v for v in first.values() if v is not None]).median())
    out["mean annual funding Binance vs Bybit (sum over coins, %)"] = [round(float(fund.loc["2022":].sum().mean() / 4.75 * 100), 2), round(float(fund_by.loc["2022":].sum().mean() / 4.75 * 100), 2)]
    out["median cost per side bp (Bybit)"] = round(float(cost.median()), 2)
else:
    listed, fund_by, cost = set(U), fund, flat
tgtB = net.copy(); tgtB[[c for c in U if c not in listed]] = 0.0
for nm, args in (("A Gen323 baseline", (net, fund, flat)), ("B only Bybit-listed coins", (tgtB, fund, flat)),
                 ("C + Bybit funding", (tgtB, fund_by, flat)), ("D + Bybit costs (5.5 bp + half spread)", (tgtB, fund_by, cost)),
                 ("E = D with the $1,000 band", (tgtB, fund_by, cost, 1000.0))):
    out[nm] = sim(*args); print(nm, out[nm], flush=True)
json.dump(out, open(ROOT / ("results/gen327.json" if HAVE else "results/gen327_codecheck.json"), "w"), indent=1, default=str)
