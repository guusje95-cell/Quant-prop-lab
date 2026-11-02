"""v9.9 R48 (research/v99/r48_protocol.json, 0 trials): stress of the best candidate (R45 Bybit-filtered ALL + add + HODLer, 4.5% total
low-cap cap, risk 1.5): drop the best events, event bootstrap, later entries, higher costs. Each new sleeve is rebuilt as the sum of its
per-event trades (R16 A rules for Coinbase/Upbit, add, HODLer; R32 B rules for futures delistings) so events can be dropped / resampled.
Writes results/v99/r48_stress.json."""
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
import pit_universe as PU
import r16_coinbase as R16
import r22_upbit_r16rules as R22
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
NAMES = {"venue": "venue listing short", "fd": "futures-delisting short", "add": "binance add short", "hodler": "hodler short"}


def capped(H, extra):
    ph, W, M = CS.portfolio_v5(H); k = kf(ph); m = M.reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    w = lambda c: W[c].reindex(idx.floor("D")).set_axis(idx).ffill().fillna(0.0)
    g = pos8.abs().sum(axis=1).reindex(idx).fillna(0.0) * w("listing short") * m * k * RISK
    for c, gr in extra.items():
        g = g + gr * w(c) * m * k * RISK
    kk = (0.045 / g).clip(upper=1.0).fillna(1.0).shift(1).fillna(1.0); H2 = H.copy(); H2["listing short"] *= kk
    for c in extra:
        H2[c] = H2[c] * kk
    return full(CS.portfolio_v5(H2)[0] * k)


def r16_event(coin, T, delay, cost):
    """(pnl, |position|) of one R16 A trade, entry delayed by `delay` hours"""
    R16.COST = cost
    h, u = R16.trades({coin: T + pd.Timedelta(hours=delay)}, idx, "A")
    return (h, (h != 0).astype(float) * R16.SIZE) if u else None


def fd_event(coin, t, delay, cost, hold=14):
    """one R32 B futures-delisting trade (same code as R32.sleeve for a single event, cost per side as a parameter)"""
    if coin in PU.TF:
        return None
    cl, fu = EL._closes(coin)
    if cl is None:
        return None
    start = t.ceil("h") + pd.Timedelta(hours=1 + delay); end = start + pd.Timedelta(days=hold)
    if not ((cl.index >= t.floor("h") - pd.Timedelta(hours=2)) & (cl.index <= t.ceil("h"))).any():
        return None
    cc = cl.loc[start:end]
    if len(cc) == 0:
        return None
    hit = cc[cc >= cc.iloc[0] * 1.30].index; last = hit[0] if len(hit) else min(end, cl.index.max())
    p = pd.Series(-0.05, index=cl.loc[start:last].index); p.index = p.index + pd.Timedelta(hours=1); p = p.reindex(idx).fillna(0.0)
    p = p.where(cl.reindex(idx - pd.Timedelta(hours=1)).notna().to_numpy(), 0.0)
    r = (cl / cl.shift(1) - 1).reindex(idx).fillna(0.0)
    f = fu.copy() if fu is not None else pd.Series(dtype=float)
    if len(f):
        f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(idx).fillna(0.0)
    else:
        f = pd.Series(0.0, index=idx)
    h = p * r - p * f - p.diff().abs().fillna(p.abs()) * cost
    return h, p.abs()


FL = EL.firm_launch()
on_bybit = lambda c, t: (FL.get(EL._norm(c)) is not None) and FL[EL._norm(c)] <= t + pd.Timedelta(hours=2)
SRC = {"venue": list(R16.events().items()) + list(R22.upbit_events().items()), "add": list(R34.events().items()), "hodler": list(R42.events().items()),
       "fd": R32.events()["futures delisting"]}
SRC = {k: sorted([x for x in v if on_bybit(*x)], key=lambda x: x[1]) for k, v in SRC.items()}


def per_event(delay=0, cost=1e-3):
    """{sleeve: [(coin, T, pnl, gross)]} after the one-trade-per-coin-per-7-days rule (R30b venue(); the fd sleeve keeps R32's own overlap rule)"""
    out = {}
    for k, ev in SRC.items():
        L, last = [], {}
        for coin, T in ev:
            if k != "fd" and coin in last and T - last[coin] < pd.Timedelta(days=7):
                continue
            x = fd_event(coin, T, delay, cost) if k == "fd" else r16_event(coin, T, delay, cost)
            if x is None:
                continue
            last[coin] = T; L.append((coin, T, x[0], x[1]))
        out[k] = L
    return out


def book(E, mult=None):
    H = V8.copy(); ex = {}
    for k, L in E.items():
        m = np.ones(len(L)) if mult is None else mult[k]
        s = pd.Series(0.0, index=idx); g = pd.Series(0.0, index=idx)
        for (_, _, h, gr), mm in zip(L, m):
            if mm:
                s = s + mm * h; g = g + mm * gr
        H[NAMES[k]] = s; ex[NAMES[k]] = g
    return capped(H, ex)


def main():
    out = {"v9.8 capped": capped(V8, {})}; ref = out["v9.8 capped"]
    beats = lambda r: bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))
    E = per_event(); out["events per sleeve"] = {k: len(L) for k, L in E.items()}
    out["base (additive rebuild of R45 capped 3.550)"] = book(E); print(out, flush=True)
    ret = {k: np.array([h.sum() for _, _, h, _ in L]) for k, L in E.items()}
    out["share of sleeve P&L from its best 10% events"] = {k: round(float(np.sort(r)[::-1][:max(1, int(round(0.1 * len(r))))].sum() / r.sum()), 3) for k, r in ret.items()}
    for q in (0.05, 0.10):
        mult = {}
        for k, r in ret.items():
            n = max(1, int(round(q * len(r)))); m = np.ones(len(r)); m[np.argsort(r)[::-1][:n]] = 0; mult[k] = m
        b = book(E, mult); out[f"S1 drop best {int(q * 100)}% events"] = {"book": b, "beats v9.8 capped +0.05, no period lower": beats(b)}; print(out[f"S1 drop best {int(q * 100)}% events"], flush=True)
    for d in (1, 3, 6):
        b = book(per_event(delay=d)); out[f"S3 entry +{d} h"] = {"book": b, "beats": beats(b)}; print(d, b, flush=True)
    for c in (2e-3, 3e-3):
        b = book(per_event(cost=c)); out[f"S4 cost {int(c * 1e4)} bp/side"] = {"book": b, "beats": beats(b)}; print(c, b, flush=True)
    R16.COST = 1e-3
    rng = np.random.default_rng(48); gains = []; per = []
    for i in range(200):
        mult = {k: np.bincount(rng.integers(0, len(L), len(L)), minlength=len(L)).astype(float) for k, L in E.items()}
        b = book(E, mult); gains.append(b[0] - ref[0]); per.append([b[1][j] - ref[1][j] for j in range(3)])
        if i % 20 == 0:
            print("boot", i, round(float(np.mean(gains)), 3), flush=True)
    g = np.array(gains); P = np.array(per)
    out["S2 event bootstrap (200)"] = {"gain vs v9.8 capped: mean / p5 / p50 / p95": [round(float(x), 3) for x in (g.mean(), *np.percentile(g, [5, 50, 95]))],
                                      "P(gain <= 0)": round(float((g <= 0).mean()), 3),
                                      "P(any period lower than v9.8)": round(float((P < 0).any(axis=1).mean()), 3),
                                      "per-period gain p5": [round(float(x), 3) for x in np.percentile(P, 5, axis=0)]}
    out["judge"] = {"S1 drop 10%": out["S1 drop best 10% events"]["beats v9.8 capped +0.05, no period lower"],
                    "S2 P(gain<=0) < 5%": out["S2 event bootstrap (200)"]["P(gain <= 0)"] < 0.05,
                    "S3 +3 h >= v9.8 + 0.05": out["S3 entry +3 h"]["book"][0] >= ref[0] + 0.05,
                    "S4 2x cost >= v9.8 + 0.05": out["S4 cost 20 bp/side"]["book"][0] >= ref[0] + 0.05}
    print(json.dumps(out, indent=1, default=str)); (ROOT / "results/v99/r48_stress.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
