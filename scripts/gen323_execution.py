"""Gen323 (descriptive engineering study, config/gen323_protocol.json): v8.6 as NET positions per coin, hour by hour.
  1. HyroTrader rule checks: gross notional / initial balance (funded cap 2x), largest single-coin daily loss (3% per-trade cap),
     the evaluation's 40% best-day profit-distribution rule, and the 4% vs 5% daily-loss reading.
  2. Execution: orders per day and order sizes; netting, no-trade bands, dust filter and an exposure cap, each with its Sharpe cost.
Writes results/gen323.json."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
import ridge_live as RL
import alt_kimchi as AK
from qpl.lab import binance_pack as B, extra_pack as X
from qpl.lab import propfirms as PF
END = L.END; ROOT = L.ROOT
SCALE, RISK, ACCT = 0.902, 2.0, 200_000.0                                  # paper v86: scale, challenge risk, account

# ---- sleeve weights (as scripts/paper_v5.py compute() for v86) -------------------------------------------------------
U = CS._breadth_universe(); Hc = CS._breadth_close(U).loc["2020-01-01":END + " 23:00"]; r = Hc.pct_change(fill_method=None).fillna(0.0)
pk = [c for c in U if c in B.coins()]
fund = pd.concat([B.funding_panel(pk)] + [X.funding(c).rename(c) for c in U if c not in pk], axis=1).sort_index()[U]
fund.index = fund.index - pd.Timedelta(hours=1); fund = fund.groupby(level=0).sum().reindex(Hc.index).fillna(0.0)
daily = {"C*": CS.cstar_weights(), "premium carry": CS.premium_weights(invvol=True, tranched=True), "delev bounce": CS.delev_bounce_weights(),
         "ridge ML": RL.predictions(END, spot=True, kb=True, volscale=True, vrp=True, cal=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5,
         "alt kimchi": AK.weights(END + " 23:00"), "premium carry 60": CS.premium_breadth_weights(invvol=True, tranched=True)}
_, cpos = CS.cascade(limit=0.005, through=0.001, positions=True)
_, tpos = CS.trend4h(positions=True)
_, wpos = CS.weiss_expiry(positions=True)
intraday = {"cascade limit strict": cpos, "trend 4h": tpos, "Weiss expiry": wpos}

Hs = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0)
ph, W, mult = CS.portfolio_v5(Hs)
assert abs(L.sh(ph, "2022-01-01", END) - L.REF[0]) < 1e-9
idx = Hc.loc["2022-01-01":].index
Wh = W.reindex(idx.floor("D")).set_axis(idx); mh = mult.reindex(idx.floor("D")).set_axis(idx)
net = pd.DataFrame(0.0, index=idx, columns=U)
for s, w in daily.items():
    wd = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    held = wd.reindex(idx.floor("D")).set_axis(idx).reindex(columns=U).fillna(0.0)
    net = net + held.mul(Wh[s] * mh, axis=0)
for s, p in intraday.items():
    net = net + p.reindex(index=idx, columns=U).fillna(0.0).mul(Wh[s] * mh, axis=0)
net = net * SCALE                                                            # fraction of equity at risk 1.0 (15% vol book)
out = {"reference v8.6": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}


def sharpe(p):
    d = p.groupby(p.index.floor("D")).sum()
    f = lambda a, z: float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365))
    return [round(f("2022-01-01", END), 3), round(f("2022", "2022"), 3), round(f("2023", "2024"), 3), round(f("2025", END), 3)]


def run(target, band_usd=0.0, dust_usd=0.0, cap=None, cost_bp=5.0, risk=RISK):
    """Execute target positions hour by hour: dust filter, exposure cap, no-trade band (all in dollars at `risk` on $200k)."""
    usd = ACCT * risk
    T = target.copy()
    if cap is not None:
        g = T.abs().sum(axis=1) * risk; T = T.mul((cap / g).clip(upper=1.0).fillna(1.0), axis=0)
    if dust_usd > 0:
        T = T.where(T.abs() * usd >= dust_usd, 0.0)
    A = T.to_numpy(); E = np.zeros_like(A); cur = np.zeros(A.shape[1]); b = band_usd / usd
    for i in range(len(A)):
        ch = np.abs(A[i] - cur) >= b if b > 0 else np.ones(A.shape[1], bool)
        ch |= (A[i] == 0) & (cur != 0)                                       # a target of zero always closes
        cur = np.where(ch, A[i], cur); E[i] = cur
    E = pd.DataFrame(E, index=T.index, columns=T.columns)
    dE = E.diff().fillna(E)
    pnl = (E * r.reindex(E.index)).sum(axis=1) - (E * fund.reindex(E.index)).sum(axis=1) - dE.abs().sum(axis=1) * cost_bp / 1e4
    trades = (dE.abs() * usd > 1.0)
    per_day = trades.groupby(trades.index.floor("D")).sum().sum(axis=1)
    sizes = (dE.abs() * usd)[trades].stack()
    gross = E.abs().sum(axis=1) * risk
    return {"sharpe D/T/H": sharpe(pnl), "orders per day (mean)": round(float(per_day.mean()), 1), "orders per day (p90)": float(per_day.quantile(0.9)),
            "median order $": round(float(sizes.median())), "share of orders < $1k": round(float((sizes < 1000).mean()), 3),
            "gross / balance p50": round(float(gross.median()), 2), "gross p99": round(float(gross.quantile(0.99)), 2),
            "hours gross > 2.0": round(float((gross > 2.0).mean()), 4), "positions held (mean)": round(float((E.abs() > 0).sum(axis=1).mean()), 1)}, pnl, E


base, pnl0, E0 = run(net)
out["A netted, every change traded (5 bp)"] = base; print("A", base, flush=True)
for nm, kw in (("B band $500", dict(band_usd=500)), ("C band $1,000", dict(band_usd=1000)), ("D band $2,500", dict(band_usd=2500)),
               ("E band $1,000 + dust < $500 dropped", dict(band_usd=1000, dust_usd=500)),
               ("F band $1,000 + exposure cap 1.9x", dict(band_usd=1000, cap=1.9)),
               ("G band $1,000 + dust $500 + cap 1.9x", dict(band_usd=1000, dust_usd=500, cap=1.9)),
               ("H funded risk 2.0: band $1,000 + dust $500 + cap 1.9x", dict(band_usd=1000, dust_usd=500, cap=1.9, risk=2.0))):
    o, _, _ = run(net, **kw); out[nm] = o; print(nm, o, flush=True)

# ---- HyroTrader single-position loss (3% of the initial balance = $6,000) -----------------------------------------------
cp = (E0 * r.reindex(E0.index)) * ACCT * RISK
dl = cp.groupby(cp.index.floor("D")).sum()
out["worst single-coin daily loss $ (risk 2.0)"] = round(float(dl.min().min()))
out["coin-days with a loss > $6,000"] = int((dl < -6000).sum().sum())
out["coin-days with a loss > $4,000"] = int((dl < -4000).sum().sum())

# ---- 40% best-day rule in the evaluation and the 4% daily-loss reading (bootstrap, Gen318 method) -------------------------
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
h = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"]
for nm, f in (("daily loss 5% (modelled)", HY), ("daily loss 4%", replace(HY, daily_loss=0.04))):
    x = h.loc["2025-01-01":"2026-09-30 23:00"]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 2.0, 0.5 * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
    out["HyroTrader 2025-26, " + nm] = {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3)}
    print(nm, out["HyroTrader 2025-26, " + nm], flush=True)
d = (h * 2.0).groupby(h.index.floor("D")).sum().loc["2023-01-01":]            # historical challenge walks, one per start week
hits, viol, extra = 0, 0, []
for s in pd.date_range("2023-01-01", "2026-06-30", freq="7D"):
    x = d.loc[s:]; eq = (1 + x).cumprod() - 1
    for tgt in (0.10,):
        reach = eq[eq >= tgt]
        if len(reach) == 0:
            continue
        t = reach.index[0]; seg = x.loc[:t]; hits += 1
        if seg.max() > 0.4 * eq.loc[t]:
            viol += 1
            ok = [u for u in eq.loc[t:].index if x.loc[:u].max() <= 0.4 * eq.loc[u]]
            extra.append((ok[0] - t).days if ok else np.nan)
out["40% rule: phase-1 walks reaching +10%"] = hits
out["40% rule: of those, best day > 40% of profit at the target day"] = viol
out["40% rule: extra days until compliant (median)"] = float(np.nanmedian(extra)) if extra else 0.0
print(json.dumps(out, indent=1)); json.dump(out, open(ROOT / "results/gen323.json", "w"), indent=1)
