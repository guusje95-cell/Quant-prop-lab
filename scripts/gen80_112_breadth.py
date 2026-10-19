"""Gen80 (premium carry breadth) and Gen112 (deleveraging bounce breadth) on the 20-coin pack + research_data/binance_extra.
Frozen rules, no re-tuning. Writes results/gen80_112.csv and results/gen112_hits.csv. The cascade part of Gen80 needs a 1-hour
replica of the 5-minute fill rule and is run separately."""
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
EXTRA = Path(os.environ.get("QPL_EXTRA", ROOT / "research_data" / "binance_extra"))
g = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}
exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], g)
CS, B, H6, B0, k0, per, sh, cst = (g[k] for k in ("CS", "B", "H6", "B0", "k0", "per", "sh", "cst"))
END = "2026-09-30 23:00"; DAYS = pd.date_range("2020-01-01", "2026-09-30")
PACK = B.coins(); XS = sorted(p.stem.replace("USDT_1h", "") for p in EXTRA.glob("*USDT_1h.parquet"))
print(len(PACK), "pack coins,", len(XS), "extra coins", flush=True)


def x_close(c):
    d = pd.read_parquet(EXTRA / f"{c}USDT_1h.parquet")
    if "time" in d:
        d = d.set_index("time")
    return d["close"].astype(float).sort_index().loc[:END]


def x_vol(c):
    d = pd.read_parquet(EXTRA / f"{c}USDT_1h.parquet")
    if "time" in d:
        d = d.set_index("time")
    return d["quote_volume"].astype(float).sort_index().loc[:END]


def x_prem(c):
    d = pd.read_parquet(EXTRA / f"{c}USDT_premium_1h.parquet"); d["time"] = pd.to_datetime(d["time"])
    return d.drop_duplicates("time").set_index("time")["close"].astype(float).sort_index().loc[:END]


def x_fund(c):
    d = pd.read_parquet(EXTRA / f"{c}USDT_funding.parquet"); t = pd.to_datetime(d["time"]).dt.round("h")
    return pd.Series(d["last_funding_rate"].astype(float).to_numpy(), index=t).groupby(level=0).last().sort_index()


def x_oi(c):
    f = EXTRA / f"{c}USDT_oi_1h.parquet"
    if not f.exists():
        return None
    s = pd.read_parquet(f)["oi_value"].astype(float); s.index = pd.to_datetime(s.index)
    return s.where(s > 0).sort_index().loc[:END]


HCP = CS._hourly_close(PACK)
HC = pd.concat([HCP] + [x_close(c).rename(c) for c in XS], axis=1).sort_index().loc[:END]
FP = B.funding_panel(PACK)
FA = pd.concat([FP] + [x_fund(c).rename(c) for c in XS], axis=1).sort_index()


def perp_daily(w, coins, cost=5):
    """Same accounting as CS._from_daily_weights on the merged universe."""
    H = HC[coins]; r = H.pct_change(fill_method=None).fillna(0.0)
    w = w.reindex(w.index.append(pd.DatetimeIndex([w.index[-1] + pd.Timedelta(days=1)])))
    hd = w.reindex(columns=coins).shift(1)
    held = hd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0)
    turn = hd.fillna(0.0).diff().abs().sum(axis=1).reindex(H.index.floor("D")).set_axis(H.index).where(H.index.hour == 0, 0.0)
    f = FA[coins].copy(); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(H.index).fillna(0.0)
    return (held * r).sum(axis=1) - (held * f).sum(axis=1) - turn.fillna(0.0) * cost / 1e4


rows = []


def book(name, hp, base_col=None, add=False, ref=None):
    H = H6.copy()
    if base_col and not add:
        H[base_col] = hp.reindex(H.index).fillna(0.0)
    else:
        H[name] = hp.reindex(H.index).fillna(0.0)
    v = CS.portfolio_v5(H.fillna(0.0))[0]; k1 = per(v, "2022-01-01"); p = per(hp, "2020-01-01")
    r = {"test": name, "DEV/TEST/HOLD": np.round(p, 3).tolist(), "2023-26": round(sh(hp, "2023-01-01", "2026-09-30"), 3),
         "corr C*": round(float(pd.concat([cst, hp.groupby(hp.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1]), 3),
         "v6 before/after": [round(B0, 3), round(sh(v, "2022-01-01", "2026-09-30"), 3)], "v6 TEST/HOLD before/after": [np.round(k0[1:], 3).tolist(), np.round(k1[1:], 3).tolist()]}
    if ref is not None:
        r["pass (Gen80 rule)"] = bool(r["2023-26"] >= ref["2023-26"] and p[2] >= ref["DEV/TEST/HOLD"][2] and r["v6 before/after"][1] > B0)
    else:
        r["pass (crypto rule)"] = bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and r["corr C*"] <= 0.3 and r["v6 before/after"][1] > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])
    rows.append(r); print(r, flush=True); return r


# ---- Gen80: premium carry on 20 vs 20+extra coins (frozen Gen61 rule)
def prem_w(coins, look=7, hold=7):
    P = HC[coins].resample("1D").last()
    prem = pd.DataFrame({c: (B.premium(c)["close"] if c in PACK else x_prem(c)).resample("1D").mean() for c in coins}).reindex(P.index).rolling(look).mean()
    listed = P.notna().cumsum() >= 60
    rk = (-prem).where(listed).rank(axis=1, pct=True)
    w = (rk > 2 / 3).astype(float).div((rk > 2 / 3).sum(axis=1), axis=0) - (rk <= 1 / 3).astype(float).div((rk <= 1 / 3).sum(axis=1), axis=0)
    return w.where(pd.Series(np.arange(len(w)) % hold == 0, index=w.index), np.nan).ffill().fillna(0.0)


ref = book("premium carry, 20 coins (current)", perp_daily(prem_w(PACK), PACK), base_col="premium carry")
ALL = PACK + XS
book("premium carry, 20 + extra coins", perp_daily(prem_w(ALL), ALL), base_col="premium carry", ref=ref)
liq = pd.Series({c: x_vol(c).resample("1D").sum().median() for c in XS})
thin = list(liq[liq < 20e6].index); print("extra coins below $20m median daily volume:", thin, flush=True)
book("premium carry, 20 + extra coins >= $20m/day", perp_daily(prem_w(PACK + [c for c in XS if c not in thin]), PACK + [c for c in XS if c not in thin]),
     base_col="premium carry", ref=ref)

# ---- Gen112: deleveraging bounce (H4 rule unchanged) on all non-BTC/ETH coins
ALTS = [c for c in PACK if c not in ("BTC", "ETH")] + XS
sig = pd.DataFrame(0.0, index=pd.date_range("2021-12-01", "2026-09-30"), columns=ALTS); hits = []
for c in ALTS:
    if c in PACK:
        m = B.metrics(c)["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1h").last().ffill(); px = HC[c]
    else:
        m = x_oi(c); px = HC[c]
        if m is None:
            continue
        m = m.resample("1h").last().ffill()
    t = sig.index + pd.Timedelta(days=1) - pd.Timedelta(minutes=5)
    f = lambda s, tt: s.reindex(tt.floor("h"), method="ffill").to_numpy()
    s = pd.Series((f(m, t) / f(m, t - pd.Timedelta(days=1)) - 1 < -0.10) & (f(px, t) < f(px, t - pd.Timedelta(days=1))), index=sig.index)
    listed = px.resample("1D").last().notna().cumsum().reindex(sig.index).fillna(0) >= 60
    sig[c] = (s & listed).astype(float)
    nd = px.resample("1D").last()
    for d in sig.index[sig[c] > 0]:                                 # G2: 2-day forward return from 00:00 d+1
        a, b = nd.get(d), nd.get(d + pd.Timedelta(days=2))
        if a and b and np.isfinite(a) and np.isfinite(b):
            hits.append({"coin": c, "extra": c in XS, "day": d, "ret2d": b / a - 1})
held = sig.rolling(2, min_periods=1).max()
elig = pd.DataFrame({c: HC[c].resample("1D").last().notna().cumsum() for c in ALTS}).reindex(sig.index).fillna(0).ge(60).sum(axis=1).clip(lower=1)
w = held.mul(0.5 * 2 / elig, axis=0)
book("G1 bounce on all altcoins (pack alts + extra)", perp_daily(w.reindex(DAYS).fillna(0.0), ALTS), add=True)
hd = pd.DataFrame(hits)
if len(hd):
    tab = hd.groupby(["extra", "coin"]).ret2d.agg(episodes="size", mean="mean", share_pos=lambda x: (x > 0).mean()).round(4)
    tab.to_csv(ROOT / "results/gen112_hits.csv")
    print(hd.groupby("extra").ret2d.agg(["size", "mean", lambda x: (x > 0).mean()]), flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen80_112.csv", index=False)
