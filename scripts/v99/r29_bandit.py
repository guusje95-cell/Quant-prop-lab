"""v9.9 R29 (research/v99/r29_protocol.json): (contextual) exponentiated-gradient allocation over the v9.8 sleeves. Writes results/v99/r29_bandit.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B


def portfolio_mult(H, Mfun, vol=0.15, start="2022-01-01"):
    D = H.groupby(H.index.floor("D")).sum(); W = CS.v5_weights(D, list(H.columns)); W = W * Mfun(D, W)
    Wh = W.reindex(H.index.floor("D")).set_axis(H.index)
    raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
    tgt = (vol / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mult = (lvl * tgt).loc[start:]
    return (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()


def eg(D, W, ctx=None, eta=0.5):
    M = pd.DataFrame(1.0, index=D.index, columns=D.columns)
    for m in pd.date_range("2021-07-01", D.index[-1], freq="MS"):
        past = D.loc[m - pd.Timedelta(days=182): m - pd.Timedelta(days=1)]
        days = D.loc[m: m + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)].index
        if ctx is None:
            groups = [(days, past)]
        else:
            groups = [(days[ctx.reindex(days).fillna(False).to_numpy() == v], past[ctx.reindex(past.index).fillna(False).to_numpy() == v]) for v in (True, False)]
        for dd_, pp in groups:
            if len(dd_) == 0 or len(pp) < 30:
                continue
            act = [c for c in D.columns if (pp[c] != 0).sum() >= 20 and pp[c].std() > 0]
            if not act:
                continue
            s = pp[act].mean() / pp[act].std() * np.sqrt(365); e = np.exp(eta * s); e = e / e.mean()
            M.loc[dd_, act] = e.clip(0.5, 2.0).to_numpy()
    return M


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    ref = full(unit(CS.portfolio_v5(V8)[0])); out = {"reference v9.8": ref, "check: multiplier 1 reproduces v9.8": full(unit(portfolio_mult(V8, lambda D, W: 1.0)))}
    btc = B.k5("BTC").close.resample("1D").last(); ctx = (btc > btc.rolling(200).mean()).shift(1)
    for name, f in (("A bandit", lambda D, W: eg(D, W)), ("B contextual bandit", lambda D, W: eg(D, W, ctx=ctx))):
        r = full(unit(portfolio_mult(V8, f))); out[name] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
        print(name, out[name], flush=True)
    (ROOT / "results/v99/r29_bandit.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
