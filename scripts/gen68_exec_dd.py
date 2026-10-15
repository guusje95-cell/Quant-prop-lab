"""Gen68 (config/gen68_protocol.json). Writes results/gen68_*.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import gen52_optimize as G
from qpl.lab import binance_pack as B, strategies as S

sh = lambda x, a, b: x.loc[a:b].mean() / x.loc[a:b].std() * np.sqrt(365)
day = lambda h: h.groupby(h.index.floor("D")).sum()

# ---------------- L1 fill realism
rows = []
for nm, kw in (("touch (v2 as adopted)", {"limit": 0.005}), ("trade-through 0.1%", {"limit": 0.005, "through": 0.001}),
               ("trade-through 0.3%", {"limit": 0.005, "through": 0.003}), ("market entry (v1)", {})):
    x = day(CS.cascade(**kw)).loc["2021-12-01":"2026-09-30"]
    rows.append({"cascade entry": nm, "2022": sh(x, "2022", "2022"), "2023-24": sh(x, "2023", "2024"), "2025-26": sh(x, "2025", "2026"), "2023+": sh(x, "2023", "2026"),
                 "active_days": int((x != 0).sum())})
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen68_fill_realism.csv", index=False)

# ---------------- L2 maker rebalancing for C* and premium carry
def maker_effect(w_daily, coins, taker_bps):
    k1 = {c: B.k5(c) for c in coins}
    h = {c: pd.DataFrame({"lo": k1[c].low.resample("1h").min(), "hi": k1[c].high.resample("1h").max(), "c": k1[c].close.resample("1h").last()}) for c in coins}
    P = B.panel("close", "1D", coins).loc[:"2026-09-30"]; idx = P.index[P.index >= "2020-01-02"]
    R = P.pct_change(fill_method=None).reindex(idx); F = B.funding_panel(coins); F.index = (F.index - pd.Timedelta(seconds=1)).floor("D")
    FD = F.groupby(level=0).sum().reindex(idx)
    held = w_daily.reindex(idx).fillna(0.0).shift(1).fillna(0.0); dw = held.diff().fillna(0.0)
    base = (held * R.fillna(0) - held * FD.fillna(0)).sum(axis=1) - dw.abs().sum(axis=1) * taker_bps / 1e4
    adj = pd.Series(0.0, index=idx); filled = tot = 0
    for c in coins:
        hc = h[c]; p0 = P[c].shift(1).reindex(idx)                         # price at 00:00 of day d (close of d-1)
        lo = hc.lo.reindex(idx); hi = hc.hi.reindex(idx); p1 = hc.c.reindex(idx)   # first hour of day d
        d_ = dw[c]; trade = d_ != 0
        fill = ((d_ > 0) & (lo <= p0 * 0.9995)) | ((d_ < 0) & (hi >= p0 * 1.0005))
        cost_m = d_.abs() * 2 / 1e4
        late = -d_ * (p1 / p0 - 1) - d_.abs() * taker_bps / 1e4             # done at 01:00 instead of 00:00
        new_cost = np.where(fill, -cost_m, late)
        adj += (pd.Series(new_cost, index=idx).where(trade, 0.0).fillna(0.0) + (d_.abs() * taker_bps / 1e4).where(trade, 0.0))
        filled += int((fill & trade).sum()); tot += int(trade.sum())
    return base, base + adj, filled / max(tot, 1)


cs = S.CStarTrend(); W, _ = G.backtest(cs.signal(G.CR, {**cs.defaults(), "btc_leads": True}), 30, 0.0)
rows2 = []
b, m, fr = maker_effect(W[B.MAJ10], B.MAJ10, 7.5)
for nm, x in (("C* taker (7.5 bp)", b), ("C* maker at 00:00, else 01:00", m)):
    rows2.append({"test": nm, "DEV": sh(x, "2020", "2022"), "2023+": sh(x, "2023", "2026"), "fill_rate": fr}); print(rows2[-1], flush=True)
C = B.coins(); P = B.panel("close", "1D", C)
prem = pd.DataFrame({c: B.premium(c)["close"].resample("1D").mean() for c in C}).reindex(P.index).rolling(7).mean()
listed = P.notna().cumsum() >= 60; rk = (-prem).where(listed).rank(axis=1, pct=True)
w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
w = w.fillna(0.0).where(pd.Series(np.arange(len(w)) % 7 == 0, index=w.index), np.nan).ffill().fillna(0.0)
b, m, fr = maker_effect(w, C, 5)
for nm, x in (("premium carry taker (5 bp)", b), ("premium carry maker at 00:00, else 01:00", m)):
    rows2.append({"test": nm, "DEV": sh(x, "2020", "2022"), "2023+": sh(x, "2023", "2026"), "fill_rate": fr}); print(rows2[-1], flush=True)
pd.DataFrame(rows2).to_csv(ROOT / "results/gen68_maker_rebalance.csv", index=False)

# ---------------- D1 / D2 drawdowns
Hs = CS.all_sleeves(); D = day(Hs)[["C*", "premium carry", "cascade limit"]].loc["2022-01-01":"2026-09-30"]
Z = D / (D.std() * np.sqrt(365)) * 0.10
port = Z.mean(axis=1); k = 0.15 / (port.std() * np.sqrt(365)); port = port * k; Zc = Z / 3 * k
eq = (1 + port).cumprod(); dd = eq / eq.cummax() - 1
eps = []; d2 = dd.copy()
for _ in range(5):
    tr = d2.idxmin(); pk = eq.loc[:tr].idxmax(); eps.append((pk, tr, dd[tr])); d2.loc[pk:tr] = 0
    rec = eq.loc[tr:]; after = rec[rec >= eq[pk]]
    if len(after):
        d2.loc[tr:after.index[0]] = 0
att = [{"peak": a.date(), "trough": b_.date(), "drawdown": v, **{c: Zc[c].loc[a:b_].sum() for c in Zc}} for a, b_, v in eps]
pd.DataFrame(att).to_csv(ROOT / "results/gen68_dd_attribution.csv", index=False); print(pd.DataFrame(att).round(3).to_string())

def summary(x, name):
    eq_ = (1 + x).cumprod(); m = (1 + x).resample("ME").prod() - 1
    rng = np.random.default_rng(3); a = x.to_numpy(); yrs = []
    for _ in range(2000):
        ii = []
        while len(ii) < 365:
            s0 = rng.integers(len(a)); ii.extend(range(s0, min(s0 + 20, len(a))))
        yrs.append(np.prod(1 + a[np.array(ii[:365])]) - 1)
    return {"variant": name, "Sharpe": sh(x, "2022", "2026"), "MaxDD": (eq_ / eq_.cummax() - 1).min(), "pos_months": (m > 0).mean(),
            "boot_p5_year": np.percentile(yrs, 5), "boot_P_loss_year": float(np.mean(np.array(yrs) < 0))}

res = [summary(port, "v2 equal risk (baseline)")]
pv = port.rolling(30).std().shift(1) * np.sqrt(365); vt = port * (0.15 / pv).clip(upper=1.5).fillna(1.0)
vt = vt * port.std() / vt.std(); res.append(summary(vt, "portfolio vol targeting 30d"))
br = pd.DataFrame(index=Z.index)
for c in Z:
    e = (1 + Z[c]).cumprod(); ddc = e / e.cummax() - 1; state = False; mult = []
    for v in ddc:
        if not state and v < -0.10:
            state = True
        elif state and v > -0.05:
            state = False
        mult.append(0.5 if state else 1.0)
    br[c] = Z[c] * pd.Series(mult, index=Z.index).shift(1).fillna(1.0)
pb = br.mean(axis=1); pb = pb * port.std() / pb.std(); res.append(summary(pb, "sleeve drawdown brake"))
out = pd.DataFrame(res); out.to_csv(ROOT / "results/gen68_dd_controls.csv", index=False); print(out.round(3).to_string())
