"""R53b (research/v99/r53b_protocol.json): robustness of ERC weights in the v9.9 candidate. Writes results/v99/r53b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c11_erc as E
import crypto_sleeves as CS
import r48_stress as S


def with_weights(fn, wf):
    orig = CS.v5_weights; CS.v5_weights = wf
    try:
        return fn()
    finally:
        CS.v5_weights = orig


def capped_series(H, ex):
    """the capped book as an hourly series (same rule as r48_stress.capped)"""
    idx = S.idx; ph, W, M = CS.portfolio_v5(H); k = S.kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = S.pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * S.RISK
    for c, gr in ex.items():
        g = g + gr * w(c) * m * k * S.RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
    for c in ex:
        H2[c] = H2[c] * kk
    ph2, W2, _ = CS.portfolio_v5(H2); return ph2 * k, W2


def risk(b, r=1.5):
    d = S.dd(b.loc["2022":"2026-09-30"]) * r; eq = (1 + d).cumprod()
    return {"worst day %": round(float(d.min() * 100), 2), "max DD %": round(float((eq / eq.cummax() - 1).min() * 100), 2), "days < -2.5%": int((d < -0.025).sum())}


def main():
    Ev = S.per_event(); idx = S.idx
    def mk(EvX):
        H = S.V8.copy(); ex = {}
        for k, L in EvX.items():
            H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
        return H, ex
    H, ex = mk(Ev); out = {}
    erc = lambda sh: (lambda D, sleeves, weiss_scale=0.5: E.erc_weights(D, sleeves, weiss_scale, shrink=sh))
    out["inverse-vol"] = S.capped(H, ex)
    for sh in (0.25, 0.5, 0.75):
        out[f"ERC shrink {sh}"] = with_weights(lambda: S.capped(H, ex), erc(sh)); print(sh, out[f"ERC shrink {sh}"], flush=True)
    out["v9.8 capped: inverse-vol / ERC"] = [S.capped(S.V8, {}), with_weights(lambda: S.capped(S.V8, {}), erc(0.5))]
    ret = {k: np.array([h.sum() for _, _, h, _ in L]) for k, L in Ev.items()}
    drop = {k: [x for x, keep in zip(L, np.isin(np.arange(len(L)), np.argsort(ret[k])[::-1][:max(1, int(round(0.1 * len(L))))], invert=True)) if keep] for k, L in Ev.items()}
    Hd, exd = mk(drop)
    out["drop best 10% events: inverse-vol / ERC"] = [S.capped(Hd, exd), with_weights(lambda: S.capped(Hd, exd), erc(0.5))]
    bi, Wi = capped_series(H, ex); be, We = with_weights(lambda: capped_series(H, ex), erc(0.5))
    out["risk at 1.5: inverse-vol / ERC"] = [risk(bi), risk(be)]
    share = lambda W: (W.loc["2022":].div(W.loc["2022":].sum(axis=1), axis=0).mean() * 100).round(1).to_dict()
    out["mean weight share % (2022-26): inverse-vol / ERC"] = [share(Wi), share(We)]
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r53b_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
