"""v9.9 R30b (diagnostics of R30, no selection): exposure per event in the book, placebo dates for the separate sleeve, half weight
(as Weiss), and the HyroTrader total low-cap cap on event short + venue sleeve together (every coin counted low-cap). Writes results/v99/r30b_checks.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r29_bandit as R29
RISK = 1.5


def venue(ev, idx):
    """(pnl, positions) of the R16 A rules on a list of (coin, T); a coin is not shorted again within 7 days"""
    pnl = pd.Series(0.0, index=idx); P = {}; last = {}
    for coin, T in sorted(ev, key=lambda x: x[1]):
        if coin in last and T - last[coin] < pd.Timedelta(days=7):
            continue
        h, u = R16.trades({coin: T}, idx, "A")
        if not u:
            continue
        last[coin] = T; pnl = pnl + h
        pos = (h != 0).astype(float) * -R16.SIZE
        P[coin] = P.get(coin, pd.Series(0.0, index=idx)).where(lambda s: s != 0, pos)
    return pnl, pd.DataFrame(P, index=idx).fillna(0.0)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    CE = list(R16.events().items()); UE = list(R22.upbit_events().items()); out = {}
    for lab, ev in (("Coinbase only", CE), ("Coinbase + Upbit", CE + UE)):
        h, P = venue(ev, idx); H = V8.assign(**{"venue listing short": h})
        ph, W, M = CS.portfolio_v5(H); k = kf(ph); b = ph * k
        wv = W["venue listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        eff = P.abs().mul(wv * m * k * RISK, axis=0); tot = eff.sum(axis=1); one = eff.max(axis=1); act = tot[tot > 0].loc["2022":]
        r = {"book": full(b), "effective short per event coin, % of equity at risk 1.5: median / p95 / max": [round(float(one[one > 0].loc["2022":].median() * 100), 2), round(float(one[one > 0].loc["2022":].quantile(0.95) * 100), 2), round(float(one.loc["2022":].max() * 100), 2)],
             "venue sleeve total when active: median / max %": [round(float(act.median() * 100), 2), round(float(act.max() * 100), 2)]}
        half = full(R29.portfolio_mult(H, lambda D, W_: pd.DataFrame({c: (0.5 if c == "venue listing short" else 1.0) for c in W_.columns}, index=W_.index)) * k)
        r["half weight (as Weiss)"] = half
        # total low-cap cap: event short + venue sleeve together, every coin low-cap
        we = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
        g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * we * m * k * RISK + P.abs().sum(axis=1) * wv * m * k * RISK
        kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
        r["with the 4.5% total low-cap cap (risk 1.5)"] = full(CS.portfolio_v5(V8.assign(**{"listing short": s8 * kk, "venue listing short": h * kk}))[0] * k)
        pl = {}
        for d in (-90, -60, 60, 90):
            hp, _ = venue([(c, t + pd.Timedelta(days=d)) for c, t in ev if pd.Timestamp("2022-01-01") <= t + pd.Timedelta(days=d) <= pd.Timestamp("2026-09-23")], idx)
            pl[f"{d:+d} days"] = full(CS.portfolio_v5(V8.assign(**{"venue listing short": hp}))[0] * kf(CS.portfolio_v5(V8.assign(**{"venue listing short": hp}))[0]))
        r["placebo dates (separate sleeve)"] = pl
        out[lab] = r; print(lab, json.dumps(r), flush=True)
    ref_c = CS.portfolio_v5(V8)[0]; g0 = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0)
    ph, W, M = CS.portfolio_v5(V8); k0 = kf(ph); we = W["listing short"].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0); m0 = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    kk0 = (0.045 / (g0 * we * m0 * k0 * RISK)).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0)
    out["reference v9.8"] = full(ph * k0); out["reference v9.8 with the cap"] = full(CS.portfolio_v5(V8.assign(**{"listing short": s8 * kk0}))[0] * k0)
    (ROOT / "results/v99/r30b_checks.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("reference v9.8", "reference v9.8 with the cap")}))


if __name__ == "__main__":
    main()
