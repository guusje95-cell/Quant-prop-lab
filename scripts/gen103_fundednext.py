"""Gen103: the CFD book under FundedNext's confirmed conditions (support, 2026-10-19): crypto = BTC ETH XRP ADA DOGE LTC XLM LNK XMR
(no SOL/AVAX/DOT/BCH), leverage 1:1 on challenge and funded, 0.04% commission per side, swap-free option, EAs allowed on MT5.
Not a strategy trial: frozen sleeves re-priced. Writes results/gen103_fundednext.csv and results/gen103_prop.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
g = {"__file__": str(ROOT / "scripts/gen100_firm_costs.py")}; sys.argv = [sys.argv[0], str(S)]
exec(open(ROOT / "scripts/gen100_firm_costs.py").read().split("ALL = set(CFD)")[0], g)
CS, CFD, POS0, pnl, IDX, ns, d2h = g["CS"], g["CFD"], g["POS0"], g["pnl"], g["IDX"], g["ns"], g["d2h"]
q = {"__file__": str(ROOT / "scripts/gen88_coinbase.py")}
exec(open(ROOT / "scripts/gen88_coinbase.py").read().split("C85 = pd.read_parquet")[0], q)
zd = q["zd"]
wq = pd.DataFrame(0.0, index=zd.index, columns=CFD)
for c in ("BTC", "ETH"):
    wq[c] = np.where(zd[c] > 1, 0.5, np.where(zd[c] < -1, -0.5, 0.0))
PREM = d2h(wq).reindex(IDX).fillna(0.0)
from qpl.lab import propfirms as PF
FN = {"BTC", "ETH", "XRP", "ADA", "DOGE", "LINK", "LTC"}


def hourly(pos_set, cap, scale, **kw):
    H, P = {}, {}
    for k, p in pos_set.items():
        H[k], P[k] = pnl(p, swap=0.0 if k == "Weiss expiry" else kw["swap"], **{a: b for a, b in kw.items() if a != "swap"})
    H = pd.DataFrame(H).fillna(0.0); ph, W, mult = CS.portfolio_v5(H)
    d = ph.groupby(ph.index.floor("D")).sum().loc["2022":"2026-09-30"]; k15 = 0.15 / (d.std() * np.sqrt(365))
    Wh = W.reindex(IDX.floor("D")).set_axis(IDX); mh = mult.reindex(IDX.floor("D")).set_axis(IDX)
    net = sum(P[k] * Wh[k].to_numpy()[:, None] for k in P).mul(mh * k15 * scale, axis=0)
    gross = net.abs().sum(axis=1).reindex(ph.index)
    h = ph * k15 * scale
    if cap:
        h = h * (cap / gross).clip(upper=1.0).fillna(1.0)
    return h.loc["2022-01-01":"2026-09-30 23:00"], gross


def stats(h):
    d = h.groupby(h.index.floor("D")).sum(); eq = (1 + d).cumprod()
    sh = lambda a, b: float(d.loc[a:b].mean() / d.loc[a:b].std() * np.sqrt(365))
    return {"Sharpe": sh("2022", "2026"), "TEST": sh("2023", "2024"), "HOLD": sh("2025", "2026"), "ann ret": float(d.mean() * 365), "MaxDD": float((eq / eq.cummax() - 1).min())}


def to_daily_stop(h, stop):
    out = []
    for d, gg in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + gg.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            out.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            out.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(out, columns=["day", "net", "worst", "best"]).set_index("day")


BOOK4 = {**POS0, "coinbase premium": PREM}
BOOK6 = {**BOOK4, "premium carry": ns["POS"]["premium carry"].reindex(IDX).fillna(0.0), "trend 4h": ns["POS"]["trend 4h"].reindex(IDX).fillna(0.0)}
rows, P = [], []
for bname, bk in (("4-sleeve CFD book (C*, Weiss, bounce, Coinbase premium)", BOOK4), ("6-sleeve swap-free book (+ premium carry, trend 4h)", BOOK6)):
    for acct, swap in (("swap-free", 0.0), ("standard swap 3.3", 3.3)):
        if bname.startswith("6") and swap > 0:
            continue
        for sp in ((5, 10), (2, 5)):
            kw = dict(spread=sp, comm=4.0, swap=swap, universe=FN, weekend_flat=False)
            hc, gc = hourly(bk, 1.0, 1.5, **kw); hf, _ = hourly(bk, 1.0, 1.0, **kw); hn, _ = hourly(bk, None, 1.0, **kw)
            r = {"book": bname, "account": acct, "spread": f"{sp[0]}/{sp[1]} bp + 4 bp comm", **{f"funded 1:1 {k}": v for k, v in stats(hf).items()},
                 "no-cap Sharpe": stats(hn)["Sharpe"], "challenge hours capped %": float((gc.loc["2022":] > 1.0).mean() * 100)}
            rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
            if sp == (5, 10):
                f = PF.PRESETS["FundedNext Stellar 2-Step $100k swap-free" if swap == 0 else "FundedNext Stellar 2-Step $100k"]
                dc = to_daily_stop(hc, 0.6 * f.daily_loss); dfd = to_daily_stop(hf, 0.6 * f.daily_loss)
                a = PF.attempts(dc, f, 1.0)
                pb = PF.pipeline(dc, f, 5, 1, 1.0, 1.0, daily_fd=dfd, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
                P.append({"book": bname, "account": acct, "setting": "1.5 / 1.0 / 60% stop, 1:1 cap", "pass": a["P_pass"], "days_to_pass": a["median_days_to_pass"],
                          "mean_net": pb["net_mean"], "p10": pb["net_p10"], "P_profit": pb["P_profit"]})
                print("   PROP", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in P[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen103_fundednext.csv", index=False)
pd.DataFrame(P).to_csv(ROOT / "results/gen103_prop.csv", index=False)
print("done", flush=True)
