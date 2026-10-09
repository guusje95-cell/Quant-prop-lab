"""Gen32 (config/crypto_gen32_protocol.json): a-priori modifications of E2 LIQUID2, each judged vs its baseline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.data import crypto as CD, static_klines as SK  # noqa: E402
from qpl.research import factory as F  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402
from qpl.strategies import cft_e2 as E, crypto_zoo as Z  # noqa: E402

PROTO = "config/crypto_gen32_protocol.json"
COST = 7.5
PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-08")}
SQ = np.sqrt(365)


def sh(x):
    x = x.dropna(); return float(x.mean() / x.std() * SQ) if len(x) > 30 and x.std() > 0 else 0.0


def weights(sig, close, high, low, scale=1, range_vol=False):
    ann = np.sqrt(365 * scale)
    lr = np.log(close).diff()
    vol = lr.rolling(30 * scale, min_periods=20 * scale).std() * ann
    if range_vol:
        pk = np.sqrt((np.log(high / low) ** 2).rolling(30 * scale, min_periods=20 * scale).mean() / (4 * np.log(2))) * ann
        vol = np.maximum(vol, pk)
    hist = close.notna().cumsum() >= 200 * scale
    n = hist.sum(axis=1).replace(0, np.nan)
    return (sig * (0.40 / vol).clip(upper=1.0)).where(hist, 0.0).div(n, axis=0).fillna(0)


def engine_bars(w, close, high, low, scale=1, cmult=1.0):
    """Bar-level P&L aggregated to UTC days: net, worst/best intraday (vs equity at 00:00)."""
    ret = close.pct_change(fill_method=None).fillna(0)
    wp = w.shift(1).fillna(0)
    cost = wp.diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4
    lo_r, hi_r = (low / close.shift(1) - 1).fillna(0), (high / close.shift(1) - 1).fillna(0)
    r = (wp * ret).sum(axis=1) - cost
    wb = (wp.clip(lower=0) * lo_r + wp.clip(upper=0) * hi_r).sum(axis=1) - cost
    bb = (wp.clip(lower=0) * hi_r + wp.clip(upper=0) * lo_r).sum(axis=1) - cost
    day = r.index.floor("D")
    df = pd.DataFrame({"r": r, "wb": wb, "bb": bb, "cost": cost, "gross": (wp * ret).sum(axis=1), "day": day})
    out = []
    for d, g in df.groupby("day", sort=True):
        cum = np.concatenate([[1.0], np.cumprod(1 + g["r"].to_numpy())])
        worst = float(np.min(cum[:-1] * (1 + g["wb"].to_numpy())) - 1)
        best = float(np.max(cum[:-1] * (1 + g["bb"].to_numpy())) - 1)
        out.append((d, cum[-1] - 1, worst, best, g["cost"].sum(), float(np.prod(1 + g["gross"].to_numpy()) - 1)))
    o = pd.DataFrame(out, columns=["day", "net", "worst", "best", "cost", "gross"]).set_index("day")
    o.index = o.index.tz_localize(None) if o.index.tz is not None else o.index
    return o


def engine_daily(w, close, high, low, cmult=1.0):
    ret = close.pct_change(fill_method=None).fillna(0)
    wp = w.shift(1).fillna(0)
    cost = wp.diff().abs().sum(axis=1).fillna(0) * COST * cmult / 1e4
    lo_r, hi_r = (low / close.shift(1) - 1).fillna(0), (high / close.shift(1) - 1).fillna(0)
    gross = (wp * ret).sum(axis=1)
    return pd.DataFrame({"net": gross - cost, "gross": gross, "cost": cost,
                         "worst": (wp.clip(lower=0) * lo_r + wp.clip(upper=0) * hi_r).sum(axis=1) - cost,
                         "best": (wp.clip(lower=0) * hi_r + wp.clip(upper=0) * lo_r).sum(axis=1) - cost})


def period_stats(d):
    x = d["net"].loc["2018-01-01":"2026-10-08"]
    o = {p: round(sh(x.loc[a:z]), 3) for p, (a, z) in PER.items()}
    o["ALL"] = round(sh(x), 3); o["vol"] = round(float(x.std() * SQ), 4)
    o["worst_day"] = round(float(d["worst"].loc["2018":].min()), 4); o["tail_ratio"] = round(-o["worst_day"] / o["vol"], 3)
    o["turnover_cost_pa"] = round(float(d["cost"].loc["2018":].mean() * 365), 4)
    return o


def paired_p(mod, base, rng):
    a, b = mod["net"].loc["2018-01-01":"2026-10-08"], base["net"].loc["2018-01-01":"2026-10-08"]
    j = pd.concat([a, b], axis=1).dropna(); a, b = j.iloc[:, 0], j.iloc[:, 1]
    dlt = (a * (b.std() / a.std()) - b).to_numpy()
    idx = T.stationary_bootstrap_indices(len(dlt), 5000, 20.0, rng)
    boot = (dlt - dlt.mean())[idx].mean(axis=1)
    return float(np.mean(boot >= dlt.mean()))


rng = np.random.default_rng(32)
D = SK.load("1d"); MAJ = D["close"].loc["2017-08-17":"2026-10-08"]
c, h, l = (D[k].reindex_like(MAJ)[["BTC", "ETH"]] for k in ("close", "high", "low"))
out = {"mods": {}}

sig0 = E.signals(c)
B0 = engine_daily(weights(sig0, c, h, l), c, h, l)
out["B0"] = period_stats(B0)

# M1 range vol
M1 = engine_daily(weights(sig0, c, h, l, range_vol=True), c, h, l)
# M2 family ensemble
fam = {}
for a in c.columns:
    s = c[a].dropna(); ohlc = pd.DataFrame({"open": s, "high": h[a].reindex(s.index), "low": l[a].reindex(s.index), "close": s})
    bo = sum(Z.short_breakout(s, n, k) for n, k in E.BO) / len(E.BO); tm = sum(Z.tsmom(s, n) for n in E.TM) / len(E.TM)
    parts = [bo, tm, Z.sma_cross(s, 20, 100), Z.ema_cross(s, 21, 55), Z.donchian_close(s, 20), Z.donchian_close(s, 50),
             Z.macd(s, 12, 26, 9), Z.supertrend(ohlc, 10, 3.0), Z.price_above_sma(s, 100)]
    fam[a] = sum(p.clip(lower=0) for p in parts) / len(parts)
sig2 = pd.DataFrame(fam).reindex_like(c).fillna(0)
M2 = engine_daily(weights(sig2, c, h, l), c, h, l)
# M3 breadth from 10 majors
sig_all = E.signals(MAJ); have = MAJ.notna().cumsum() >= 200
breadth = ((sig_all > 0) & have).sum(axis=1) / have.sum(axis=1).replace(0, np.nan)
sig3 = sig0.mul(0.5 + 0.5 * breadth.fillna(0), axis=0)
M3 = engine_daily(weights(sig3, c, h, l), c, h, l)
# M4 4h BTC vs daily BTC (Bitstamp)
b4 = CD.btc_bars("4h"); b4.index = b4.index.tz_localize(None); b4 = b4.loc["2014-01-01":"2026-10-08 23:59"]
c4, h4, l4 = (b4[[k]].rename(columns={k: "BTC"}) for k in ("close", "high", "low"))
s4 = pd.DataFrame({"BTC": E.signal_one(c4["BTC"], scale=6)}).reindex_like(c4).fillna(0)
M4 = engine_bars(weights(s4, c4, h4, l4, scale=6), c4, h4, l4, scale=6)
b1 = CD.btc_bars("1D"); b1.index = b1.index.tz_localize(None); b1 = b1.loc["2014-01-01":"2026-10-08"]
c1, h1, l1 = (b1[[k]].rename(columns={k: "BTC"}) for k in ("close", "high", "low"))
B4 = engine_daily(weights(pd.DataFrame({"BTC": E.signal_one(c1["BTC"])}).reindex_like(c1).fillna(0), c1, h1, l1), c1, h1, l1)
out["B0_BTC_daily_bitstamp"] = period_stats(B4)
out["B4_extra_2015_2017"] = {"daily": round(sh(B4["net"].loc["2015":"2017"]), 3), "4h": round(sh(M4["net"].loc["2015":"2017"]), 3)}

pv = {}
for name, d, base in (("M1_RANGE_VOL", M1, B0), ("M2_FAMILY_ENSEMBLE", M2, B0), ("M3_BREADTH", M3, B0), ("M4_4H_BTC", M4, B4)):
    st, bs = period_stats(d), period_stats(base)
    pv[name] = paired_p(d, base, rng)
    out["mods"][name] = {"stats": st, "beats_each_period": bool(all(st[p] > bs[p] for p in PER)),
                         "tail_ok": bool(st["tail_ratio"] <= bs["tail_ratio"] * 1.10), "p_raw": round(pv[name], 4)}
order = sorted(pv, key=pv.get); run = 0.0
for i, k in enumerate(order):
    run = max(run, min(1.0, (len(order) - i) * pv[k])); out["mods"][k]["p_holm"] = round(run, 4)
for k, m in out["mods"].items():
    m["ACCEPTED"] = bool(m["beats_each_period"] and m["tail_ok"] and m["p_holm"] < 0.05)
acc = [k for k in ("M1_RANGE_VOL", "M2_FAMILY_ENSEMBLE", "M3_BREADTH") if out["mods"][k]["ACCEPTED"]]
if len(acc) == 3:
    M5 = engine_daily(weights(sig2.mul(0.5 + 0.5 * breadth.fillna(0), axis=0), c, h, l, range_vol=True), c, h, l)
    out["mods"]["M5_COMBO"] = {"stats": period_stats(M5)}
out["accepted"] = acc
for k, m in out["mods"].items():
    F.append({"kind": "dev_evaluation", "hypothesis_id": f"GEN32_{k}", "protocol": PROTO, "result": m})
(ROOT / "results/crypto_gen32_improve.json").write_text(json.dumps(out, indent=1, default=float))
pd.to_pickle({"B0": B0, "M1": M1, "M2": M2, "M3": M3, "M4": M4, "B4": B4}, ROOT / "results/crypto_gen32_series.pkl")
print(json.dumps(out, indent=1, default=float))
