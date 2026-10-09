"""Track C gen21: rolling-hedge pairs stat-arb on Dukascopy daily (protocol config/statarb_protocol.json)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl import instruments as INS
from qpl.research import factory as F, v6
PROTO = "config/statarb_protocol.json"; PR = json.loads(Path(PROTO).read_text()); PER = PR["periods"]
def px(sym):
    inv = sym.endswith("_inv"); s = sym.replace("_inv", "")
    c = pd.read_parquet(f"data/processed/dukascopy/{s}_D1.parquet")["close"]
    c.index = c.index.tz_convert("UTC").normalize()
    c = c[~c.index.duplicated(keep="last")]
    cost = INS.SPOT_COST_PRICE_UNITS[s] / c                    # fraction of notional per unit turnover (round trip proxy)
    return (1 / c if inv else c), cost
def pair_pnl(a, b, form=252, entry=2.0, exit_=0.5, stop=4.0, maxd=20, cmult=1.0):
    pa, ca = px(a); pb, cb = px(b)
    df = pd.concat({"a": np.log(pa), "b": np.log(pb), "ca": ca, "cb": cb}, axis=1).dropna()
    la, lb = df.a, df.b
    cov = la.rolling(form).cov(lb); var = lb.rolling(form).var()
    beta = (cov / var)
    spread = la - beta * lb
    z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
    ra, rb = la.diff(), lb.diff()
    sret = ra - beta.shift(1) * rb                               # spread return held from t-1 to t
    vol = sret.rolling(60).std()
    pos = np.zeros(len(df)); cur = 0.0; age = 0
    zv = z.to_numpy()
    for t in range(len(df)):
        if not np.isfinite(zv[t]): cur = 0.0
        elif cur == 0:
            if zv[t] > entry: cur, age = -1.0, 0
            elif zv[t] < -entry: cur, age = 1.0, 0
        else:
            age += 1
            if abs(zv[t]) < exit_ or abs(zv[t]) > stop or age >= maxd or np.sign(zv[t]) == np.sign(cur) * 1 and False: cur = 0.0
        pos[t] = cur
    size = pd.Series(pos, index=df.index) / vol                 # risk-normalised units
    held = size.shift(2).fillna(0)                               # decided at close t, held from close t+1 -> earns t+2
    bet = beta.shift(2)
    gross = held * (ra - bet * rb)
    dpos = size.shift(1).diff().abs().fillna(0)
    cost = dpos * (df.ca + beta.abs() * df.cb) * cmult
    out = pd.DataFrame({"gross": gross, "net": gross - cost, "trade": (size.shift(1).fillna(0) != 0) & (size.shift(2).fillna(0) == 0)}).dropna()
    return out
def sharpe(x): x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else 0.0
def stage(per, cmult=1.0, **kw):
    pn = {k: pair_pnl(*v, cmult=cmult, **kw) for k, v in PR["pairs"].items()}
    a, z = PER[per]
    P = pd.DataFrame({k: v.loc[a:z, "net"] for k, v in pn.items()}).fillna(0)
    G = pd.DataFrame({k: v.loc[a:z, "gross"] for k, v in pn.items()}).fillna(0)
    P = P / P.std(); G = G / P.std().replace(0, 1)                # equal risk per pair (ex-post scale, Sharpe-neutral per pair)
    tot = P.mean(axis=1)
    eq = tot.cumsum()
    return {"pooled_sharpe_net": sharpe(tot), "pooled_sharpe_gross": sharpe(G.mean(axis=1)), "per_pair_net": {k: round(sharpe(P[k]), 3) for k in P},
            "trades": {k: int(v.loc[a:z, "trade"].sum()) for k, v in pn.items()}, "max_dd_units": float((eq - eq.cummax()).min()),
            "by_year": {int(y): round(sharpe(g), 2) for y, g in tot.groupby(tot.index.year)}}
hid = "C21_PAIRS_ROLLING"
F.Hypothesis(hid, "stat-arb/pairs", "rolling-hedge z-score mean reversion on 6 economically related pairs", "temporary relative mispricing reverts",
             PR["gates"]["DEV"], "Dukascopy D1", json.dumps(PR["neighbours"]), "zero", PROTO, generation=21).register()
res = {"DEV": stage("DEV"), "DEV_2x": stage("DEV", 2.0)["pooled_sharpe_net"]}
res["neighbours"] = {f"entry{e}": stage("DEV", entry=e)["pooled_sharpe_net"] for e in (1.5, 2.5)}
res["neighbours"].update({f"form{f}": stage("DEV", form=f)["pooled_sharpe_net"] for f in (126, 504)})
d = res["DEV"]
res["dev_pass"] = bool(d["pooled_sharpe_net"] >= 0.5 and sum(v > 0 for v in d["per_pair_net"].values()) >= 4 and np.mean([v > 0 for v in res["neighbours"].values()]) >= 2 / 3)
v6.record(hid, "stat-arb/pairs", "primary", {}, "DEV", {"DEV": d, "neigh": res["neighbours"]}, 21, PROTO, "Dukascopy")
if res["dev_pass"]:
    res["VAL"] = stage("VAL"); res["val_pass"] = res["VAL"]["pooled_sharpe_net"] >= 0.3
    if res["val_pass"]:
        res["TEST"] = stage("TEST"); res["TEST_2x"] = stage("TEST", 2.0)["pooled_sharpe_net"]
        res["test_pass"] = res["TEST"]["pooled_sharpe_net"] > 0 and res["TEST_2x"] >= 0
v = "REJECTED" if not res["dev_pass"] else ("EXPLORATORY" if not res.get("val_pass") else ("PROMISING_BUT_UNVALIDATED" if res.get("test_pass") else "EXPLORATORY"))
res["verdict"] = v
F.decide(F.Hypothesis(hid, "", "", "", "", "", "", "", PROTO, generation=21), v, json.dumps({k: res[k]["pooled_sharpe_net"] for k in ("DEV", "VAL", "TEST") if k in res}), {"protocol": PROTO})
Path("results/statarb_gen21.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
