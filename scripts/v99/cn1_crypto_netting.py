"""CN-1 (execution, 0 alpha trials): how much of the crypto book's cost the live bot saves by trading the NET position per coin.
The research / paper book charges every sleeve (and every ensemble / basket member) its own turnover at 5 bp per side; the bot trades
sum_i W_i x m x pos_i per coin. Positions are rebuilt from the sleeve code for the eight non-event v9.8 sleeves (C*, trend 4h ensemble,
Weiss, delev bounce, ridge, alt kimchi ensemble, diversifier basket, relative crowding 6) and checked against the v9.8 sleeve P&L
(corr of position x return with the sleeve series). Cost saving = per-member costs - net costs (event short excluded: no overlap).
Writes results/v99/cn1_crypto_netting.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import basket_live as BL
import crypto_sleeves as CS
import alt_kimchi as AK
from qpl.lab import binance_pack as B

IX = pd.date_range("2022-01-01", "2026-09-30 23:00", freq="h")
H = pd.read_parquet(ROOT / "results/v98_oct_oos.parquet").drop(columns="port").loc[:"2026-09-30 23:00"]


def d2h(w):
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    return w.reindex(IX.floor("D")).set_axis(IX).fillna(0.0)


POS = {}; MEMBER_TURN = {}                                                     # per-member turnover (what the research pays)
def turn(p):
    return p.diff().abs().fillna(p.abs()).sum(axis=1)
c = d2h(CS.cstar_weights()); POS["C*"] = c; MEMBER_TURN["C*"] = turn(c)
outs = [CS.trend4h(n_in=n, n_out=n // 2, positions=True)[1].reindex(IX).fillna(0.0) for n in (15, 20, 30)]
POS["trend 4h"] = sum(outs) / 3; MEMBER_TURN["trend 4h"] = sum(turn(o) for o in outs) / 3
wp = CS.weiss_expiry(positions=True)[1].reindex(IX).fillna(0.0); POS["Weiss expiry"] = wp; MEMBER_TURN["Weiss expiry"] = turn(wp)
db = d2h(CS.delev_bounce_weights()); POS["delev bounce"] = db; MEMBER_TURN["delev bounce"] = turn(db)
pr = pd.read_parquet(ROOT / "results/gen108_preds.parquet").pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
rg = d2h(pr); POS["ridge ML"] = rg; MEMBER_TURN["ridge ML"] = turn(rg)
ws = [d2h(AK.weights(th=t)) for t in (0.75, 1.0, 1.25)]; POS["alt kimchi"] = sum(ws) / 3; MEMBER_TURN["alt kimchi"] = sum(turn(x) for x in ws) / 3
_, BW = BL.basket(IX); bm = {k: d2h(v) for k, v in BW.items()}
POS["diversifier basket"] = sum(bm.values()); MEMBER_TURN["diversifier basket"] = sum(turn(x) for x in bm.values())
POS["relative crowding 6"] = BL.rc_positions(IX).fillna(0.0); MEMBER_TURN["relative crowding 6"] = turn(POS["relative crowding 6"])
coins = sorted(set().union(*[p.columns for p in POS.values()]))
R = B.panel("close", "1h", coins).pct_change(fill_method=None).reindex(IX).fillna(0.0)
check = {}
for n, p in POS.items():
    g = (p.reindex(columns=coins).fillna(0.0) * R).sum(axis=1)
    x = pd.concat([g.groupby(g.index.floor("D")).sum(), H[n].groupby(H[n].index.floor("D")).sum()], axis=1).loc["2022":"2026-09-30"].dropna()
    check[n] = round(float(x.corr().iloc[0, 1]), 3)
Hb = H.loc["2020":"2026-09-30 23:00"]
ph, W, mult = CS.portfolio_v5(Hb, start="2022-01-01")
Wh = W.reindex(IX.floor("D")).set_axis(IX).ffill().fillna(0.0); mh = mult.reindex(IX.floor("D")).set_axis(IX).ffill().fillna(0.0)
sep = sum(Wh[n] * mh * MEMBER_TURN[n] for n in POS) * 5e-4
net = sum((POS[n].reindex(columns=coins).fillna(0.0)).mul(Wh[n] * mh, axis=0) for n in POS)
netc = net.diff().abs().fillna(net.abs()).sum(axis=1) * 5e-4
book = ph.loc["2022":"2026-09-30"]
d = lambda s: s.groupby(s.index.floor("D")).sum().reindex(pd.date_range("2022-01-01", "2026-09-30")).fillna(0.0)
sh = lambda s: float(s.mean() / s.std() * np.sqrt(365))
saving = d(sep - netc)
per = {}
for a, b in (("2022-01-01", "2022-12-31"), ("2023-01-01", "2024-12-31"), ("2025-01-01", "2026-09-30")):
    bb = d(book).loc[a:b]; per[f"{a[:4]}-{b[:4]}"] = [round(sh(bb), 3), round(sh(bb + saving.loc[a:b]), 3)]
out = {"position check (corr daily gross vs v9.8 sleeve P&L)": check,
       "annual cost, per-member accounting (book units)": round(float(d(sep).mean() * 365), 4), "annual cost, net execution": round(float(d(netc).mean() * 365), 4),
       "v9.8 book Sharpe 2022-26 research / with the net-execution saving": [round(sh(d(book)), 3), round(sh(d(book) + saving), 3)], "by period [research, net]": per}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/cn1_crypto_netting.json").write_text(json.dumps(out, indent=1))
