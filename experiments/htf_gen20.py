"""Track A gen20: HTF levels on DAILY bars (protocol config/htf_daily_protocol.json, committed 09761e9 before any daily HTF result).
Gated in code: DEV -> VAL -> TEST (single look) -> FRESH_HOLDOUT on TopstepX (single look)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl import instruments as INS  # noqa: E402
from qpl.htf import core as H  # noqa: E402
from qpl.research import factory as F, v6  # noqa: E402
from qpl.statistics import tests as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTO = "config/htf_daily_protocol.json"
PR = json.loads((ROOT / PROTO).read_text())
PR1 = json.loads((ROOT / "config/htf_protocol.json").read_text())
DS = list(PR["datasets_and_periods"].values())
DUKA = ["US500", "US100", "US30", "DE40", "XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "BRENT"]
TSX = ["ES", "NQ", "RTY", "GC", "CL", "6E", "6B", "6J"]
STRATS = [(s, f) for s in ("A1_SR1", "A3_SR3", "A2_BO") for f in ("PW", "PM")]
NEIGH = {"hold2": dict(hold=2), "hold10": dict(hold=10), "tgt1.5R_hold10": dict(hold=10, target_r=1.5)}
HOLD = 5


def load(src, sym):
    if src == "duka":
        return pd.read_parquet(ROOT / f"data/processed/dukascopy/{sym}_D1.parquet")[["open", "high", "low", "close"]]
    if src == "tsx":
        return pd.read_parquet(ROOT / f"data/processed/topstepx/{sym}_daily.parquet")[["open", "high", "low", "close"]]
    d = pd.read_parquet(ROOT / "data/processed/crypto/bitstamp_btcusd_1D.parquet")
    return d[["open", "high", "low", "close"]]


def cost_fn(src, sym):
    if src == "duka":
        c = INS.SPOT_COST_PRICE_UNITS[sym]; return lambda p: c
    if src == "tsx":
        i = INS.get(sym); c = i.cost_per_rt() / i.point_value; return lambda p: c
    return lambda p: 0.0014 * p


DATA = {("duka", s): load("duka", s) for s in DUKA}
DATA.update({("tsx", s): load("tsx", s) for s in TSX})
DATA[("btc", "BTCUSD")] = load("btc", "BTCUSD").loc["2014-06-01":]
LV = {k: H.htf_frame(v, "crypto" if k[0] == "btc" else "fx") for k, v in DATA.items()}
EV = {(k, f): H.detect_events(DATA[k], LV[k], f) for k in DATA for f in ("PW", "PM")}


def trades_for(k, strat, fam, cost_mult=1.0, **kw):
    kw.setdefault("hold", HOLD)
    ev = [e for e in EV[(k, fam)] if e.strategy == strat]
    cf = cost_fn(*k)
    return H.simulate(DATA[k], ev, lambda p: cf(p) * cost_mult, **kw)


def pooled(keys, strat, fam, a, z, cost_mult=1.0, **kw):
    tr, cal = [], set()
    for k in keys:
        t = trades_for(k, strat, fam, cost_mult, **kw)
        idx = DATA[k].loc[a:z].index
        cal |= set(idx.tz_convert("UTC").normalize().tz_localize(None))
        if len(t):
            t = t[(t.t_entry >= pd.Timestamp(a, tz="UTC")) & (t.t_entry <= pd.Timestamp(z, tz="UTC") + pd.Timedelta(days=1))]
            t["inst"] = k[1]; tr.append(t)
    T_ = pd.concat(tr) if tr else pd.DataFrame()
    cal = pd.DatetimeIndex(sorted(cal))
    ann = len(cal) / ((cal[-1] - cal[0]).days / 365.25) if len(cal) > 1 else 252
    dn, dg = H.daily_series(T_, cal), H.daily_series(T_, cal, "R_gross")
    m = H.summarize(T_, dn, ann, dg)
    if len(T_):
        m["ann_days"] = round(ann, 1)
        m["nw_p"] = T.newey_west_t(dn.to_numpy(), lags=5)[1]
        bi = T_.groupby("inst").R_net.mean()
        m["share_inst_positive"] = float((bi > 0).mean()); m["by_inst_exp_R"] = bi.round(3).to_dict()
        m["by_year_R"] = T_.groupby(T_.t_entry.dt.year).R_net.sum().round(2).to_dict()
        m["sample"] = [str(cal[0].date()), str(cal[-1].date())]
    return m, T_


def r(m, keys=("sharpe_net", "sharpe_gross", "expectancy_R_net", "trades", "win_rate", "profit_factor_net", "share_inst_positive")):
    return {k: (round(m[k], 3) if isinstance(m.get(k), float) else m.get(k)) for k in keys}


out = {"dukascopy": {}, "btc": {}}
for dsname, keys, per in (("dukascopy", [k for k in DATA if k[0] == "duka"], DS[0]), ("btc", [("btc", "BTCUSD")], DS[1])):
    pv = {}
    for strat, fam in STRATS:
        hid = f"HTFD_{strat}_{fam}_{dsname.upper()}"
        F.Hypothesis(hid, "HTF liquidity levels", PR1["strategies"][strat], "stop-run/liquidity (A1/A3) or breakout continuation (A2) at HTF levels",
                     PR["gates"], dsname, json.dumps(list(NEIGH)), "zero (no position)", PROTO, generation=20).register()
        res = {}
        m, _ = pooled(keys, strat, fam, *per["DEV"]); res["DEV"] = m
        res["DEV_2x_cost"] = r(pooled(keys, strat, fam, *per["DEV"], cost_mult=2.0)[0])
        res["DEV_neighbours"] = {nk: r(pooled(keys, strat, fam, *per["DEV"], **kw)[0]) for nk, kw in NEIGH.items()}
        pv[hid] = m.get("nw_p", 1.0)
        need_inst = 0.6 if dsname == "dukascopy" else 0.0
        res["dev_pass"] = bool(m.get("trades", 0) and m["sharpe_net"] >= 0.5 and m["expectancy_R_net"] > 0 and m.get("share_inst_positive", 0) >= need_inst)
        v6.record(hid, "HTF", strat, {"family": fam}, "DEV", {**r(m), "neigh": res["DEV_neighbours"]}, 20, PROTO, dsname)
        if res["dev_pass"]:
            mv, _ = pooled(keys, strat, fam, *per["VAL"]); res["VAL"] = mv
            res["val_pass"] = bool(mv["sharpe_net"] >= 0.3 and mv["expectancy_R_net"] > 0)
            v6.record(hid, "HTF", strat, {"family": fam}, "VAL", r(mv), 20, PROTO, dsname)
            if res["val_pass"]:
                mt, _ = pooled(keys, strat, fam, *per["TEST"]); mt2, _ = pooled(keys, strat, fam, *per["TEST"], cost_mult=2.0)
                res["TEST"] = mt; res["TEST_2x"] = r(mt2)
                res["test_pass"] = bool(mt["sharpe_net"] > 0 and mt2["sharpe_net"] >= 0)
                v6.record(hid, "HTF", strat, {"family": fam}, "TEST_LOOK", r(mt), 20, PROTO, dsname)
                if dsname == "dukascopy" and res["test_pass"]:
                    tk = [k for k in DATA if k[0] == "tsx"]
                    mh, _ = pooled(tk, strat, fam, *PR["datasets_and_periods"]["TOPSTEPX_DAILY"]["FRESH_HOLDOUT"])
                    res["FRESH_HOLDOUT"] = mh; res["holdout_pass"] = bool(mh.get("expectancy_R_net", -1) > 0)
                    v6.record(hid, "HTF", strat, {"family": fam}, "FRESH_HOLDOUT_LOOK", r(mh), 20, PROTO, "topstepx")
        v = ("REJECTED" if not res["dev_pass"] else "EXPLORATORY" if not res.get("val_pass") else
             "PROMISING_BUT_UNVALIDATED" if not (res.get("test_pass") and res.get("holdout_pass", dsname == "btc")) else "ELIGIBLE_FOR_INDEPENDENT_VALIDATION")
        res["verdict"] = v
        F.decide(F.Hypothesis(hid, "HTF", "", "", "", "", "", "", PROTO, generation=20), v,
                 json.dumps({k: r(res[k]) for k in ("DEV", "VAL", "TEST", "FRESH_HOLDOUT") if k in res})[:600], {"protocol": PROTO})
        out[dsname][f"{strat}_{fam}"] = res
        print(dsname, strat, fam, "DEV", r(m), "->", res["dev_pass"], "| VAL", r(res["VAL"]) if "VAL" in res else "-", "|", v, flush=True)
    out[dsname]["holm_DEV"] = v6.holm(pv)
# descriptive (no gate): fresh-holdout behaviour of ALL primaries on TopstepX is NOT computed unless a primary passed - protocol.
(ROOT / "results/htf_gen20.json").write_text(json.dumps(out, indent=1, default=str))
