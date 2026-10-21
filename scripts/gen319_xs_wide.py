"""Gen319 (config/gen319_protocol.json): 60-coin invvol XS momentum / reversal as added sleeves in v8.5. Writes results/gen319.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import crypto_sleeves as CS
END = L.END
coins = CS._breadth_universe(); P = CS._breadth_close(coins).resample("1D").last()
listed = P.notna().cumsum() >= 60; vol = P.pct_change(fill_method=None).rolling(30).std()


def xs_w(score, hold=7):
    rk = score.where(listed).rank(axis=1, pct=True); iv = (1 / vol).where(listed)
    wl, ws = iv.where(rk > 2 / 3, 0.0), iv.where(rk <= 1 / 3, 0.0)
    w = wl.div(wl.sum(axis=1), axis=0) - ws.div(ws.sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


out = {"reference v8.5": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}
A = xs_w(P.shift(1) / P.shift(29) - 1); B = xs_w(-(P / P.shift(7) - 1))
for k, w in (("A XS momentum 28d invvol", A), ("B XS reversal 7d invvol", B)):
    L.judge(k, CS.premium_carry_breadth(coins=coins, w=w).loc[:END + " 23:00"], out, dev_start="2020-01-01")
json.dump(out, open(L.ROOT / "results/gen319.json", "w"), indent=1)
