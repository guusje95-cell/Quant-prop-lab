"""Gen322 (config/gen322_protocol.json): tranched carry rebalancing in v8.5 and bf2.4. Writes results/gen322.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import bf2lab as F
import cfd_book as CB
import crypto_sleeves as CS
from qpl.lab import binance_pack as B
END = L.END


def tranche(fn):
    """fn(offset) -> weights held 7 days from rebalance days with that offset; returns the mean over offsets 0..6."""
    return sum(fn(o) for o in range(7)) / 7


def staggered(raw, o, hold=7):
    """raw daily weights recomputed every day -> held from days with index % hold == o."""
    return raw.where(pd.Series((np.arange(len(raw)) % hold) == o, index=raw.index), np.nan).ffill().fillna(0.0)


def raw_premium(coins, P, prem_fn, invvol):
    prem = pd.DataFrame({c: prem_fn(c).resample("1D").mean() for c in coins}).reindex(P.index).rolling(7).mean()
    listed = P.notna().cumsum() >= 60; rk = (-prem).where(listed).rank(axis=1, pct=True)
    if invvol:
        iv = (1 / P.pct_change(fill_method=None).rolling(30).std()).where(listed); wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
        return wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
    return (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)


from qpl.lab import extra_pack as X
pf = lambda c: B.premium(c)["close"] if c in B.coins() else X.premium(c)
out = {"reference v8.5": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()], "reference bf2.4": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()]}
# v8.5
C20 = B.coins(); P20 = B.panel("close", "1D", C20); r20 = raw_premium(C20, P20, pf, True)
assert float((staggered(r20, 0) - CS.premium_weights(invvol=True)).abs().max().max()) < 1e-12
U60 = CS._breadth_universe(); P60 = CS._breadth_close(U60).resample("1D").last(); r60 = raw_premium(U60, P60, pf, True)
H = L.H6.copy(); H["premium carry"] = CS._from_daily_weights(tranche(lambda o: staggered(r20, o)), C20, 5).reindex(H.index).fillna(0.0)
pc60 = CS.premium_carry_breadth(w=tranche(lambda o: staggered(r60, o))).loc[:END + " 23:00"].reindex(H.index).fillna(0.0).rename("premium carry 60")
b = L.CS.portfolio_v5(pd.concat([H, L.RIDGE] + [a for a in L.ALTK if a.name != "premium carry 60"] + [pc60], axis=1).fillna(0.0))[0]
B1, k = L.sh(b, "2022-01-01", END), L.per(b, "2022-01-01")
out["v8.5 tranched"] = [round(B1, 3), np.round(k, 3).tolist()]; out["v8.5 pass"] = bool(B1 > L.REF[0] and k[1] >= L.REF[1][1] and k[2] >= L.REF[1][2]); print(out, flush=True)
# bf2.4
R, pos, _ = CB.positions(); P11 = B.panel("close", "1D", CB.CFD); r11 = raw_premium(CB.CFD, P11, pf, False)
assert float((staggered(r11, 0) - CB.premium_carry_w()).abs().max().max()) < 1e-12
U = CB.CARRY_CFD; PU = CS._breadth_close(U).resample("1D").last(); rU = raw_premium(U, PU, pf, True)
HB = F.HB0.copy(); HB["premium carry"] = CB.sleeve_pnl(CB.d2h(tranche(lambda o: staggered(r11, o)), pos["C*"].index), R).reindex(F.IDXbf).fillna(0.0)
wU = tranche(lambda o: staggered(rU, o)); Hc = CS._breadth_close(U); rc = Hc.pct_change(fill_method=None).fillna(0.0)
hU = wU.reindex(wU.index.append(pd.DatetimeIndex([wU.index[-1] + pd.Timedelta(days=1)]))).reindex(columns=U).shift(1).reindex(Hc.index.floor("D")).set_axis(Hc.index).fillna(0.0)
pcbf = ((hU * rc).sum(axis=1) - hU.diff().abs().fillna(hU.abs()).mul((CB.CARRY_SPREAD + CB.COMM) / 1e4, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0).rename("premium carry BF")
b = F.CS.portfolio_v5(pd.concat([HB, F.IS0, F.HB_RIDGE.rename("ridge ML")] + [a for a in F.ALTK_BF if a.name != "premium carry BF"] + [pcbf], axis=1).fillna(0.0))[0]
B1, k = F.sh(b, "2022-01-01", END), F.per(b, "2022-01-01")
out["bf2.4 tranched"] = [round(B1, 3), np.round(k, 3).tolist()]; out["bf2.4 pass"] = bool(B1 > F.REF[0] and k[1] >= F.REF[1][1] and k[2] >= F.REF[1][2])
print(out); json.dump(out, open(L.ROOT / "results/gen322.json", "w"), indent=1)
