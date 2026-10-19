"""Gen104: the CFD books under BrightFunded's MT5 specification (exported 2026-10-19, research_data/firm_specs/): per-coin swap from the
swap points (converted at the latest Coinbase price), 1:5 crypto leverage, measured spread BTC 0.36 bp / ETH 2.65 bp, commission 0.024%
per deal. Not a strategy trial. Writes results/gen104_brightfunded.csv and results/gen104_prop.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; S = Path(sys.argv[1])
g = {"__file__": str(ROOT / "scripts/gen103_fundednext.py")}; sys.argv = [sys.argv[0], str(S)]
exec(open(ROOT / "scripts/gen103_fundednext.py").read().split("BOOK4 = {")[0], g)
CS, CFD, IDX, POS0, PREM, ns, PF, stats, to_daily_stop = (g[k] for k in ("CS", "CFD", "IDX", "POS0", "PREM", "ns", "PF", "stats", "to_daily_stop"))
R1 = ns["R1"]; ROLL = pd.Series(IDX.hour == 21, index=IDX)
spec = pd.read_csv(sorted((ROOT / "research_data/firm_specs").glob("BrightFunded*.csv"))[-1]).set_index("symbol")
MAP = {"BTC": "BTC/USD", "ETH": "ETH/USD", "SOL": "SOL/USD", "XRP": "XRP/USD", "ADA": "ADA/USD", "DOGE": "XDG/USD", "LINK": "LINK/USD",
       "AVAX": "AVAX/USD", "DOT": "DOT/USD", "LTC": "LTC/USD", "BCH": "BCH/USD"}
SWL, SWS = {}, {}
for c, s in MAP.items():
    px = pd.read_parquet(ROOT / f"research_data/coinbase/{c}-USD_1h.parquet")["close"].iloc[-1]; pt = 10.0 ** -spec.at[s, "digits"]
    SWL[c] = -spec.at[s, "swap_long"] * pt / px * 1e4; SWS[c] = -spec.at[s, "swap_short"] * pt / px * 1e4     # cost in bp per day (positive)
SWL, SWS = pd.Series(SWL), pd.Series(SWS)


def pnl(pos, spread, comm, swapfree):
    pos = pos.reindex(columns=CFD).fillna(0.0)
    cost = pd.Series({c: spread[0] if c == "BTC" else (spread[1] if c == "ETH" else spread[2]) for c in CFD}) + comm
    turn = pos.diff().abs().fillna(pos.abs()).mul(cost / 1e4, axis=1).sum(axis=1)
    sw = 0.0 if swapfree else (pos.clip(lower=0).mul(SWL / 1e4, axis=1) + (-pos.clip(upper=0)).mul(SWS / 1e4, axis=1)).sum(axis=1).where(ROLL, 0.0)
    return (pos * R1).sum(axis=1) - turn - sw, pos


def hourly(pos_set, cap, scale, **kw):
    H, P = {}, {}
    for k, p in pos_set.items():
        H[k], P[k] = pnl(p, kw["spread"], kw["comm"], True if k == "Weiss expiry" else kw["swapfree"])
    H = pd.DataFrame(H).fillna(0.0); ph, W, mult = CS.portfolio_v5(H)
    d = ph.groupby(ph.index.floor("D")).sum().loc["2022":"2026-09-30"]; k15 = 0.15 / (d.std() * np.sqrt(365))
    Wh = W.reindex(IDX.floor("D")).set_axis(IDX); mh = mult.reindex(IDX.floor("D")).set_axis(IDX)
    gross = sum(P[k] * Wh[k].to_numpy()[:, None] for k in P).mul(mh * k15 * scale, axis=0).abs().sum(axis=1).reindex(ph.index)
    h = ph * k15 * scale
    if cap:
        h = h * (cap / gross).clip(upper=1.0).fillna(1.0)
    return h.loc["2022-01-01":"2026-09-30 23:00"], H


BOOK4 = {**POS0, "coinbase premium": PREM}
BOOK6 = {**BOOK4, "premium carry": ns["POS"]["premium carry"].reindex(IDX).fillna(0.0), "trend 4h": ns["POS"]["trend 4h"].reindex(IDX).fillna(0.0)}
BTCONLY = {k: v.where(v.columns == "BTC", 0.0) if False else v.mul(pd.Series({c: 1.0 if c == "BTC" else 0.0 for c in v.columns}), axis=1) for k, v in BOOK4.items()}
rows, P = [], []
f = PF.PRESETS["BrightFunded Two-Step Classic $100k"]
for bname, bk in (("4-sleeve CFD book", BOOK4), ("6-sleeve book", BOOK6), ("4-sleeve, BTC only", BTCONLY)):
    for acct, sf in (("standard (real BF swaps)", False), ("swap-free (if the add-on exists)", True)):
        for cm in (2.4, 1.2):
            kw = dict(spread=(0.4, 2.7, 10.0), comm=cm, swapfree=sf)
            hf, H = hourly(bk, 5.0, 1.0, **kw); st = stats(hf)
            sl = {f"sleeve {k}": float(H[k].loc["2022":].mean() / H[k].loc["2022":].std() * np.sqrt(365 * 24)) for k in H if H[k].loc["2022":].std() > 0}
            r = {"book": bname, "account": acct, "commission bp/side": cm, **st, **{k: round(v, 2) for k, v in sl.items()}}
            rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
            if cm == 2.4 and bname != "4-sleeve, BTC only":
                hc, _ = hourly(bk, 5.0, 1.5, **kw)
                dc = to_daily_stop(hc, 0.6 * f.daily_loss); dfd = to_daily_stop(hf, 0.6 * f.daily_loss)
                a = PF.attempts(dc, f, 1.0)
                pb = PF.pipeline(dc, f, 5, 1, 1.0, 1.0, daily_fd=dfd, horizon_days=730, method="bootstrap", n_boot=500, block=20, seed=11)
                P.append({"book": bname, "account": acct, "pass": a["P_pass"], "mean_net": pb["net_mean"], "p10": pb["net_p10"], "P_profit": pb["P_profit"]})
                print("   PROP", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in P[-1].items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen104_brightfunded.csv", index=False)
pd.DataFrame(P).to_csv(ROOT / "results/gen104_prop.csv", index=False)
print("done", flush=True)
