import sys; from pathlib import Path; R = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / "scripts")); sys.path.insert(0, str(R / "src"))
import gen52_optimize as G
import numpy as np, pandas as pd
from qpl.lab import propfirms as PF, strategies as S
sig = S.CStarTrend().signal(G.CR, S.CStarTrend().defaults())
sig2 = S.CStarTrend().signal(G.CR, {"stablecoin_filter": False, "long_only": True})
ch = G.SRC["Binance spot majors (hourly, 2022+)"]()
hret = ch.close[G.CR.symbols].sort_index().pct_change(fill_method=None).fillna(0.0); hday = hret.index.floor("D")
def hourly(w, scale, stop, tp, lim):
    held = (w * scale).shift(1).fillna(0.0)
    H = pd.DataFrame(held.reindex(hday).to_numpy(), index=hret.index, columns=w.columns).fillna(0.0)
    turn = held.diff().abs().sum(axis=1) * 7.5 / 1e4; port = (H * hret).sum(axis=1); rows = []
    for dd, g in port.groupby(hday):
        if dd not in turn.index: continue
        path = np.concatenate([[1.0], np.cumprod(1 + g.to_numpy())]) * (1 - turn.loc[dd]); k = None
        if stop > 0 and (path <= 1 - stop * lim).any(): k = int(np.argmax(path <= 1 - stop * lim))
        if tp > 0 and (path >= 1 + tp).any():
            k2 = int(np.argmax(path >= 1 + tp)); k = k2 if k is None or k2 < k else k
        if k is not None:
            c = path[k] - 0.001; rows.append((dd, c - 1, min(path[:k + 1].min(), c) - 1, path[:k + 1].max() - 1))
        else: rows.append((dd, path[-1] - 1, path.min() - 1, path.max() - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")
cases = [("plain C* (vol30, no band), 1.0/0.4", sig, 30, 0.0, 1.0, 0.4, 0, 0),
         ("C* vol20 band0.2, 1.0/0.4", sig, 20, 0.2, 1.0, 0.4, 0, 0),
         ("FTMO pick: C* no filter vol20 band0.2, 1.5/0.6, stop90%, TP4%", sig2, 20, 0.2, 1.5, 0.6, 0.9, 0.04)]
for nm, sg, look, b, sc, sf, stop, tp in cases:
    w, d = G.backtest(sg, look, b)
    for fn, f0 in G.FIRMS.items():
        f = PF.replace(f0, stop_frac=stop, take_profit=tp)
        t = G.prop_eval(d.loc[G.TEST[0]:G.TEST[1]], f, sc, sf)
        hc = hourly(w, sc, stop, tp, f0.daily_loss); hf = hourly(w, sf, stop, tp, f0.daily_loss)
        a = PF.attempts(hc, f0, 1.0); p = PF.pipeline(hc, f0, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
        print(f"{nm:62s} {fn:4s} TEST pass {t['pass']:.0%} net {t['net']:7.0f} P(profit) {t['p_profit']:.0%} | HOURLY pass {a['P_pass']:.0%} net {p['net_mean']:7.0f} p50 {p['net_p50']:7.0f} P(profit) {p['P_profit']:.0%}", flush=True)
