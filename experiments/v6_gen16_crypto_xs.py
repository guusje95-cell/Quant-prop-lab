"""V6 gen16: crypto cross-sectional and on-chain factors on Coin Metrics community data. Protocol config/v6_gen16_protocol.json
(committed 5373c4f before any return was computed). Stage gates applied in code."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import factory as F, v6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/v6_gen16_protocol.json"
PR = v6.protocol("v6_gen16_protocol.json"); PER = PR["periods"]
SRC = ROOT / "data/raw/ext/coinmetrics-data/csv"
STABLE_WRAPPED = {"usdt", "usdc", "dai", "busd", "tusd", "pax", "husd", "usdk", "sai", "frax", "fdusd", "usde", "usdd", "eurc", "gusd", "paxg",
                  "xaut", "buidl", "renbtc", "wbtc", "hbtc", "wnxm", "pyusd", "usdp", "lusd", "usd1", "rlusd", "susde", "steth", "weth"}
cols = ["time", "PriceUSD", "CapMrktCurUSD", "CapMVRVCur", "AdrActCnt", "volume_reported_spot_usd_1d"]
data = {}
for f in sorted(SRC.glob("*.csv")):
    a = f.stem
    if "_" in a or a in STABLE_WRAPPED:
        continue
    d = pd.read_csv(f, usecols=lambda c: c in cols)
    if "PriceUSD" not in d or d.PriceUSD.notna().sum() < 90:
        continue
    d["time"] = pd.to_datetime(d.time); data[a] = d.set_index("time")
panel = {c: pd.DataFrame({a: d[c] for a, d in data.items() if c in d}) for c in cols[1:]}
px, cap = panel["PriceUSD"].sort_index(), panel["CapMrktCurUSD"].reindex_like(panel["PriceUSD"])
px = px.loc["2013-01-01":"2026-05-24"]; cap = cap.loc[px.index]
vol = panel["volume_reported_spot_usd_1d"].reindex_like(px)
mvrv = panel["CapMVRVCur"].reindex_like(px); adr = panel["AdrActCnt"].reindex_like(px)
print("assets", px.shape[1])
# point-in-time universe at each Wednesday
reb = px.index[px.index.dayofweek == 2]
hist = px.notna().cumsum() >= 90
vmed = vol.rolling(30, min_periods=10).median()


def universe(t):
    ok = hist.loc[t] & cap.loc[t].notna() & px.loc[t].notna()
    v = vmed.loc[t]
    ok &= (v.isna() | (v >= 1e6))
    c = cap.loc[t][ok].sort_values(ascending=False)
    return list(c.index[:30])


UNI = {t: universe(t) for t in reb}


def run(score: pd.DataFrame, cost_bps=30.0, min_n=9) -> pd.DataFrame:
    rows = []; w_old = pd.Series(dtype=float)
    for t in reb:
        i = px.index.get_loc(t)
        if i + 8 >= len(px):
            break
        u = [a for a in UNI[t] if a in score.columns and np.isfinite(score.loc[t, a])]
        if len(u) < min_n:
            w = pd.Series(dtype=float)
        else:
            s = score.loc[t, u].rank(pct=True)
            lo, hi = s[s <= 1 / 3].index, s[s > 2 / 3].index
            w = pd.concat([pd.Series(1 / len(hi), index=hi), pd.Series(-1 / len(lo), index=lo)])
        p1, p8 = px.iloc[i + 1], px.iloc[i + 8]
        r = (p8.reindex(w.index).fillna(px.iloc[i + 1:i + 9].ffill().iloc[-1].reindex(w.index)) / p1.reindex(w.index) - 1).fillna(0) if len(w) else pd.Series(dtype=float)
        turn = (w.reindex(w.index.union(w_old.index)).fillna(0) - w_old.reindex(w.index.union(w_old.index)).fillna(0)).abs().sum()
        gross = float((w * r).sum()) if len(w) else 0.0
        rows.append({"t": px.index[i + 1], "gross": gross, "cost": turn * cost_bps / 1e4, "net": gross - turn * cost_bps / 1e4, "n": len(w), "turn": turn})
        w_old = w
    return pd.DataFrame(rows).set_index("t")


def sh(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(52)) if len(x) > 10 and x.std() > 0 else 0.0


def per(d, k, col="net"):
    a, z = PER[k]
    return d.loc[a:z, col]


lr = np.log(px)
SIGS = {
    "H16a_XS_MOM": ({"L21": lr - lr.shift(21)}, {"L7": lr - lr.shift(7), "L63": lr - lr.shift(63)}),
    "H16b_XS_REV": ({"L7": -(lr - lr.shift(7))}, {"L3": -(lr - lr.shift(3)), "L14": -(lr - lr.shift(14))}),
    "H16c_XS_MVRV": ({"logmvrv": -np.log(mvrv.where(mvrv > 0))},
                     {"z365": -((np.log(mvrv.where(mvrv > 0)) - np.log(mvrv.where(mvrv > 0)).rolling(365, min_periods=180).mean())
                                / np.log(mvrv.where(mvrv > 0)).rolling(365, min_periods=180).std())}),
    "H16d_XS_NETGROWTH": ({"g28": np.log(adr.rolling(7).mean()).diff(28)}, {"g91": np.log(adr.rolling(7).mean()).diff(91)}),
}
out = {}
for hid, (prim, neigh) in SIGS.items():
    h = F.Hypothesis(hid, "crypto/cross-section", PR["hypotheses"][hid]["signal"], PR["hypotheses"][hid]["source"], PR["gates"]["TRAIN"],
                     "Coin Metrics community", json.dumps(list(neigh)), "zero (dollar neutral)", PROTO, generation=16)
    h.register()
    (pk, ps), = prim.items()
    d = run(ps); d60 = run(ps, 60.0)
    r = {"TRAIN": {"net": sh(per(d, "TRAIN")), "gross": sh(per(d, "TRAIN", "gross")), "avg_n": float(per(d, "TRAIN", "n").mean()),
                   "turn_wk": float(per(d, "TRAIN", "turn").mean())}, "neighbours": {}}
    for nk, ns in neigh.items():
        r["neighbours"][nk] = sh(per(run(ns), "TRAIN"))
    r["train_pass"] = bool(r["TRAIN"]["net"] >= 0.5 and np.mean([v > 0 for v in r["neighbours"].values()]) >= 2 / 3)
    v6.record(hid, h.family, pk, {}, "TRAIN", r["TRAIN"] | {"neighbours": r["neighbours"]}, 16, PROTO, "crypto XS")
    if r["train_pass"]:
        r["VALIDATION"] = {"net": sh(per(d, "VALIDATION")), "gross": sh(per(d, "VALIDATION", "gross"))}
        r["val_pass"] = r["VALIDATION"]["net"] >= 0.3
        v6.record(hid, h.family, pk, {}, "VALIDATION", r["VALIDATION"], 16, PROTO, "crypto XS")
        if r["val_pass"]:
            r["TEST"] = {"net": sh(per(d, "TEST")), "net60": sh(per(d60, "TEST")), "gross": sh(per(d, "TEST", "gross"))}
            r["test_pass"] = r["TEST"]["net"] > 0 and r["TEST"]["net60"] > 0
            v6.record(hid, h.family, pk, {}, "TEST_LOOK", r["TEST"], 16, PROTO, "crypto XS")
    r["by_year_net"] = {int(y): round(float(v), 3) for y, v in d["net"].groupby(d.index.year).sum().items()}
    v = "REJECTED" if not r["train_pass"] else ("EXPLORATORY" if not r.get("val_pass") else "PROMISING_BUT_UNVALIDATED")
    r["verdict"] = v
    F.decide(h, v, json.dumps({k: r[k] for k in ("TRAIN", "VALIDATION", "TEST") if k in r}), {"protocol": PROTO})
    out[hid] = r
    print(hid, json.dumps({k: r[k] for k in r if k != "by_year_net"}))

# H16e BTC MVRV timing (time series, daily)
h = F.Hypothesis("H16e_BTC_MVRV_TIMING", "crypto/on-chain valuation", PR["hypotheses"]["H16e_BTC_MVRV_TIMING"]["signal"], "MVRV mean reversion",
                 PR["gates"]["H16e"], "Coin Metrics btc", "scale variant", "BTC buy&hold", PROTO, generation=16)
h.register()
bp = px["btc"].dropna(); m = mvrv["btc"].reindex(bp.index)
med = m.rolling(1460, min_periods=730).median()
pos = {"binary": (m < med).astype(float).where(med.notna()), "scaled": (2 - m / med).clip(0, 1).where(med.notna())}
r1 = bp.pct_change().shift(-2)                                       # decided at t, held over day t+2 (one-day lag)
res = {}
for k, w in pos.items():
    turn = w.diff().abs().fillna(0)
    net = (w * r1 - turn * 15e-4).dropna()
    bh = r1.reindex(net.index)
    for pk, (a, z) in {"TRAIN": ("2013-01-01", "2019-12-31"), "VALIDATION": ("2020-01-01", "2021-12-31"), "OOS": ("2022-01-01", "2023-12-31"),
                       "USED_2024_26": ("2024-01-01", "2026-05-22")}.items():
        x, y = net.loc[a:z], bh.loc[a:z]
        b = np.cov(x, y)[0, 1] / y.var()
        res.setdefault(k, {})[pk] = {"sharpe": float(x.mean() / x.std() * np.sqrt(365)), "resid": float((x - b * y).mean() / (x - b * y).std() * np.sqrt(365)),
                                    "bh": float(y.mean() / y.std() * np.sqrt(365)), "share_invested": float(w.loc[a:z].mean())}
t, vv, o = res["binary"]["TRAIN"], res["binary"]["VALIDATION"], res["binary"]["OOS"]
passed = t["sharpe"] >= 0.5 and t["resid"] >= 0.3 and vv["sharpe"] >= 0.3 and vv["resid"] > 0 and o["sharpe"] >= 0.3 and o["resid"] > 0
res["verdict"] = "PROMISING_BUT_UNVALIDATED" if passed else ("REJECTED" if t["sharpe"] < 0.5 or t["resid"] < 0.3 else "EXPLORATORY")
v6.record("H16e_BTC_MVRV_TIMING", h.family, "binary", {}, "TRAIN/VAL/OOS", res["binary"], 16, PROTO, "BTC")
F.decide(h, res["verdict"], json.dumps(res["binary"])[:400], {"protocol": PROTO})
out["H16e_BTC_MVRV_TIMING"] = res
(ROOT / "results/v6_gen16_crypto_xs.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(res, indent=1))
for k, v in out.items():
    if "by_year_net" in v:
        print(k, v["by_year_net"])
