"""v9.9 R46 (research/v99/r46_protocol.json): Bybit-only / Bybit-first listings as a separate listing-short sleeve. Writes results/v99/r46_bybit_listing_sleeve.json."""
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
import listing_live as LL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42
D = ROOT / "research_data/bybit_listings"; RISK = 1.5


def sleeve(idx):
    TF = set(json.loads((ROOT / "config/tradfi_perps.json").read_text())["symbols"])
    EVB = LL.events(); bt0 = {s[:-4]: t0 for s, t0, c, f in EVB}; EVY = []
    for x in json.loads((D / "instruments.json").read_text()):
        sym = x["symbol"]; base = sym[:-4]; t0 = pd.to_datetime(x["launchTime"], unit="ms")
        if t0 < LL.FIRST or base in TF or not (D / f"{sym}_1h.parquet").exists():
            continue
        k = pd.read_parquet(D / f"{sym}_1h.parquet"); k.index = pd.DatetimeIndex(k.index)
        if len(k) < 30 or k.loc[:k.index.min() + pd.Timedelta(hours=23), "quote_volume"].sum() < 1e7:
            continue
        if base in bt0 and abs((bt0[base] - k.index.min()).days) <= 7:
            continue
        fp = D / f"{sym}_funding.parquet"; f = pd.read_parquet(fp) if fp.exists() else pd.DataFrame({"time": [], "last_funding_rate": []})
        fs = pd.Series(f["last_funding_rate"].astype(float).to_numpy(), index=pd.to_datetime(f["time"]).dt.floor("h")).groupby(level=0).last()
        EVY.append(("BYBIT_" + sym, k.index.min(), k["close"], fs))
    cap, LL.CAP = LL.CAP, 1e9
    try:
        P = LL.positions(idx, EVY)
    finally:
        LL.CAP = cap
    P = P.T.groupby(level=0).min().T.reindex(idx).fillna(0.0); g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
    CF = {s[:-4]: (c, f) for s, t0, c, f in EVY}; out = pd.Series(0.0, index=idx)
    for n in P.columns:
        c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
        fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
        out = out + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
    return out, P, len(EVY)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, pos8, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum(); kf = lambda x: 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
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
    h, P, n = sleeve(idx); ref = full(CS.portfolio_v5(V8)[0] * kf(CS.portfolio_v5(V8)[0])); r = full(CS.portfolio_v5(V8.assign(**{"bybit listing short": h}))[0] * kf(CS.portfolio_v5(V8.assign(**{"bybit listing short": h}))[0]))
    hu, Pu = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx); gf = (hf != 0).astype(float) * 0.05
    ha, Pa = RB.venue(list(R34.events().items()), idx); hh, Ph = RB.venue(list(R42.events().items()), idx)
    HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
    ex = {"venue listing short": Pu.abs().sum(axis=1), "futures-delisting short": gf, "binance add short": Pa.abs().sum(axis=1), "hodler short": Ph.abs().sum(axis=1)}
    c0, u0 = capped(HC, ex); c1, u1 = capped(HC.assign(**{"bybit listing short": h}), {**ex, "bybit listing short": P.abs().sum(axis=1)})
    out = {"reference v9.8": ref, "Bybit-only / first events": n, "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
           "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "ALL + add + HODLer (uncapped / capped)": [u0, c0], "+ bybit listing sleeve (uncapped / capped)": [u1, c1]}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r46_bybit_listing_sleeve.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
