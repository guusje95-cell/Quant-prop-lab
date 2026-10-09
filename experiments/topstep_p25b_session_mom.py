"""P25b/c: US-session momentum vs reversal on GC/SI/CL/FX (protocol config/topstep_gen25_protocol.json, f1b443e)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from qpl.research import factory as F, v6
from qpl.statistics import tests as T
PROTO = "config/topstep_gen25_protocol.json"; PR = json.load(open(PROTO))["P25b_US_SESSION_MOMENTUM"]; PER = PR["periods"]

def sessions(h):
    e = h.copy(); e.index = h.index.tz_convert("America/New_York")
    e["date"] = e.index.normalize().tz_localize(None); e["hr"] = e.index.hour
    g = e.groupby("date")
    def pick(x, hr, col):
        r = x[x.hr == hr]; return r[col].iloc[0] if len(r) else np.nan
    s = pd.DataFrame({"c09": g.apply(lambda x: pick(x, 9, "close")), "o10": g.apply(lambda x: pick(x, 10, "open")),
                      "c15": g.apply(lambda x: pick(x, 15, "close")),
                      "lo": g.apply(lambda x: x[(x.hr >= 10) & (x.hr <= 15)].low.min()), "hi": g.apply(lambda x: x[(x.hr >= 10) & (x.hr <= 15)].high.max())})
    s = s[s.index.dayofweek < 5].dropna()
    s["early"] = s.c09 / s.c15.shift(1) - 1                   # prev 15:00 CT close -> 09:00 CT
    s["rest"] = s.c15 / s.o10 - 1                              # 09:00 CT -> 15:00 CT
    return s.dropna()

def book(s, cost_bp, sign=+1, cmult=1.0):
    sd_e = s.early.rolling(60, min_periods=40).std().shift(1)
    trig = s.early.abs() > 0.25 * sd_e
    vol = s.rest.rolling(20, min_periods=15).std().shift(1)
    pos = sign * np.sign(s.early).where(trig, 0.0) / vol
    pos = pos / pos.abs().rolling(250, min_periods=60).mean().shift(1)
    gross = pos * s.rest
    net = gross - pos.abs() * cost_bp * cmult / 1e4
    worst = np.minimum(0, np.where(pos > 0, pos * (s.lo / s.o10 - 1), -pos * (s.hi / s.o10 - 1)))
    return pd.DataFrame({"pos": pos, "gross": gross, "net": net, "worst": worst}).dropna()

def load(src, sym):
    p = f"data/processed/dukascopy/{sym}_H1.parquet" if src == "duka" else f"data/processed/topstepx/{sym}_1h.parquet"
    return pd.read_parquet(p)[["open", "high", "low", "close"]]

def pooled(B, a, z, col="net"):
    X = pd.DataFrame({k: v.loc[a:z, col] for k, v in B.items()}).fillna(0); tot = X.sum(axis=1)
    ann = len(tot) / ((tot.index[-1] - tot.index[0]).days / 365.25)
    return (float(tot.mean() / tot.std() * np.sqrt(ann)) if tot.std() > 0 else 0.0), tot, X

def stats(B, a, z):
    sh, tot, X = pooled(B, a, z); shg = pooled(B, a, z, "gross")[0]
    tr = X.stack(); tr = tr[tr != 0]
    return {"net_sharpe": round(sh, 3), "gross_sharpe": round(shg, 3), "trades": int(len(tr)), "win_rate": round(float((tr > 0).mean()), 3),
            "profit_factor": round(float(tr[tr > 0].sum() / -tr[tr < 0].sum()), 3), "share_mkts_pos": round(float((X.mean() > 0).mean()), 3),
            "per_mkt": {k: round(float(X[k].mean() / X[k].std() * 16), 2) for k in X if X[k].std() > 0}, "nw_p": round(T.newey_west_t(tot.to_numpy(), 5)[1], 4)}

S = {sym: sessions(load("duka", sym)) for sym in PR["markets_dev"]}
out = {}
pv = {}
for hid, sign in (("P25b_US_SESSION_MOMENTUM", +1), ("P25c_US_SESSION_REVERSAL", -1)):
    F.Hypothesis(hid, "prop/topstep-intraday", PR["hypothesis"] + (" (reversal variant)" if sign < 0 else ""), PR["rationale"], json.dumps(PR["gates"]),
                 "Dukascopy H1 + TopstepX 1h", "single spec", "zero", PROTO, generation=25).register()
    B = {sym: book(S[sym], PR["costs_bp_RT"][f], sign) for sym, f in PR["markets_dev"].items()}
    B2 = {sym: book(S[sym], PR["costs_bp_RT"][f], sign, 2.0) for sym, f in PR["markets_dev"].items()}
    B3 = {sym: book(S[sym], PR["costs_bp_RT"][f], sign, 3.0) for sym, f in PR["markets_dev"].items()}
    r = {"DEV": stats(B, *PER["DEV"]), "DEV_2x": round(pooled(B2, *PER["DEV"])[0], 3), "DEV_3x": round(pooled(B3, *PER["DEV"])[0], 3)}
    pv[hid] = r["DEV"]["nw_p"]
    r["dev_pass"] = bool(r["DEV"]["net_sharpe"] >= 0.5 and r["DEV"]["share_mkts_pos"] >= 4 / 6)
    v6.record(hid, "prop/topstep", hid, {}, "DEV", r["DEV"], 25, PROTO, "Dukascopy H1")
    if r["dev_pass"]:
        r["VAL"] = stats(B, *PER["VAL"]); r["val_pass"] = r["VAL"]["net_sharpe"] >= 0.3
        v6.record(hid, "prop/topstep", hid, {}, "VAL", r["VAL"], 25, PROTO, "Dukascopy H1")
        if r["val_pass"]:
            r["TEST"] = stats(B, *PER["TEST"]); r["TEST_2x"] = round(pooled(B2, *PER["TEST"])[0], 3)
            r["test_pass"] = bool(r["TEST"]["net_sharpe"] > 0 and r["TEST_2x"] >= 0)
            v6.record(hid, "prop/topstep", hid, {}, "TEST_LOOK", r["TEST"], 25, PROTO, "Dukascopy H1")
            if r["test_pass"]:
                BF = {f: book(sessions(load("tsx", f)), PR["costs_bp_RT"][f], sign) for f in PR["markets_fresh"]}
                st = max(b.index[0] for b in BF.values())
                r["FRESH"] = stats(BF, str(st.date()), PER["FRESH"][1]); r["fresh_pass"] = bool(pooled(BF, str(st.date()), PER["FRESH"][1])[1].mean() > 0)
                v6.record(hid, "prop/topstep", hid, {}, "FRESH_LOOK", r["FRESH"], 25, PROTO, "TopstepX")
    v = "REJECTED" if not r["dev_pass"] else ("EXPLORATORY" if not r.get("val_pass") else ("PROMISING_BUT_UNVALIDATED" if r.get("fresh_pass") else "EXPLORATORY"))
    r["verdict"] = v
    F.decide(F.Hypothesis(hid, "", "", "", "", "", "", "", PROTO, generation=25), v, json.dumps({k: r[k]["net_sharpe"] for k in ("DEV", "VAL", "TEST", "FRESH") if k in r}), {"protocol": PROTO})
    out[hid] = r
out["holm_DEV"] = v6.holm(pv)
json.dump(out, open("results/topstep_p25b.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
