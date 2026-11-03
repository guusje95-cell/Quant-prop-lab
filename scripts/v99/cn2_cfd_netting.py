"""CN-2 (execution, 0 alpha trials): net execution of the CFD book bf2.8 vs per-sleeve / per-member cost accounting (as CN-1 for crypto).
Crypto-CFD sleeves only (the index sleeve trades other instruments). Per-coin cost = half the measured BrightFunded spread + 1.2 bp
(cfd_book.measured_costs; coins outside its lists: cfd_extra.costs). Positions rebuilt from the sleeve code and checked against the
bf2.8 sleeve P&L. Writes results/v99/cn2_cfd_netting.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import alt_kimchi as AK
import c1_cfd_port as C
import c3_ensembles as E
import cfd_book as CB
import crypto_sleeves as CS
from qpl.live import cfd_extra as X

CB.measured_costs()
BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
R0 = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
b27 = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
H = b27.assign(**{"trend 4h": E.trend(R0, (15, 20, 30)), "alt kimchi": E.altk(R0, (0.75, 1.0, 1.25))})
IX = idx[idx >= "2021-06-01"]


def d2h(w):
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    return w.reindex(IX.floor("D")).set_axis(IX).fillna(0.0)


def turn(p):
    return p.diff().abs().fillna(p.abs())


POS, MEM = {}, {}                                             # MEM: list of member position frames (each pays its own turnover)
POS["C*"] = d2h(CB.cstar_w()); MEM["C*"] = [POS["C*"]]
tps = [CS.trend4h(n_in=n, n_out=n // 2, positions=True)[1].reindex(index=IX, columns=CB.CFD).fillna(0.0) for n in (15, 20, 30)]
POS["trend 4h"] = sum(tps) / 3; MEM["trend 4h"] = [t / 3 for t in tps]
wp = CS.weiss_expiry(positions=True)[1].reindex(index=IX, columns=CB.CFD).fillna(0.0); POS["Weiss expiry"] = wp; MEM["Weiss expiry"] = [wp]
POS["delev bounce"] = d2h(CS.delev_bounce_weights().reindex(columns=CB.CFD).fillna(0.0)); MEM["delev bounce"] = [POS["delev bounce"]]
POS["coinbase premium"] = d2h(CB.coinbase_premium_w(idx[-1])); MEM["coinbase premium"] = [POS["coinbase premium"]]
pr = pd.read_parquet(ROOT / "results/gen108_preds.parquet").pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
POS["ridge ML"] = d2h(pr.reindex(columns=["BTC", "ETH"]).fillna(0.0)); MEM["ridge ML"] = [POS["ridge ML"]]
aws = [AK.weights(th=t) for t in (0.75, 1.0, 1.25)]; aws = [d2h(w[[c for c in w.columns if c in CB.ALT_CFD]]) for w in aws]
POS["alt kimchi"] = sum(aws) / 3; MEM["alt kimchi"] = [a / 3 for a in aws]
XP = X.positions(IX)
POS["rc6 CFD"] = XP["rc6 CFD"]; MEM["rc6 CFD"] = [XP["rc6 CFD"]]
import basket_live as BL
_, BW = BL.basket(IX); bm = [d2h(v.reindex(columns=list(BL.C6)).fillna(0.0)) for v in BW.values()]
POS["basket CFD"] = sum(bm); MEM["basket CFD"] = bm
coins = sorted(set().union(*[p.columns for p in POS.values()]))
cost = pd.Series({c: (CB.SPREAD.get(c, np.nan) if c in CB.SPREAD.index else CB.ALT_SPREAD.get(c, np.nan)) for c in coins})
xc = X.costs([c for c in coins if not np.isfinite(cost.get(c, np.nan))]) * 1e4 - 1.2 if any(~np.isfinite(cost)) else pd.Series(dtype=float)
cost = cost.fillna(xc).fillna(10.0); cost = (cost + CB.COMM) / 1e4
R = pd.DataFrame({c: CS._hourly_close([c])[c] for c in coins}).pct_change(fill_method=None).reindex(IX).fillna(0.0)
check = {}
for n, p in POS.items():
    g = (p.reindex(columns=coins).fillna(0.0) * R).sum(axis=1)
    x = pd.concat([C.dd(g), C.dd(H[n].reindex(IX).fillna(0.0))], axis=1).loc["2022":"2026-09-30"]
    check[n] = round(float(x.corr().iloc[0, 1]), 3)
orig = CS.v5_weights; CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: orig(D, sleeves, weiss_scale=1.0)
ph, W, M = CS.portfolio_v5(H); CS.v5_weights = orig
k = 0.15 / (C.dd(ph.loc["2022":"2024"]).std() * np.sqrt(365))
Wh = W.reindex(IX.floor("D")).set_axis(IX).ffill().fillna(0.0); mh = (M.reindex(IX.floor("D")).set_axis(IX).ffill().fillna(0.0)) * k
sep = sum(sum((turn(m.reindex(columns=coins).fillna(0.0)) * cost).sum(axis=1) for m in MEM[n]) * Wh[n] * mh for n in POS)
net = sum(POS[n].reindex(columns=coins).fillna(0.0).mul(Wh[n] * mh, axis=0) for n in POS)
netc = (turn(net) * cost).sum(axis=1)
book = (ph * k).reindex(IX).fillna(0.0)
sv = C.dd(sep - netc)
out = {"position check (daily corr vs bf2.8 sleeve P&L)": check,
       "annual cost of these sleeves, per-member (book units)": round(float(C.dd(sep).loc["2022":"2026-09-30"].mean() * 365), 4),
       "annual cost, net execution": round(float(C.dd(netc).loc["2022":"2026-09-30"].mean() * 365), 4),
       "bf2.8 (uncapped) research": C.full(book), "bf2.8 with the net-execution saving": C.full(book + (sep - netc))}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn2_cfd_netting.json").write_text(json.dumps(out, indent=1))
