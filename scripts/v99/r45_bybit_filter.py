"""v9.9 R45 (realism check, 0 trials): the four new event sleeves restricted to coins that had a Bybit USDT perp at the entry (the venue
HyroTrader uses; event_live.firm_launch, as the v9.8 event short already does). Writes results/v99/r45_bybit_filter.json."""
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
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42
RISK = 1.5
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(x, a, z):
    d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
full = lambda b: [shp(b, "2022", "2026-09-30"), [shp(b, "2022", "2022"), shp(b, "2023", "2024"), shp(b, "2025", "2026-09-30")]]
def capped(H, extra):
    ph, W, M = CS.portfolio_v5(H); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
    for c, gr in extra.items():
        g = g + gr * w(c) * m * k * RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
    for c in extra:
        H2[c] = H2[c] * kk
    return full(CS.portfolio_v5(H2)[0] * k), full(ph * k)
FL = EL.firm_launch()
on_bybit = lambda c, t: (FL.get(EL._norm(c)) is not None) and FL[EL._norm(c)] <= t + pd.Timedelta(hours=2)
srcs = {"venue": list(R16.events().items()) + list(R22.upbit_events().items()), "add": list(R34.events().items()), "hodler": list(R42.events().items())}
fd_all = R32.events()["futures delisting"]
out = {"Bybit launch times known": len(FL), "events kept / total": {}}
res = {}
for flt in (False, True):
    S, P = {}, {}
    for k, ev in srcs.items():
        e = [x for x in ev if on_bybit(*x)] if flt else ev
        if flt:
            out["events kept / total"][k] = [len(e), len(ev)]
        S[k], P[k] = RB.venue(e, idx)
    fe = [x for x in fd_all if on_bybit(*x)] if flt else fd_all
    if flt:
        out["events kept / total"]["futures delisting"] = [len(fe), len(fd_all)]
    hf, _ = R32.sleeve(fe, 14, idx); gf = (hf != 0).astype(float) * 0.05
    H = V8.assign(**{"venue listing short": S["venue"], "futures-delisting short": hf, "binance add short": S["add"], "hodler short": S["hodler"]})
    ex = {"venue listing short": P["venue"].abs().sum(axis=1), "futures-delisting short": gf, "binance add short": P["add"].abs().sum(axis=1), "hodler short": P["hodler"].abs().sum(axis=1)}
    c, u = capped(H, ex); res["Bybit-filtered" if flt else "as tested (Binance perps)"] = {"uncapped": u, "capped (4.5% low-cap, risk 1.5)": c}
out.update(res); out["v9.8 capped"] = capped(V8, {})[0]
print(json.dumps(out, indent=1)); (ROOT / "results/v99/r45_bybit_filter.json").write_text(json.dumps(out, indent=1))
