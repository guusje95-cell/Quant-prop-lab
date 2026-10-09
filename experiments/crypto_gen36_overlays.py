"""Gen36 (config/crypto_gen36_protocol.json): a-priori overlays on frozen E2 LIQUID2 from on-chain / liquidity / macro data."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "experiments/crypto_gen32_improve.py").read_text().split("rng = np.random.default_rng(32)")[0]
G = {"__name__": "g32", "__file__": str(ROOT / "experiments/crypto_gen32_improve.py")}
exec(compile(src, "g32", "exec"), G)
E, SK, F, T = G["E"], G["SK"], G["F"], G["T"]
weights, engine_daily, period_stats, paired_p, sh, SQ = (G[k] for k in ("weights", "engine_daily", "period_stats", "paired_p", "sh", "SQ"))
from qpl.data import coinmetrics as CM, macro_daily as MD  # noqa: E402

PROTO = "config/crypto_gen36_protocol.json"
PER = {"DEV": ("2018-01-01", "2021-12-31"), "VAL": ("2022-01-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-05-24")}
G["PER"].clear(); G["PER"].update(PER)                     # period_stats uses these periods

D = SK.load("1d"); c = D["close"].loc["2017-08-17":"2026-05-24", ["BTC", "ETH"]]
h, l = D["high"].reindex_like(c), D["low"].reindex_like(c)
cal = c.index


def cm(asset, cols):
    d = pd.read_csv(CM.SRC / f"{asset}.csv", usecols=lambda x: x in ["time"] + cols, parse_dates=["time"]).set_index("time")
    return d.reindex(cal)


oc = {a: cm(a.lower(), ["CapMVRVCur", "FlowInExUSD", "FlowOutExUSD", "CapMrktCurUSD", "AdrActCnt", "HashRate", "SplyExNtv"]) for a in ("BTC", "ETH")}
stab = sum(cm(s, ["CapMrktCurUSD"])["CapMrktCurUSD"].fillna(0) for s in ("usdt", "usdc"))
MAC = MD.load().reindex(pd.date_range("2015-01-01", "2026-05-24")).ffill(limit=4).reindex(cal)


def per_coin(fn):
    return pd.DataFrame({a: fn(oc[a]) for a in ("BTC", "ETH")}, index=cal)


def both(s):
    return pd.DataFrame({"BTC": s, "ETH": s}, index=cal)


O = {}
O["O1_MVRV"] = per_coin(lambda d: (1 - 0.75 * ((d.CapMVRVCur - 2.0) / 1.5).clip(0, 1)).where(d.CapMVRVCur.notna(), 1.0))
def _nf(d):
    x = ((d.FlowInExUSD - d.FlowOutExUSD).rolling(7).sum() / d.CapMrktCurUSD)
    z = (x - x.rolling(365, min_periods=180).mean()) / x.rolling(365, min_periods=180).std()
    return pd.Series(np.where(z > 1.5, 0.5, 1.0), index=cal)
O["O2_EXCH_NETFLOW"] = per_coin(_nf)
g = np.log(stab.replace(0, np.nan)).diff(30)
O["O3_STABLE_LIQUIDITY"] = both(pd.Series(np.where(g > 0, 1.25, np.where(g <= 0, 0.75, 1.0)), index=cal))
O["O4_ACTIVE_ADDR"] = per_coin(lambda d: pd.Series(np.where(d.AdrActCnt.rolling(30).mean() > d.AdrActCnt.rolling(90).mean(), 1.25,
                                                            np.where(d.AdrActCnt.rolling(90).mean().notna(), 0.75, 1.0)), index=cal))
hr = oc["BTC"].HashRate
O["O5_HASH_RIBBON"] = both(pd.Series(np.where(hr.rolling(30).mean() < hr.rolling(60).mean(), 0.75, 1.0), index=cal))
O["O6_VIX"] = both(pd.Series(np.where(MAC["VIX"] > 30, 0.5, 1.0), index=cal))
usd = pd.concat([np.log(MAC[k]) * (1 if k.startswith("USD") else -1) for k in ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCAD", "USDCHF")], axis=1).mean(axis=1)
du = usd.diff(50)
O["O7_DOLLAR_TREND"] = both(pd.Series(np.where(du > 0, 0.75, np.where(du <= 0, 1.25, 1.0)), index=cal))
spx = MAC["SPX"]; ma = spx.rolling(100, min_periods=80).mean()
O["O8_SPX_TREND"] = both(pd.Series(np.where(spx.isna() | ma.isna(), 1.0, np.where(spx > ma, 1.25, 0.75)), index=cal))
O["O9_EXCH_SUPPLY"] = per_coin(lambda d: pd.Series(np.where(d.SplyExNtv.diff(30) < 0, 1.25, np.where(d.SplyExNtv.diff(30).notna(), 0.75, 1.0)), index=cal))

sig0 = E.signals(c)
B0 = engine_daily(weights(sig0, c, h, l), c, h, l)
rng = np.random.default_rng(36)
out = {"base": period_stats(B0), "overlays": {}}
series = {"B0": B0}
pv = {}
for k, f in O.items():
    f = f.shift(1).fillna(1.0)                                 # 1-day publication lag
    d = engine_daily(weights(sig0 * f, c, h, l), c, h, l)
    series[k] = d
    kk = B0["net"].loc["2018":].std() / d["net"].loc["2018":].std(); dd = d * kk
    st, bs = period_stats(dd), period_stats(B0)
    pv[k] = paired_p(dd, B0, rng)
    out["overlays"][k] = {"stats": st, "beats_each_period": bool(all(st[p] > bs[p] for p in PER)),
                          "tail_ok": bool(st["tail_ratio"] <= bs["tail_ratio"] * 1.10), "p_raw": round(pv[k], 4),
                          "share_f_ne_1": round(float((f.loc["2018":] != 1).mean().mean()), 3)}
# Benjamini-Hochberg
order = sorted(pv, key=pv.get); m = len(order); bh = {}
prev = 1.0
for i in range(m - 1, -1, -1):
    k = order[i]; prev = min(prev, pv[k] * m / (i + 1)); bh[k] = prev
for k, o in out["overlays"].items():
    o["q_bh"] = round(bh[k], 4); o["ACCEPTED"] = bool(o["beats_each_period"] and o["tail_ok"] and bh[k] < 0.10)
    F.append({"kind": "dev_evaluation", "hypothesis_id": f"GEN36_{k}", "protocol": PROTO, "result": o})
acc = [k for k, o in out["overlays"].items() if o["ACCEPTED"]]
out["accepted"] = acc
if len(acc) >= 2:
    f = np.prod([O[k].shift(1).fillna(1.0) for k in acc], axis=0)
    d = engine_daily(weights(sig0 * pd.DataFrame(f, index=cal, columns=c.columns), c, h, l), c, h, l)
    kk = B0["net"].loc["2018":].std() / d["net"].loc["2018":].std()
    out["combo"] = period_stats(d * kk); series["COMBO"] = d
(ROOT / "results/crypto_gen36_overlays.json").write_text(json.dumps(out, indent=1, default=float))
pd.to_pickle(series, ROOT / "results/crypto_gen36_series.pkl")
print(json.dumps(out, indent=1, default=float))
