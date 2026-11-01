"""v9.9 R21 (measurement, 0 trials): what the HyroTrader total low-cap cap really costs, with the OFFICIAL classification on the last
~11 months (CoinGecko free history is 365 days): low-cap = market cap < $100M or 24h volume between $0.5M and $5M (previous day's
values); a coin without CoinGecko data counts as low-cap; Bybit Innovation Zone membership is unknown (not modelled). Compared with the
conservative reading used so far (every event coin is low-cap). Cap 4.5% of the initial balance at risk 1.5, as in sizing_v98_capped.py,
applied to the low-cap part of the event short only. Writes results/v99/r21_lowcap_real.json."""
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
CG = ROOT / "research_data/coingecko_lowcap"; RISK = 1.5


def lowcap_flags(idx, names):
    F = {}
    for n in names:
        c = n[4:] if n.startswith("spo_") else n; f = CG / f"{c}.parquet"
        if not f.exists():
            F[n] = pd.Series(True, index=idx); continue
        d = pd.read_parquet(f).shift(1)                                     # previous day's values
        lc = (d.mcap < 1e8) | ((d.volume >= 5e5) & (d.volume <= 5e6))
        F[n] = lc.reindex(idx.floor("D")).set_axis(idx).fillna(True).astype(bool)
    return pd.DataFrame(F)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit_k = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    s, pos, _ = EL.pnl(idx); flags = {}
    def hook(P, CF):
        Fl = lowcap_flags(P.index, P.columns); flags["F"] = Fl
        return P.where(Fl.reindex(columns=P.columns).fillna(True).to_numpy(), 0.0)
    s_low, pos_low, _ = EL.pnl(idx, pre_cap=hook); s_high = s - s_low
    ph, W, M = CS.portfolio_v5(V7.assign(**{"listing short": s}))
    w = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    def capped(sl, sh, gross):
        k = (0.045 / (gross * w * m * 0.902 * RISK)).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
        return CS.portfolio_v5(V7.assign(**{"listing short": sl * k + sh}))[0]
    g_all = pos.abs().sum(axis=1).reindex(idx).fillna(0.0); g_low = pos_low.abs().sum(axis=1).reindex(idx).fillna(0.0)
    unc = CS.portfolio_v5(V7.assign(**{"listing short": s}))[0]; kk = unit_k(unc)
    books = {"uncapped": unc * kk, "cap, every event coin low-cap (conservative)": capped(s, 0 * s, g_all) * kk, "cap, official classification": capped(s_low, s_high, g_low) * kk}
    a, z = "2025-11-03", "2026-09-30"
    def shp(x):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
    F = flags["F"].loc[a:z]; P = pos.reindex(F.index).loc[a:z]; held = (P != 0)
    share = float((P.abs() * F.reindex(columns=P.columns).fillna(True)).sum().sum() / P.abs().sum().sum())
    out = {"window": [a, z], "coins with CoinGecko data": len(list(CG.glob("*.parquet"))),
           "share of event-short notional that is low-cap (official)": round(share, 3),
           "book Sharpe in the window": {k: shp(v) for k, v in books.items()},
           "note": "Sharpe of ~11 months is noisy; the useful number is the DIFFERENCE between the two capped books (same months)"}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r21_lowcap_real.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
