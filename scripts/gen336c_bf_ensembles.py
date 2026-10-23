"""Gen336c (config/gen335_protocol.json): carry BF and alt kimchi BF neighbourhood ensembles in bf2.6. Appends to results/gen336.json."""
import itertools
import json
import numpy as np
import pandas as pd
import bf2lab as F
import crypto_sleeves as CS
import alt_kimchi as AK
import cfd_book as CB
from qpl.lab import binance_pack as B
END = F.END; U = CB.CARRY_CFD; H = CS._breadth_close(U); r2 = H.pct_change(fill_method=None).fillna(0.0)


def carry(lk, hd):
    cw = CS.premium_breadth_weights(coins=U, look=lk, hold=hd, invvol=True, tranched=True)
    h2 = cw.reindex(cw.index.append(pd.DatetimeIndex([cw.index[-1] + pd.Timedelta(days=1)]))).reindex(columns=U).shift(1).reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0)
    return ((h2 * r2).sum(axis=1) - h2.diff().abs().fillna(h2.abs()).mul((CB.CARRY_SPREAD + CB.COMM) / 1e4, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)


def altk(th):
    aw = AK.weights(END + " 23:00", th=th); ac = [c for c in aw.columns if c in CB.ALT_CFD]; aw = aw[ac]
    cost = pd.Series({c: CB.ALT_SPREAD[c] + CB.COMM for c in ac}) / 1e4
    r = B.panel("close", "1h", ac).loc[:END + " 23:00"].pct_change(fill_method=None).fillna(0.0)
    held = aw.reindex(aw.index.append(pd.DatetimeIndex([aw.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
    return ((held * r).sum(axis=1) - held.diff().abs().fillna(held.abs()).mul(cost, axis=1).sum(axis=1)).reindex(F.IDXbf).fillna(0.0)


assert np.allclose(carry(7, 7).to_numpy(), [s for s in F.ALTK_BF if s.name == "premium carry BF"][0].to_numpy())
assert np.allclose(altk(1.0).to_numpy(), [s for s in F.ALTK_BF if s.name == "alt kimchi"][0].to_numpy())
ce = sum(carry(a, b) for a, b in itertools.product((5, 7, 10), (5, 7, 10))) / 9; ae = sum(altk(t) for t in (0.75, 1.0, 1.25)) / 3
ex = [ae.rename("alt kimchi"), ce.rename("premium carry BF")]
b = F.CS.portfolio_v5(pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML")] + ex, axis=1).fillna(0.0))[0]
k = [round(F.sh(b, "2022-01-01", END), 3)] + np.round(F.per(b, "2022-01-01"), 3).tolist()
R = [round(F.REF[0], 3)] + np.round(F.REF[1], 3).tolist()
res = {"reference bf2.6": R, "bf2.6 D/T/H": k, "every period not lower": bool(all(a >= c for a, c in zip(k[1:], R[1:]))),
       "strict pass": bool(all(a >= c for a, c in zip(k[1:], R[1:])) and k[0] >= R[0] + 0.05)}
print(res, flush=True)
d = json.load(open(F.ROOT / "results/gen336.json")); d["Gen336c bf2.6 carry BF + alt kimchi ensembles"] = res
json.dump(d, open(F.ROOT / "results/gen336.json", "w"), indent=1)
